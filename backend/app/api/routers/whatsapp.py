"""Inbound WhatsApp webhook (§9/§10) — the isolated Node microservice POSTs here.

This is one of the two HTTP seams to the Node service (the other is outbound
``POST {WHATSAPP_SERVICE_URL}/send-whatsapp``). Every inbound prospect message funnels through the
SAME classification sink as email replies (``apply_reply`` with ``channel="whatsapp"``), so WhatsApp
and email share one classifier and one stage-transition table. Messages that don't map to a known
lead (or that come from the admin) are logged to the activity feed and acknowledged — nothing is
lost, and unknown senders never spuriously advance a lead.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.core.events import event_bus
from app.core.logging import get_logger
from app.core.phone import phones_match
from app.graph.nodes.response_classification import apply_reply
from app.memory.store import get_store
from app.schemas.activity import ActivityEvent
from app.schemas.lead import Lead

router = APIRouter(tags=["whatsapp"])
logger = get_logger(__name__)


class IncomingWhatsApp(BaseModel):
    """Payload the Node forwarder POSTs for each inbound WhatsApp message."""

    model_config = ConfigDict(populate_by_name=True)

    text: str = Field("", description="Message body")
    phone: str = Field("", description="Sender number (digits); may also arrive via 'from' JID")
    from_: str = Field("", alias="from", description="Full WhatsApp JID, e.g. 123@s.whatsapp.net")
    push_name: str = Field("", alias="pushName", description="Sender display name, if any")
    message_id: str = Field("", alias="messageId")


def _classify(lead: Lead, text: str, settings):
    return apply_reply(lead, text, channel="whatsapp", settings=settings)


def _publish(message: str, *, lead_id: str | None = None, stage: str | None = None) -> None:
    event_bus.publish(
        ActivityEvent(
            kind="whatsapp_in",
            message=message,
            lead_id=lead_id,
            stage=stage,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )


@router.post("/whatsapp-incoming")
async def whatsapp_incoming(msg: IncomingWhatsApp) -> dict:
    """Classify an inbound WhatsApp reply (§10) and advance the matching lead's stage (§11)."""
    number = msg.phone or msg.from_
    text = msg.text.strip()
    if not text:
        return {"status": "ignored", "reason": "empty message"}

    settings = get_settings()
    store = get_store()

    # Admin messages aren't prospect replies — surface them, but never run the classifier on them.
    if settings.admin_whatsapp_number and phones_match(number, settings.admin_whatsapp_number):
        _publish(f"Admin WhatsApp: {text[:80]}")
        return {"status": "received", "matched": False, "admin": True}

    lead = store.get_lead_by_phone(number)
    if lead is None:
        sender = msg.push_name or number or "unknown"
        logger.info("whatsapp-incoming: no lead matches %s", number)
        _publish(f"Unmatched WhatsApp from {sender}: {text[:80]}")
        return {"status": "received", "matched": False}

    try:
        updated, classification = await run_in_threadpool(_classify, lead, text, settings)
    except RuntimeError as exc:  # e.g. no LLM provider configured
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("WhatsApp reply classification failed")
        raise HTTPException(status_code=502, detail=f"Classification failed: {exc}") from exc

    store.upsert_lead(updated)
    _publish(
        f"{updated.company_name} replied on WhatsApp — '{classification.category.value}' "
        f"-> {updated.stage.value}.",
        lead_id=updated.id,
        stage=updated.stage.value,
    )
    return {
        "status": "classified",
        "matched": True,
        "lead_id": updated.id,
        "category": classification.category.value,
        "stage": updated.stage.value,
    }
