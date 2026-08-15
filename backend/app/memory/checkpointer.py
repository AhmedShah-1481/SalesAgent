"""Short-term memory: LangGraph checkpointer.

Phase 1: in-memory ``MemorySaver`` (zero file dependency, boots instantly).
Phase 10: swap to a persistent ``SqliteSaver`` at ``settings.checkpoint_db_path``.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver


@lru_cache
def get_checkpointer():
    # TODO(Phase 10): persist across restarts, e.g.
    #   from langgraph.checkpoint.sqlite import SqliteSaver
    #   return SqliteSaver.from_conn_string(get_settings().checkpoint_db_path)
    return MemorySaver()
