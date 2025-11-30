# ... imports stay the same ...
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, task, crew
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from journalist_crew.models import ResearchDossier
from journalist_crew.storage import StorageManager
import os
from crewai import LLM

@CrewBase
class JournalistCrew():
    """JournalistCrew - Database Native & Interactive"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        self.search_tool = SerperDevTool()
        self.scrape_tool = ScrapeWebsiteTool()
        self.db = StorageManager()
        self.current_dossier = None

        # ... (LLM Definitions stay the same as your previous setup) ...
        self.smart_llm = LLM(
            model="openrouter/google/gemini-2.0-flash-exp:free",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            temperature=0.7
        )
        self.fast_llm = LLM(
            model="openrouter/x-ai/grok-4-fast:free",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            temperature=0.5
        )

    # ... (Agents definitions stay the same) ...
    @agent
    def strategy_chief(self) -> Agent:
        return Agent(config=self.agents_config['strategy_chief'], tools=[self.search_tool], verbose=True, llm=self.smart_llm)

    @agent
    def timeline_hunter(self) -> Agent:
        return Agent(config=self.agents_config['timeline_hunter'], tools=[self.search_tool, self.scrape_tool], verbose=True, llm=self.fast_llm)

    @agent
    def context_analyst(self) -> Agent:
        return Agent(config=self.agents_config['context_analyst'], tools=[self.search_tool], verbose=True, llm=self.smart_llm)

    @agent
    def writer(self) -> Agent:
        return Agent(config=self.agents_config['writer'], verbose=True, llm=self.smart_llm)

    # --- UPDATED LOGIC HANDLERS ---

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
        print(f"\n🚀 Starting New Research Session on: {topic}")
        
        # (Task definitions skipped for brevity - same as before)
        # We manually construct tasks to inject inputs
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
            verbose=True
        )

        result = research_crew.kickoff(inputs={"question": topic})
        
        # The resulting Pydantic object auto-generates a new UUID if we didn't provide one
        self.current_dossier = result.pydantic
        
        # Save using the new UUID
        self.db.save_dossier(self.current_dossier)
        
        return self.current_dossier

    def run_writer(self, instructions: str, lang: str):
        if not self.current_dossier:
            raise ValueError("No dossier loaded.")

        writer_agent = self.writer()
        context_data = self.current_dossier.model_dump_json()
        
        write_task = Task(
            config=self.tasks_config['write_task'],
            agent=writer_agent,
            description=self.tasks_config['write_task']['description'].format(
                lang=lang, 
                instructions=instructions
            ) + f"\n\n**SOURCE DATA:**\n{context_data}"
        )

        writing_crew = Crew(agents=[writer_agent], tasks=[write_task], verbose=True)
        result = writing_crew.kickoff()
        
        # Save linked to the current Dossier UUID
        self.db.save_article(
            self.current_dossier.id, 
            result.raw, 
            instructions, 
            lang
        )
        
        return result.raw