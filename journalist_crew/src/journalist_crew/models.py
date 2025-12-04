import uuid
from typing import List
from pydantic import BaseModel, Field

class SourceReference(BaseModel):
    title: str = Field(..., description="Title of the article or document.")
    url: str = Field(..., description="Direct URL.")
    credibility_score: int = Field(..., description="1-10 score of source reliability.")

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
    comprehensive_narrative: str = Field(..., description="Deep-dive narrative history. Must contain inline citations.")
    key_figures: List[KeyFigure] = Field(..., description="List of major players.")
    timeline: List[TimelineEvent] = Field(..., description="Chronological list of events.")
    sources: List[SourceReference] = Field(default_factory=list, description="List of all unique sources used.")