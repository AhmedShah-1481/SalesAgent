"""Retrieve grounding context so downstream decisions cite the company knowledge (§1, §6).

``retrieve`` returns (Document, relevance) pairs for display/inspection; ``get_retriever``
returns a plain LangChain retriever that later nodes (research, qualification, service
matching, outreach) will inject to stay grounded — "no inventing facts".
"""
from __future__ import annotations

from langchain_core.documents import Document

from app.config import get_settings
from app.rag.vectorstore import get_vectorstore


def retrieve(query: str, k: int | None = None, store=None) -> list[tuple[Document, float]]:
    store = store or get_vectorstore()
    k = k or get_settings().rag_top_k
    return store.similarity_search_with_relevance_scores(query, k=k)


def get_retriever(k: int | None = None, store=None):
    store = store or get_vectorstore()
    return store.as_retriever(search_kwargs={"k": k or get_settings().rag_top_k})
