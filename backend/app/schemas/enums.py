"""Spec-locked enums: pipeline states (§15) and response categories (§11)."""
from __future__ import annotations

from enum import StrEnum


class PipelineStage(StrEnum):
    """Sales pipeline states from the challenge spec, §15."""

    # positive lifecycle
    DISCOVERED = "Discovered"
    POTENTIAL = "Potential"
    RESEARCHING = "Researching"
    QUALIFIED = "Qualified"
    CONTACTED = "Contacted"
    INTERESTED = "Interested"
    MEETING_SCHEDULED = "Meeting Scheduled"
    CONVERTED = "Converted"
    # negative / terminal
    NOT_QUALIFIED = "Not Qualified"
    NOT_INTERESTED = "Not Interested"
    DO_NOT_CONTACT = "Do Not Contact"


class ResponseCategory(StrEnum):
    """Inbound reply classification from the challenge spec, §11."""

    POSITIVE = "Positive/Interested"
    MEETING_REQUESTED = "Meeting requested"
    QUESTION = "Question"
    PRICING_OBJECTION = "Pricing objection"
    TECHNICAL_OBJECTION = "Technical objection"
    NOT_INTERESTED = "Not interested"
    NOT_NOW = "Not now"
    WRONG_PERSON = "Wrong person/Referral"
    OTHER = "Other"
