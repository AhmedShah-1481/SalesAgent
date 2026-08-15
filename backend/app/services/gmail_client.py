"""Gmail API client (send outreach email) — Phase 6.

Real send uses OAuth (GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN + GMAIL_SENDER) via the
google-api-python-client. §9/§10 allow simulation instead of real sending, and that is the
default: EMAIL_MODE=simulate logs the email and returns a 'simulated' result with no network
call and no extra dependency. The real-send path imports googleapiclient lazily, so the app
boots — and simulate mode works — on requirements-base.txt alone. Sync (the Gmail client is
synchronous); callers run it in a threadpool like every other service client.
"""
from __future__ import annotations

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_GMAIL_KEYS = ("gmail_client_id", "gmail_client_secret", "gmail_refresh_token", "gmail_sender")


def send_email(to: str | None, subject: str, body: str, *, settings=None) -> dict:
    """Send (or simulate) an outreach email. Returns a status dict; never raises when simulating."""
    settings = settings or get_settings()

    if settings.email_mode != "send":
        logger.info("[EMAIL SIMULATE] to=%s | subject=%s", to or "(no address)", subject)
        return {"status": "simulated", "to": to, "subject": subject}

    if not to:
        return {"status": "skipped", "reason": "no recipient email", "subject": subject}

    missing = [k for k in _GMAIL_KEYS if not getattr(settings, k)]
    if missing:
        raise RuntimeError(f"EMAIL_MODE=send but missing Gmail settings: {', '.join(missing)}")

    return _send_via_gmail(to, subject, body, settings)


def _send_via_gmail(to: str, subject: str, body: str, settings) -> dict:
    import base64
    from email.mime.text import MIMEText

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:  # optional deps, only needed for real sending
        raise RuntimeError(
            "EMAIL_MODE=send requires 'google-api-python-client' and 'google-auth' "
            "(pip install google-api-python-client google-auth)."
        ) from exc

    creds = Credentials(
        None,
        refresh_token=settings.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    msg = MIMEText(body)
    msg["to"] = to
    msg["from"] = settings.gmail_sender
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info("[EMAIL SENT] to=%s id=%s", to, sent.get("id"))
    return {"status": "sent", "to": to, "id": sent.get("id")}
