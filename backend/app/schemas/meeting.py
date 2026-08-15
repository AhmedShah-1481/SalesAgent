"""Meeting record + admin briefing (§12, §13)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AdminBriefing(BaseModel):
    """Structured admin briefing (§12) — the four elements the reminder must include."""

    customer_problem: str = Field(description="The prospect's likely problem, grounded in research")
    recommended_service: str = Field(description="Which of our services we're pitching and why")
    key_objections: list[str] = Field(
        default_factory=list, description="Objections/questions raised in the conversation so far"
    )
    discussion_points: list[str] = Field(
        default_factory=list, description="What the admin should cover in the meeting"
    )


class Meeting(BaseModel):
    lead_id: str | None = Field(None, description="Lead this meeting belongs to")
    company: str
    contact_name: str | None = None
    scheduled_time: datetime | None = None
    meeting_link: str | None = None
    briefing: str | None = Field(
        None,
        description="Admin briefing: customer problem, recommended service, "
        "key objections/questions, discussion points",
    )
    reminder_sent: bool = False
