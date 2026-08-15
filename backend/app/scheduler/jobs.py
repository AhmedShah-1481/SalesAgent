"""APScheduler jobs — 3-day follow-up sweep (§11) + 30-min meeting reminder sweep (§12).

A single BackgroundScheduler singleton runs in its own thread. ``start_follow_up_sweeps()``
registers a periodic job that scans CONTACTED leads and sends Email #2 to any that are due (no
reply after ``follow_up_wait_days``). ``start_meeting_reminders()`` registers a second job that
scans stored meetings and pings the admin ~30 minutes before each (§12). Both are best-effort: the
app boots and the manual POST endpoints still work even if the scheduler can't start. Sweeps run off
the event loop, so they publish activity via ``event_bus.publish_threadsafe``.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_scheduler():
    """Lazily create + start a single BackgroundScheduler (thread-based, no asyncio needed)."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.start()
    return scheduler


def _sweep_follow_ups() -> None:
    """Scan CONTACTED leads and send due follow-ups (§11). Runs in the scheduler thread."""
    from datetime import datetime, timezone

    from app.core.events import event_bus
    from app.graph.nodes.follow_up import run_follow_ups
    from app.memory.store import get_store
    from app.schemas.activity import ActivityEvent
    from app.schemas.enums import PipelineStage

    store = get_store()
    contacted = store.list_leads(stage=PipelineStage.CONTACTED)
    if not contacted:
        return
    try:
        updated, logs = run_follow_ups(contacted, now=datetime.now(tz=timezone.utc))
    except Exception:
        logger.exception("Follow-up sweep failed")
        return
    if not updated:
        return

    store.upsert_many(updated)
    store.add_outreach_logs(logs)
    logger.info("Follow-up sweep sent %d Email #2(s).", len(logs))
    event_bus.publish_threadsafe(
        ActivityEvent(
            kind="follow_up",
            message=f"Follow-up sweep: {len(logs)} second-touch emails sent.",
            stage=PipelineStage.CONTACTED.value,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )


def start_follow_up_sweeps() -> None:
    """Register the periodic follow-up sweep (idempotent — replaces any existing job)."""
    settings = get_settings()
    scheduler = get_scheduler()
    scheduler.add_job(
        _sweep_follow_ups,
        "interval",
        minutes=settings.follow_up_sweep_minutes,
        id="follow_up_sweep",
        replace_existing=True,
    )
    logger.info(
        "Follow-up sweep scheduled every %d min (wait %d days, max %d follow-ups).",
        settings.follow_up_sweep_minutes,
        settings.follow_up_wait_days,
        settings.max_follow_ups,
    )


def schedule_meeting_reminder(*args, **kwargs):
    # Retained for backward-compat with earlier callers; the reminder mechanism is now the
    # periodic sweep below (start_meeting_reminders), which scans stored meetings.
    raise NotImplementedError("Use start_meeting_reminders() — reminders run via the sweep now.")


def _sweep_meeting_reminders() -> None:
    """Scan stored meetings and notify the admin ~30 min before each (§12). Scheduler thread."""
    from datetime import datetime, timezone

    from app.core.events import event_bus
    from app.graph.nodes.meeting import run_reminders
    from app.memory.store import get_store
    from app.schemas.activity import ActivityEvent
    from app.schemas.enums import PipelineStage

    store = get_store()
    meetings = store.list_meetings()
    if not meetings:
        return
    try:
        reminded = run_reminders(meetings, now=datetime.now(tz=timezone.utc))
    except Exception:
        logger.exception("Meeting-reminder sweep failed")
        return
    if not reminded:
        return

    for meeting in reminded:
        store.upsert_meeting(meeting)
    logger.info("Meeting-reminder sweep pinged admin for %d meeting(s).", len(reminded))
    event_bus.publish_threadsafe(
        ActivityEvent(
            kind="meeting_reminder",
            message=f"Meeting reminder: admin notified about {len(reminded)} upcoming meeting(s).",
            stage=PipelineStage.MEETING_SCHEDULED.value,
            timestamp=datetime.now(tz=timezone.utc),
        )
    )


def start_meeting_reminders() -> None:
    """Register the periodic meeting-reminder sweep (idempotent — replaces any existing job)."""
    settings = get_settings()
    scheduler = get_scheduler()
    scheduler.add_job(
        _sweep_meeting_reminders,
        "interval",
        minutes=settings.reminder_sweep_minutes,
        id="meeting_reminder_sweep",
        replace_existing=True,
    )
    logger.info(
        "Meeting-reminder sweep scheduled every %d min (remind %d min before meeting).",
        settings.reminder_sweep_minutes,
        settings.meeting_reminder_minutes,
    )
