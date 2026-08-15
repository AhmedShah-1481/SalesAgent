"""Serper (google.serper.dev) search client — backup for Tavily — Phase 3.

A thin sync wrapper over the Serper `/search` endpoint via httpx. Normalizes the
`organic` results to the same shape Tavily returns: ``[{"title", "url", "content"}]``.
"""
from __future__ import annotations

import httpx

from app.config import get_settings

_ENDPOINT = "https://google.serper.dev/search"


def search(query: str, num: int = 8, api_key: str | None = None) -> list[dict]:
    key = api_key or get_settings().serper_api_key
    if not key:
        raise RuntimeError("SERPER_API_KEY is not set.")

    resp = httpx.post(
        _ENDPOINT,
        headers={"X-API-KEY": key, "Content-Type": "application/json"},
        json={"q": query, "num": num},
        timeout=20.0,
    )
    resp.raise_for_status()
    organic = resp.json().get("organic", [])
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("link", ""),
            "content": r.get("snippet", ""),
        }
        for r in organic
    ]
