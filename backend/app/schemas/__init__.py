"""Pydantic domain models — shared across the graph, API, and (later) Supabase.

These double as structured-output targets for LangChain ``.with_structured_output(...)``.
"""
from app.schemas.activity import ActivityEvent
from app.schemas.contact import Contact
from app.schemas.conversation import Message, ReplyClassification
from app.schemas.email import EmailDraft, OutreachLog
from app.schemas.enums import PipelineStage, ResponseCategory
from app.schemas.icp import ICP
from app.schemas.lead import Lead, ScoreBreakdown
from app.schemas.matching import DecisionMakerList, ServiceMatch
from app.schemas.meeting import AdminBriefing, Meeting
from app.schemas.research import QualificationResult, ResearchProfile

__all__ = [
    "ActivityEvent",
    "Contact",
    "Message",
    "ReplyClassification",
    "EmailDraft",
    "OutreachLog",
    "PipelineStage",
    "ResponseCategory",
    "ICP",
    "Lead",
    "ScoreBreakdown",
    "ServiceMatch",
    "DecisionMakerList",
    "ResearchProfile",
    "QualificationResult",
    "Meeting",
    "AdminBriefing",
]
