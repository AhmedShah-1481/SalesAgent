"""Service matching (§6) + decision-maker identification (§7) models — Phase 5.

`ServiceMatch` is the grounded pick of one of OUR OWN services for a qualified prospect —
the matcher may choose ONLY from services present in the RAG knowledge base (§6 forbids
inventing services). `DecisionMakerList` is the set of relevant people extracted for a
company, prioritized by the recommended service (§7). Both are LLM structured-output
targets; the router unpacks them onto the flat `Lead` fields (`recommended_service`,
`service_rationale`, `contacts`), so `Lead` stays stable and the store/pipeline are
unaffected.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.contact import Contact


class ServiceMatch(BaseModel):
    """Which of our own services best fits a prospect, grounded in the knowledge base (§6)."""

    recommended_service: str | None = Field(
        None,
        description="Best-fit service, chosen ONLY from our documented offerings; null if none fit",
    )
    rationale: str | None = Field(
        None, description="Why this service fits, grounded in the prospect's problems/signals"
    )
    alternatives: list[str] = Field(
        default_factory=list, description="Other documented services that could also fit"
    )


class DecisionMakerList(BaseModel):
    """Relevant decision-makers for a company, prioritized by the recommended service (§7)."""

    contacts: list[Contact] = Field(default_factory=list)
