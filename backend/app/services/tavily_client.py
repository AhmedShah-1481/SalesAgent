"""Tavily search client (primary web/company search) — Phase 3.

Synchronous by design: discovery runs inside a threadpool (like the RAG layer), so the
graph nodes stay plain sync functions. Returns a normalized result shape shared with the
Serper backup: ``[{"title", "url", "content"}]``.
"""
from __future__ import annotations

from app.config import get_settings


def search(query: str, max_results: int = 8, api_key: str | None = None) -> list[dict]:
    from tavily import TavilyClient  # lazy: keeps import cost off the boot path

    key = api_key or get_settings().tavily_api_key
    if not key:
        raise RuntimeError("TAVILY_API_KEY is not set.")

    client = TavilyClient(api_key=key)
    resp = client.search(query=query, max_results=max_results, search_depth="basic")
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        }
        for r in resp.get("results", [])
    ]
