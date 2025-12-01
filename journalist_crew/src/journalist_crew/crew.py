import os

from crewai import LLM, Agent, Crew, Task
from crewai.project import CrewBase, agent
from crewai_tools import PDFSearchTool, ScrapeWebsiteTool, SerperDevTool, WebsiteSearchTool, YoutubeVideoSearchTool

from journalist_crew.models import ResearchDossier
from journalist_crew.storage import StorageManager


@CrewBase
class JournalistCrew:
    """JournalistCrew - Database Native & Interactive"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        self.search_tool = SerperDevTool()
        self.scrape_tool = ScrapeWebsiteTool()

        # self.site_search_tool = WebsiteSearchTool(
        #     config=dict(
        #         llm=dict(
        #             provider="google",
        #             config=dict(
        #                 model="gemini-2.0-flash-lite",
        #                 api_key=os.getenv("GOOGLE_API_KEY"),
        #             ),
        #         ),
        #         embedder=dict(
        #             provider="google-generativeai",
        #             config=dict(
        #                 model_name="models/text-embedding-004",
        #                 task_type="RETRIEVAL_DOCUMENT",
        #                 api_key=os.getenv("GOOGLE_API_KEY"),
        #             ),
        #         ),
        #     )
        # )
        # self.pdf_tool = PDFSearchTool(
        #     config={
        #         "embedding_model": {
        #             "provider": "google",
        #             "config": {
        #                 "model_name": "models/text-embedding-004",
        #                 "api_key": os.getenv("GOOGLE_API_KEY"),
        #             },
        #         },
        #         "vectordb": {
        #             "provider": "chromadb",  # or "qdrant" if you prefer
        #             "config": {
        #                 # optional settings for persistent storage
        #                 # from chromadb.config import Settings
        #                 # "settings": Settings(
        #                 #     persist_directory="./chroma",
        #                 #     allow_reset=True,
        #                 #     is_persistent=True,
        #                 # )
        #             },
        #         },
        #     }
        # )
        # self.youtube_tool = YoutubeVideoSearchTool(
        #     config=dict(
        #         llm=dict(
        #             provider="google",
        #             config=dict(
        #                 model="gemini-2.0-flash-lite",
        #                 api_key=os.getenv("GOOGLE_API_KEY"),
        #             ),
        #         ),
        #         embedder=dict(
        #             provider="google-generativeai",
        #             config=dict(
        #                 model_name="models/text-embedding-004",
        #                 task_type="RETRIEVAL_DOCUMENT",
        #                 api_key=os.getenv("GOOGLE_API_KEY"),
        #             ),
        #         ),
        #     )
        # )

        self.db = StorageManager()
        self.current_dossier = None


        # --- LLM CONFIGURATION ---
        self.smart_llm = LLM(
            model="openrouter/x-ai/grok-4.1-fast:free",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            temperature=0.7,
            max_tokens=16384,
            timeout=240,
            max_retries=3
        )

        self.fast_llm = LLM(
            model="openrouter/x-ai/grok-4.1-fast:free",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            temperature=0.3,
            max_tokens=16384,
            timeout=240,
            max_retries=3
        )


    @agent
    def strategy_chief(self) -> Agent:
        return Agent(
            config=self.agents_config['strategy_chief'],
            tools=[self.search_tool], # self.site_search_tool
            verbose=True,
            llm=self.smart_llm
        )

    @agent
    def timeline_hunter(self) -> Agent:
        return Agent(
            config=self.agents_config['timeline_hunter'],
            tools=[
                self.search_tool,
                self.scrape_tool,
                
            ],
            # self.pdf_tool,
            # self.youtube_tool
            verbose=True,
            llm=self.fast_llm
        )

    @agent
    def context_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['context_analyst'],
            tools=[self.search_tool, self.scrape_tool],
            verbose=True,
            llm=self.smart_llm
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config['writer'],
            verbose=True,
            llm=self.smart_llm
        )


    def load_context(self, dossier_id: str) -> bool:
        """Loads a specific dossier by UUID."""
        print(f"🔎 Loading Session ID: {dossier_id}...")
        dossier = self.db.load_dossier(dossier_id)
        if dossier:
            self.current_dossier = dossier
            print(f"✅ Loaded Topic: '{dossier.topic}'")
            return True
        return False

    def run_research(self, topic: str, instructions: str = ""):
        print(f"\n🚀 Starting Research Session on: {topic}")

        existing_id = None
        if self.current_dossier:
            existing_id = self.current_dossier.id
            print(f"🔄 Updating existing Dossier ID: {existing_id}")

        if instructions:
            print(f"🎯 Focus: {instructions}")

        strategy = self.strategy_chief()
        hunter = self.timeline_hunter()
        analyst = self.context_analyst()

        plan = Task(config=self.tasks_config['plan_task'], agent=strategy)
        facts = Task(config=self.tasks_config['fact_finding_task'], agent=hunter)
        analysis = Task(config=self.tasks_config['analysis_task'], agent=analyst)

        compile_t = Task(
            config=self.tasks_config['compile_task'],
            agent=strategy,
            output_pydantic=ResearchDossier
        )

        research_crew = Crew(
            agents=[strategy, hunter, analyst],
            tasks=[plan, facts, analysis, compile_t],
            verbose=True,
            max_rpm=30
        )

        # Context Injection
        search_query = topic
        if instructions:
            old_data_context = ""
            if self.current_dossier:
                old_data_context = f"\n\nEXISTING KNOWLEDGE TO UPDATE:\n{self.current_dossier.model_dump_json()}"

            search_query = f"{topic}. SPECIFIC FOCUS: {instructions}. (Context: North Macedonia/Balkans){old_data_context}"

        result = research_crew.kickoff(inputs={"question": search_query})

        if existing_id:
            result.pydantic.id = existing_id

        self.current_dossier = result.pydantic

        self.db.save_dossier(self.current_dossier)

        return self.current_dossier

    def run_writer(self, instructions: str, lang: str):
        if not self.current_dossier:
            raise ValueError("No dossier loaded.")

        writer_agent = self.writer()
        context_data = self.current_dossier.model_dump_json()

        # 1. Draft Task
        write_task = Task(
            config=self.tasks_config['write_task'],
            agent=writer_agent,
            description=self.tasks_config['write_task']['description'].format(
                lang=lang,
                instructions=instructions
            ) + f"\n\n**SOURCE DATA:**\n{context_data}"
        )

        # 2. Edit Task
        edit_task = Task(
            config=self.tasks_config['edit_task'],
            agent=writer_agent,
            context=[write_task]
        )

        writing_crew = Crew(
            agents=[writer_agent],
            tasks=[write_task, edit_task],
            verbose=True,
            max_rpm=30
        )

        result = writing_crew.kickoff()

        self.db.save_article(
            self.current_dossier.id,
            result.raw,
            instructions,
            lang
        )

        return result.raw