"""Unified web search — picks a provider and degrades gracefully — Phase 3.

Discovery calls ``search_web`` and doesn't care which provider answered. Selection:
  - "tavily" / "serper": force that provider.
  - "auto" (default): prefer Tavily, fall back to Serper if Tavily has no key or errors.
Raises a clear RuntimeError when no provider is configured, so the API can surface a
helpful 400 instead of crashing.
"""
from __future__ import annotations

from app.config import get_settings
from app.core.logging import get_logger
from app.services import serper_client, tavily_client

logger = get_logger(__name__)


def search_web(query: str, *, max_results: int = 8, settings=None) -> list[dict]:
    settings = settings or get_settings()
    provider = (settings.discovery_search_provider or "auto").lower()

    if provider == "tavily":
        return tavily_client.search(query, max_results=max_results)
    if provider == "serper":
        return serper_client.search(query, num=max_results)

    # auto: try Tavily first, then Serper.
    if settings.tavily_api_key:
        try:
            return tavily_client.search(query, max_results=max_results)
        except Exception as exc:  # network / quota — fall through to Serper
            logger.warning("Tavily search failed (%s); trying Serper.", exc)
    if settings.serper_api_key:
        return serper_client.search(query, num=max_results)

    raise RuntimeError(
        "No search provider configured — set TAVILY_API_KEY or SERPER_API_KEY."
    )
