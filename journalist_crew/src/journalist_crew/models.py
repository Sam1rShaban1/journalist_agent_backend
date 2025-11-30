from pydantic import BaseModel, Field
from typing import List

class TimelineEvent(BaseModel):
    year: str = Field(..., description="Year or specific date.")
    event: str = Field(..., description="Description of the event.")

class KeyFigure(BaseModel):
    name: str = Field(..., description="Name of the person/organization.")
    role: str = Field(..., description="Role during the relevant time period.")
    impact: str = Field(..., description="Specific contribution or controversy.")

class ResearchDossier(BaseModel):
    """
    The Master Context Object.
    This persists in the database and is fed to the Writer agent.
    """
    topic: str = Field(..., description="The main topic.")
    executive_summary: List[str] = Field(..., description="3-5 high-level summary points.")
    comprehensive_narrative: str = Field(..., description="A deep-dive narrative covering the 'Why' and 'How' from inception to now.")
    key_figures: List[KeyFigure] = Field(..., description="List of major players.")
    timeline: List[TimelineEvent] = Field(..., description="Chronological list of events.")