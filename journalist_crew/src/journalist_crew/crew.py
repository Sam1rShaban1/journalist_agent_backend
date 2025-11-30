from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, task, crew
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from journalist_crew.models import ResearchDossier
from journalist_crew.storage import StorageManager

@CrewBase
class JournalistCrew():
    """JournalistCrew - Database Native & Interactive"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        # Initialize Tools & DB
        self.search_tool = SerperDevTool()
        self.scrape_tool = ScrapeWebsiteTool()
        self.db = StorageManager()
        self.current_dossier = None

    # --- AGENTS ---
    @agent
    def strategy_chief(self) -> Agent:
        return Agent(
            config=self.agents_config['strategy_chief'],
            tools=[self.search_tool],
            verbose=True
        )

    @agent
    def timeline_hunter(self) -> Agent:
        return Agent(
            config=self.agents_config['timeline_hunter'],
            tools=[self.search_tool, self.scrape_tool],
            verbose=True
        )

    @agent
    def context_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['context_analyst'],
            tools=[self.search_tool],
            verbose=True
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config['writer'],
            verbose=True
        )

    # --- LOGIC HANDLERS ---

    def load_context(self, topic: str) -> bool:
        """Attempts to load a research dossier from SQLite."""
        print(f"🔎 Checking database for '{topic}'...")
        dossier = self.db.load_dossier(topic)
        if dossier:
            self.current_dossier = dossier
            print("✅ Dossier loaded from database.")
            return True
        return False

    def run_research(self, topic: str, instructions: str = ""):
        """
        Runs the Research Phase.
        Saves the result to the Database.
        """
        print(f"\n🚀 Starting Deep Research on: {topic}")
        
        # Instantiate Agents
        strategy = self.strategy_chief()
        hunter = self.timeline_hunter()
        analyst = self.context_analyst()

        # Instantiate Tasks manually to inject dynamic inputs
        plan = Task(
            config=self.tasks_config['plan_task'], 
            agent=strategy
        )
        facts = Task(
            config=self.tasks_config['fact_finding_task'], 
            agent=hunter
        )
        analysis = Task(
            config=self.tasks_config['analysis_task'], 
            agent=analyst
        )
        
        # The Compilation task enforces the Pydantic Structure
        compile_t = Task(
            config=self.tasks_config['compile_task'], 
            agent=strategy, 
            output_pydantic=ResearchDossier
        )

        # Create the Research Sub-Crew
        research_crew = Crew(
            agents=[strategy, hunter, analyst],
            tasks=[plan, facts, analysis, compile_t],
            verbose=True
        )

        # Run
        result = research_crew.kickoff(inputs={"question": topic})
        
        # Handle Result & Persistence
        self.current_dossier = result.pydantic
        self.db.save_dossier(self.current_dossier)
        
        return self.current_dossier

    def run_writer(self, instructions: str, lang: str):
        """
        Runs the Writing Phase.
        Uses cached data from DB. Saves Article to DB.
        """
        if not self.current_dossier:
            raise ValueError("No research dossier loaded. Load or research a topic first.")

        writer_agent = self.writer()

        # DYNAMIC TASK CREATION
        # We inject the JSON dossier into the description so the writer strictly follows it.
        context_data = self.current_dossier.model_dump_json()
        
        write_task = Task(
            config=self.tasks_config['write_task'],
            agent=writer_agent,
            description=self.tasks_config['write_task']['description'].format(
                lang=lang, 
                instructions=instructions
            ) + f"\n\n**STRICT SOURCE MATERIAL:**\n{context_data}"
        )

        writing_crew = Crew(
            agents=[writer_agent],
            tasks=[write_task],
            verbose=True
        )

        result = writing_crew.kickoff()
        
        # Save Generated Draft to DB
        self.db.save_article(
            self.current_dossier.topic, 
            result.raw, 
            instructions, 
            lang
        )
        
        return result.raw