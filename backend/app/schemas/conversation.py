"""Conversation turns (§13 short-term memory) + reply classification (§10) — Phase 7.

`Message` is one turn in a lead's conversation (an agent email we sent, or a prospect reply).
`ReplyClassification` is what the classifier LLM returns for an inbound reply; its `category`
drives the pipeline's next action (§10).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import ResponseCategory


class Message(BaseModel):
    """One conversation turn with a prospect."""

    role: str = Field(description="'agent' (we sent it) or 'prospect' (inbound reply)")
    channel: str = Field("email", description="'email' or 'whatsapp'")
    text: str = ""
    category: ResponseCategory | None = Field(
        None, description="Set on classified prospect replies"
    )
    timestamp: datetime | None = None


class ReplyClassification(BaseModel):
    """LLM classification of one inbound reply (§10)."""

    category: ResponseCategory
    reasoning: str = Field(description="Why this category, grounded in the reply text")
    suggested_action: str = Field("", description="Next action for the sales agent")
