import uuid
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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique Session ID")
    topic: str = Field(..., description="The main topic.")
    executive_summary: List[str] = Field(..., description="High-level summary points.")
    comprehensive_narrative: str = Field(..., description="A deep-dive narrative.")
    key_figures: List[KeyFigure] = Field(..., description="List of major players.")
    timeline: List[TimelineEvent] = Field(..., description="Chronological list of events.")