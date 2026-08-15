"""Activity-feed event emitted by pipeline nodes for the live UI feed."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ActivityEvent(BaseModel):
    kind: str = Field(description="e.g. research, qualify, email, follow_up, meeting")
    message: str
    lead_id: str | None = None
    stage: str | None = None
    timestamp: datetime | None = None
