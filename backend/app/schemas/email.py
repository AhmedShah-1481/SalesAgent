"""Outreach email draft + the log record persisted per outreach action (§9, §10)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EmailDraft(BaseModel):
    to: str | None = None
    subject: str = ""
    body: str = ""
    meeting_link: str | None = None


class OutreachLog(BaseModel):
    """§10: log every outreach with company, contact, role, score, service, message,
    evidence, and timestamp."""

    company: str
    contact_name: str | None = None
    role: str | None = None
    lead_score: float | None = None
    recommended_service: str | None = None
    message: str = ""
    evidence: list[str] = Field(default_factory=list)
    timestamp: datetime | None = None
