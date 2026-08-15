"""HTTP client for the isolated WhatsApp Node microservice.

Python treats WhatsApp exactly like Tavily/Gmail — a plain outbound HTTP call. This
is the ONLY way the Python backend talks to WhatsApp; no Baileys/Node code lives here.
The async ``send_whatsapp`` is the inbound-era client wired fully in Phase 9. ``notify_admin``
(Phase 8, §12) is a sync, best-effort admin channel used by the meeting flow: if the Node
service isn't reachable/connected yet, it degrades to a log so meeting automation still works
end-to-end today — Phase 9 makes the same call actually deliver over WhatsApp.
"""
from __future__ import annotations

import httpx

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_whatsapp(to: str, message: str) -> dict:
    settings = get_settings()
    url = f"{settings.whatsapp_service_url}/send-whatsapp"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json={"to": to, "message": message})
        resp.raise_for_status()
        return resp.json()


def notify_admin(message: str, *, settings=None) -> dict:
    """Best-effort admin WhatsApp notification (§12). Never raises: degrades to a log when the
    WhatsApp service is unset/unreachable/not-yet-connected (Phase 9 makes it deliver)."""
    settings = settings or get_settings()
    to = settings.admin_whatsapp_number
    headline = message.splitlines()[0] if message else ""
    if not to:
        logger.info("[ADMIN SIMULATE] (no ADMIN_WHATSAPP_NUMBER) %s", headline)
        return {"status": "simulated", "reason": "no admin number"}
    url = f"{settings.whatsapp_service_url}/send-whatsapp"
    try:
        resp = httpx.post(url, json={"to": to, "message": message}, timeout=5)
        resp.raise_for_status()
        logger.info("[ADMIN NOTIFIED] WhatsApp -> %s", to)
        return {"status": "sent", "to": to}
    except Exception as exc:  # service down / not connected yet (Phase 9)
        logger.info("[ADMIN SIMULATE] WhatsApp unavailable (%s) — %s", exc, headline)
        return {"status": "simulated", "to": to}
