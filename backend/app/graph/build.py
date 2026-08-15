"""LangGraph assembly — the ONE place each pipeline stage is wired in.

Adding a future phase = implement the node's ``run`` + add one ``add_node`` line here.
Phase 1 wires a simple linear happy path so the graph compiles and can be invoked
end-to-end as a no-op. Conditional edges are added at their phase:
  - qualification -> (Not Qualified branch)              [Phase 4]
  - response_classification -> follow_up loop / meeting  [Phase 7]
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    cheap_filter,
    decision_makers,
    deep_research,
    discovery,
    follow_up,
    meeting,
    outreach,
    qualification,
    response_classification,
    service_matching,
)
from app.graph.state import PipelineState
from app.memory.checkpointer import get_checkpointer

# Ordered pipeline stages: (node name, module). Order defines the linear edges.
_STAGES = [
    ("discovery", discovery),
    ("cheap_filter", cheap_filter),
    ("deep_research", deep_research),
    ("qualification", qualification),
    ("service_matching", service_matching),
    ("decision_makers", decision_makers),
    ("outreach", outreach),
    ("response_classification", response_classification),
    ("follow_up", follow_up),
    ("meeting", meeting),
]


def build_graph():
    g = StateGraph(PipelineState)

    for name, module in _STAGES:
        g.add_node(name, module.run)

    g.add_edge(START, _STAGES[0][0])
    for (prev, _), (nxt, _) in zip(_STAGES, _STAGES[1:], strict=False):
        g.add_edge(prev, nxt)
    g.add_edge(_STAGES[-1][0], END)

    return g.compile(checkpointer=get_checkpointer())
