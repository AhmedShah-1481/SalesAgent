"""Best-effort website text fetch to enrich the research dossier (§4) — Phase 4.

Deliberately lightweight and resilient: a short-timeout httpx GET plus a crude HTML->text
reduction. It never raises — on any failure (timeout, block, non-HTML) it returns "" so
deep research falls back to search evidence. Good enough for static/SSR marketing sites;
a Playwright backend can be swapped in here later for JS-heavy pages without touching
callers (the earmarked `playwright` dep in requirements-ml.txt).
"""
from __future__ import annotations

import re

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

_SCRIPT_STYLE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _html_to_text(html: str) -> str:
    text = _SCRIPT_STYLE.sub(" ", html)
    text = _TAGS.sub(" ", text)
    text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)  # strip HTML entities
    return _WS.sub(" ", text).strip()


def scrape(url: str, *, max_chars: int = 4000, timeout: float = 12.0) -> str:
    """Return visible text from ``url`` (truncated), or "" on any failure."""
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    try:
        resp = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AgentHackBot/1.0)"},
        )
        resp.raise_for_status()
        if "text/html" not in resp.headers.get("content-type", ""):
            return ""
        return _html_to_text(resp.text)[:max_chars]
    except Exception as exc:  # network, block, bad HTML — enrichment is optional
        logger.info("Website scrape skipped for %s (%s)", url, exc)
        return ""
