"""Lead + confidence scoring (§5) + service match / decision-makers (§6–7) + conversation (§10)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.contact import Contact
from app.schemas.conversation import Message
from app.schemas.enums import PipelineStage, ResponseCategory

# ScoreBreakdown lives in research.py (shared with the qualifier); re-exported here so
# `from app.schemas.lead import ScoreBreakdown` keeps working.
from app.schemas.research import ResearchProfile, ScoreBreakdown

__all__ = ["Lead", "ScoreBreakdown", "ResearchProfile"]


class Lead(BaseModel):
    id: str
    company_name: str
    domain: str | None = None
    stage: PipelineStage = PipelineStage.DISCOVERED
    confidence: float | None = Field(
        None, ge=0, le=100, description="Lead confidence percentage, 0-100"
    )
    explanation: str | None = Field(None, description="Written rationale for the score")
    score_breakdown: ScoreBreakdown | None = None
    evidence: list[str] = Field(default_factory=list)
    research: ResearchProfile | None = Field(None, description="Deep-research dossier (§4)")
    recommended_service: str | None = None
    service_rationale: str | None = Field(
        None, description="Grounded reason the recommended service fits this prospect (§6)"
    )
    contacts: list[Contact] = Field(default_factory=list)
    # ── Conversation + follow-up (§10–11) ────────────────
    messages: list[Message] = Field(
        default_factory=list, description="Conversation turns, agent + prospect (§13)"
    )
    last_response_category: ResponseCategory | None = Field(
        None, description="Category of the most recent inbound reply (§10)"
    )
    follow_up_count: int = Field(0, description="Automated second-touch emails sent (§11)")
    last_outreach_at: datetime | None = Field(
        None, description="When we last emailed — drives the 3-day follow-up clock (§11)"
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None
