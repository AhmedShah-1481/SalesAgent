"""Phase 2 RAG tests: ingest a company doc, then prove grounded retrieval works.

Requires requirements-ml.txt (torch/sentence-transformers/chromadb). Environments with
only requirements-base.txt skip this file rather than failing, preserving the fast-boot
guarantee. The first run downloads the all-MiniLM-L6-v2 weights (~90 MB), then caches them.
"""
from __future__ import annotations

import pytest

pytest.importorskip("sentence_transformers")
pytest.importorskip("chromadb")
pytest.importorskip("langchain_chroma")

from app.rag.ingest import ingest_pdf, ingest_text, knowledge_stats, query_knowledge  # noqa: E402
from app.rag.vectorstore import get_vectorstore  # noqa: E402
from scripts.generate_sample_company import build as build_sample_pdf  # noqa: E402


@pytest.fixture
def tmp_store(tmp_path):
    """A throwaway Chroma collection so tests never touch the real data/chroma."""
    return get_vectorstore(collection="test_knowledge", persist_dir=str(tmp_path / "chroma"))


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory):
    out = tmp_path_factory.mktemp("sample") / "company.pdf"
    return str(build_sample_pdf(out))


def test_ingest_pdf_produces_multiple_chunks(tmp_store, sample_pdf):
    result = ingest_pdf(sample_pdf, store=tmp_store)
    assert result.doc_type == "pdf"
    assert result.pages >= 1
    assert result.chunks >= 5, "sample profile should split into several chunks"
    assert result.characters > 0


def test_grounded_retrieval_ranks_the_right_chunk(tmp_store, sample_pdf):
    ingest_pdf(sample_pdf, store=tmp_store)

    whatsapp = query_knowledge("service for high WhatsApp message volume", k=3, store=tmp_store)
    assert whatsapp.results, "expected at least one hit"
    assert "whatsapp" in whatsapp.results[0].text.lower()
    assert whatsapp.results[0].score is not None

    pricing = query_knowledge("how much does the starter plan cost", k=3, store=tmp_store)
    assert any("1,500" in c.text or "starter" in c.text.lower() for c in pricing.results)

    limits = query_knowledge("do you offer on-premise deployment", k=3, store=tmp_store)
    assert any("premise" in c.text.lower() for c in limits.results)


def test_stats_reflect_ingestion(tmp_store, sample_pdf):
    ingest_text("Sable AI sells a WhatsApp AI Chatbot.", source="blurb.txt", store=tmp_store)
    ingest_pdf(sample_pdf, store=tmp_store)
    stats = knowledge_stats(store=tmp_store)
    assert stats.total_chunks >= 6
    assert "blurb.txt" in stats.sources
    assert "company.pdf" in stats.sources
