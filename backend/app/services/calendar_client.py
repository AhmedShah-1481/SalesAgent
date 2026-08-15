"""Google Calendar + Meet client — Phase 8.

Only used when MEETING_MODE=create. Simulate mode (the default) never calls this, so the app
boots and the meeting flow demos without Google credentials. Google libraries are imported
lazily so they stay out of requirements-base.txt. Sync (like the Gmail client); callers run it
in a threadpool.
"""
from __future__ import annotations

from datetime import datetime

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_calendar_event(
    summary: str,
    start: datetime,
    end: datetime,
    attendees: list[str] | None = None,
    *,
    settings=None,
) -> dict:
    """Create a Calendar event with a Meet link. Returns {status, meeting_link, event_id}."""
    settings = settings or get_settings()
    if not settings.google_calendar_credentials:
        raise RuntimeError(
            "MEETING_MODE=create but GOOGLE_CALENDAR_CREDENTIALS (path to creds JSON) is unset."
        )
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:  # optional deps, only needed for real event creation
        raise RuntimeError(
            "MEETING_MODE=create requires 'google-api-python-client' and 'google-auth' "
            "(pip install google-api-python-client google-auth)."
        ) from exc

    creds = Credentials.from_service_account_file(
        settings.google_calendar_credentials,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    event = {
        "summary": summary,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
        "attendees": [{"email": a} for a in (attendees or []) if a],
        "conferenceData": {
            "createRequest": {
                "requestId": f"{summary}-{start.isoformat()}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    created = (
        service.events()
        .insert(calendarId="primary", body=event, conferenceDataVersion=1)
        .execute()
    )
    link = created.get("hangoutLink") or created.get("htmlLink")
    logger.info("[MEETING CREATED] %s", link)
    return {"status": "created", "meeting_link": link, "event_id": created.get("id")}
