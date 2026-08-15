"""Phase 1 smoke tests: the app boots, /health is green, and the graph compiles + runs.

These deliberately require only requirements-base.txt (no torch/chroma).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root_ok():
    r = client.get("/")
    assert r.status_code == 200
    assert "name" in r.json()


def test_graph_compiles_and_runs_noop():
    """Compile the full pipeline and run it end-to-end as a no-op.

    Every node is a pass-through in Phase 1, so seeding just a company name must
    flow through untouched and the reducer-backed channels must initialize to [].
    (Invoking with a literal ``{}`` writes no channel and LangGraph returns None —
    not a realistic call, since the pipeline always starts from a company.)
    """
    from app.graph.build import build_graph

    graph = build_graph()
    result = graph.invoke(
        {"company_name": "Acme Corp"},
        config={"configurable": {"thread_id": "smoke-test"}},
    )
    assert isinstance(result, dict)
    assert result["company_name"] == "Acme Corp"
    # add / add_messages reducers seed empty lists across the pipeline state.
    for channel in ("leads", "messages", "activity", "errors"):
        assert result[channel] == []


def test_pipeline_stage_enum_matches_spec():
    from app.schemas.enums import PipelineStage

    values = {s.value for s in PipelineStage}
    # §15 positive lifecycle + negative outcomes
    assert {"Discovered", "Qualified", "Meeting Scheduled", "Converted"} <= values
    assert {"Not Qualified", "Not Interested", "Do Not Contact"} <= values
