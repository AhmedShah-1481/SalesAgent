"""Response Classification node (§10) — Phase 7.

Classifies an inbound prospect reply into one of the nine ResponseCategory values and applies the
resulting pipeline transition. Classification determines the pipeline's next action (§10):

    Positive / Meeting requested          -> Interested   (Phase 8 books the meeting)
    Question / Pricing / Technical obj.   -> Interested   (engaged; keep the conversation going)
    Not interested                        -> Not Interested
    Not now / Wrong person / Other        -> stage unchanged (soft defer / reroute)

The classifier LLM is dependency-injected so this unit-tests with no API key or network.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.graph.state import PipelineState
from app.schemas.conversation import Message, ReplyClassification
from app.schemas.enums import PipelineStage, ResponseCategory
from app.schemas.lead import Lead

_CATEGORIES = ", ".join(c.value for c in ResponseCategory)

# Category -> forced pipeline transition. Categories omitted here leave the stage unchanged
# (Not now / Wrong person / Other are soft signals, not stage moves).
_CATEGORY_TO_STAGE: dict[ResponseCategory, PipelineStage] = {
    ResponseCategory.POSITIVE: PipelineStage.INTERESTED,
    ResponseCategory.MEETING_REQUESTED: PipelineStage.INTERESTED,
    ResponseCategory.QUESTION: PipelineStage.INTERESTED,
    ResponseCategory.PRICING_OBJECTION: PipelineStage.INTERESTED,
    ResponseCategory.TECHNICAL_OBJECTION: PipelineStage.INTERESTED,
    ResponseCategory.NOT_INTERESTED: PipelineStage.NOT_INTERESTED,
}


def next_stage(category: ResponseCategory, current: PipelineStage) -> PipelineStage:
    """The pipeline stage an inbound reply of this category moves the lead to (§10)."""
    return _CATEGORY_TO_STAGE.get(category, current)


def _classify_prompt(lead: Lead, reply_text: str) -> str:
    ctx = (
        f"We offered '{lead.recommended_service}' to {lead.company_name}."
        if lead.recommended_service
        else f"Prospect company: {lead.company_name}."
    )
    return (
        "You are triaging an inbound reply from a B2B sales prospect. Classify it into EXACTLY one "
        f"category from this list: {_CATEGORIES}. Judge only from the reply text — do not assume "
        "intent that isn't there. Give brief reasoning and a short suggested next action for the "
        f"sales agent.\n\n{ctx}\n\nInbound reply:\n\"\"\"\n{reply_text.strip()}\n\"\"\""
    )


def classify_reply(
    lead: Lead, reply_text: str, *, classifier=None, settings=None
) -> ReplyClassification:
    """Classify one inbound reply into a ResponseCategory (dependency-injected classifier)."""
    settings = settings or get_settings()
    if classifier is None:
        from app.llm.parsers import structured

        classifier = structured(ReplyClassification, model=settings.llm_model)
    return classifier.invoke(_classify_prompt(lead, reply_text))


def apply_reply(
    lead: Lead,
    reply_text: str,
    *,
    channel: str = "email",
    classifier=None,
    settings=None,
) -> tuple[Lead, ReplyClassification]:
    """Classify an inbound reply, record it on the lead, and advance the stage per §10."""
    result = classify_reply(lead, reply_text, classifier=classifier, settings=settings)
    now = datetime.now(tz=timezone.utc)
    message = Message(
        role="prospect", channel=channel, text=reply_text,
        category=result.category, timestamp=now,
    )
    updated = lead.model_copy(
        update={
            "messages": [*lead.messages, message],
            "last_response_category": result.category,
            "stage": next_stage(result.category, lead.stage),
            "updated_at": now,
        }
    )
    return updated, result


def run(state: PipelineState) -> dict:
    # Graph-path adapter: classification is inbound-triggered, so the canonical driver is
    # POST /leads/{id}/reply operating on the store. Nothing to do in a batch sweep.
    return {}
