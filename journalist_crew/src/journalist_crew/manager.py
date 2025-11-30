import yaml
from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from journalist_crew.models import ResearchDossier
from journalist_crew.storage import StorageManager

class JournalistSession:
    def __init__(self):
        self.search_tool = SerperDevTool()
        self.scrape_tool = ScrapeWebsiteTool()
        self.db = StorageManager()
        self.current_dossier: ResearchDossier | None = None
        
        # Load configs
        with open('src/journalist_crew/config/agents.yaml', 'r') as f:
            self.agents_config = yaml.safe_load(f)
        with open('src/journalist_crew/config/tasks.yaml', 'r') as f:
            self.tasks_config = yaml.safe_load(f)

    def load_topic(self, topic: str) -> bool:
        """Loads context from DB (Instant)."""
        print(f"🔎 Querying DB for '{topic}'...")
        dossier = self.db.load_dossier(topic)
        if dossier:
            self.current_dossier = dossier
            print("✅ Dossier loaded from memory.")
            return True
        return False

    def research_phase(self, topic: str, instructions: str = ""):
        """Runs the expensive research agents."""
        print(f"\n🚀 Running Deep Research on: {topic}")
        
        # Initialize Agents
        strategy = Agent(config=self.agents_config['strategy_chief'], tools=[self.search_tool], verbose=True)
        hunter = Agent(config=self.agents_config['timeline_hunter'], tools=[self.search_tool, self.scrape_tool], verbose=True)
        analyst = Agent(config=self.agents_config['context_analyst'], tools=[self.search_tool], verbose=True)

        # Initialize Tasks
        plan = Task(config=self.tasks_config['plan_task'], agent=strategy)
        facts = Task(config=self.tasks_config['fact_finding_task'], agent=hunter)
        analysis = Task(config=self.tasks_config['analysis_task'], agent=analyst)
        compile_t = Task(config=self.tasks_config['compile_task'], agent=strategy, output_pydantic=ResearchDossier)

        # Inject inputs
        crew = Crew(
            agents=[strategy, hunter, analyst],
            tasks=[plan, facts, analysis, compile_t],
            verbose=True
        )

        result = crew.kickoff(inputs={"question": topic})
        
        # Save Result
        self.current_dossier = result.pydantic
        self.db.save_dossier(self.current_dossier)
        return self.current_dossier

    def writing_phase(self, instructions: str, lang: str):
        """Runs only the writer using cached data."""
        if not self.current_dossier:
            return "Error: No research loaded."

        writer = Agent(config=self.agents_config['writer'], verbose=True)

        # We manually inject the context here to ensure the Writer follows strict instructions
        write_task = Task(
            config=self.tasks_config['write_task'],
            agent=writer,
            description=self.tasks_config['write_task']['description'].format(
                lang=lang,
                instructions=instructions
            ) + f"\n\n**CONTEXT DATA:**\n{self.current_dossier.model_dump_json()}"
        )

        crew = Crew(agents=[writer], tasks=[write_task], verbose=True)
        result = crew.kickoff()
        
        # Save Article to DB
        self.db.save_article(self.current_dossier.topic, result.raw, instructions, lang)
        return result.raw