"""Shared LangGraph state — the single contract every pipeline node reads/writes.

Append-only fields use reducers so parallel/loop nodes accumulate rather than
overwrite. The values inside the lists are the pydantic models from app.schemas.
"""
from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from app.schemas.activity import ActivityEvent
from app.schemas.email import OutreachLog
from app.schemas.icp import ICP
from app.schemas.lead import Lead


class PipelineState(TypedDict, total=False):
    # ── Company knowledge (RAG grounding) ────────────────
    company_name: str
    company_knowledge: str  # retrieved grounding context / summary

    # ── ICP intake (§3) ──────────────────────────────────
    icp: ICP | None

    # ── Leads flowing through discovery -> qualification -> outreach ──
    candidates: list[Lead]  # DISCOVERED, pre-cheap-filter (overwrite, not accumulated)
    leads: Annotated[list[Lead], add]
    current_lead_id: str | None

    # ── LLM conversation turns for chat-style nodes ──────
    messages: Annotated[list[AnyMessage], add_messages]

    # ── Live activity feed (append-only) ─────────────────
    activity: Annotated[list[ActivityEvent], add]

    # ── Outreach actions logged per email (append-only, §9) ──
    outreach_logs: Annotated[list[OutreachLog], add]

    # ── Non-fatal errors collected during a run ──────────
    errors: Annotated[list[str], add]
