from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class CitationInput(BaseModel):
    statement: str = Field(..., description="The specific fact, quote, or event being cited.")
    source_url: str = Field(..., description="The direct URL where this information was found.")
    source_name: str = Field(..., description="The name of the website or publication (e.g., 'BalkanInsight', 'Reuters').")

class CitationTool(BaseTool):
    name: str = "Citation Formatter"
    description: str = (
        "Use this tool to format a verified fact with an inline, clickable citation. "
        "Returns a string in the format: 'Fact... ([Source](URL))'. "
        "You MUST use this for every key date, figure, or quote."
    )
    args_schema: type[BaseModel] = CitationInput

    def _run(self, statement: str, source_url: str, source_name: str) -> str:
        # Returns: "The budget was 20M ([BalkanInsight](https://...))."
        return f"{statement} ([{source_name}]({source_url}))"