"""Pipeline nodes — one module per stage. Each exposes ``run(state) -> dict``.

Phase 1: every node is a pass-through stub returning ``{}`` so the graph compiles
and runs end-to-end with no side effects.
"""
