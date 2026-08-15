"""Shared FastAPI dependencies."""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings  # re-exported for routers

__all__ = ["get_settings", "get_graph"]


@lru_cache
def get_graph():
    """Compiled LangGraph pipeline (built once, reused)."""
    from app.graph.build import build_graph

    return build_graph()


# TODO(Phase 10): def get_repo() -> LeadRepository backed by Supabase.
