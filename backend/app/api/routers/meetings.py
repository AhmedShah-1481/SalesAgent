"""Meeting scheduling + admin reminder endpoints (§12) — Phase 8.

POST /leads/{id}/schedule-meeting finalizes a meeting for an INTERESTED lead: it picks a fixed
time, provides a meeting link (simulated or real Google Meet per MEETING_MODE), replies to the
prospect with the link + time (§11), notifies the admin over WhatsApp with a briefing (§12), and
stores the meeting. GET /meetings lists stored meetings; POST /meetings/reminders/run drives the
30-min admin reminder on demand (the scheduler does this automatically; ``?force=true`` fires it
now for the demo). Phase 10 swaps the store for Supabase behind the same shapes, so these stay put.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.events import event_bus
from app.core.logging import get_logger
from app.graph.nodes.meeting import finalize_meeting, run_reminders
from app.memory.store import get_store
from app.schemas.activity import ActivityEvent
from app.schemas.enums import PipelineStage
from app.schemas.lead import Lead
from app.schemas.meeting import Meeting

router = APIRouter(tags=["meetings"])
logger = get_logger(__name__)


class ScheduleMeetingBody(BaseModel):
    """Optional overrides for POST /leads/{id}/schedule-meeting."""

    when: datetime | None = Field(
        None, description="Explicit meeting time (UTC); default is a fixed slot a few days out."
    )


class MeetingResult(BaseModel):
    """Response for POST /leads/{id}/schedule-meeting."""

    meeting: Meeting
    lead: Lead
    emailed: bool = Field(description="Whether a confirmation email was sent/simulated (§11)")


class ReminderRunResult(BaseModel):
    """Response for POST /meetings/reminders/run (§12 admin reminder sweep)."""

    reminded: int = Field(description="Meetings the admin was reminded about this run")
    pending: int = Field(description="Stored meetings still awaiting a reminder")
    meetings: list[Meeting] = Field(default_factory=list)


def _finalize(lead: Lead, when: datetime | None, settings):
    return finalize_meeting(lead, when=when, settings=settings)


@router.post("/leads/{lead_id}/schedule-meeting", response_model=MeetingResult)
async def schedule_meeting(lead_id: str, body: ScheduleMeetingBody | None = None) -> MeetingResult:
    """Finalize a meeting (§12): link + fixed time, prospect confirm (§11), admin briefing."""
    store = get_store()
    lead = store.get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail=f"No lead with id '{lead_id}'.")

    settings = get_settings()
    when = body.when if body else None
    try:
        updated, meeting, log = await run_in_threadpool(_finalize, lead, when, settings)
    except RuntimeError as exc:  # e.g. MEETING_MODE=create without Calendar creds/libs
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Meeting scheduling failed")
        raise HTTPException(status_code=502, detail=f"Scheduling failed: {exc}") from exc

    store.upsert_lead(updated)
    store.upsert_meeting(meeting)
    if log is not None:
        store.add_outreach_logs([log])
    event_bus.publish(
        ActivityEvent(
            kind="meeting",
            message=f"Meeting scheduled with {updated.company_name} "
            f"({meeting.contact_name or 'contact'}); admin briefed.",
            stage=PipelineStage.MEETING_SCHEDULED.value,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )
    return MeetingResult(meeting=meeting, lead=updated, emailed=log is not None)


@router.get("/meetings", response_model=list[Meeting])
def list_meetings() -> list[Meeting]:
    """Every finalized meeting (company, contact, time, link, briefing, reminder status)."""
    return get_store().list_meetings()


def _run_reminders(meetings: list[Meeting], force: bool, settings) -> list[Meeting]:
    return run_reminders(meetings, force=force, settings=settings)


@router.post("/meetings/reminders/run", response_model=ReminderRunResult)
async def run_meeting_reminders(force: bool = False) -> ReminderRunResult:
    """Send the admin the 30-min briefing reminder for any due meeting (§12).

    The scheduler runs this automatically near each meeting; ``?force=true`` fires it now (demo).
    """
    store = get_store()
    meetings = store.list_meetings()
    if not meetings:
        raise HTTPException(
            status_code=400, detail="No meetings scheduled — POST /leads/{id}/schedule-meeting."
        )

    settings = get_settings()
    try:
        reminded = await run_in_threadpool(_run_reminders, meetings, force, settings)
    except Exception as exc:
        logger.exception("Meeting-reminder run failed")
        raise HTTPException(status_code=502, detail=f"Reminder run failed: {exc}") from exc

    for meeting in reminded:
        store.upsert_meeting(meeting)
    if reminded:
        event_bus.publish(
            ActivityEvent(
                kind="meeting_reminder",
                message=f"Admin reminded about {len(reminded)} upcoming meeting(s).",
                stage=PipelineStage.MEETING_SCHEDULED.value,
                timestamp=datetime.now(tz=timezone.utc),
            )
        )
    pending = sum(1 for m in store.list_meetings() if not m.reminder_sent)
    return ReminderRunResult(reminded=len(reminded), pending=pending, meetings=reminded)
