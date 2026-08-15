"""Chroma vector store wrapper, persisted at settings.chroma_persist_dir (§1).

A single collection ("company_knowledge" by default) holds the current company's
knowledge. Uses cosine space so relevance scores are comparable and in ~[0, 1].
Optional overrides exist purely so tests can point at a throwaway directory/collection.
"""
from __future__ import annotations

from app.config import get_settings
from app.rag.embeddings import get_embeddings


def get_vectorstore(collection: str | None = None, persist_dir: str | None = None):
    from langchain_chroma import Chroma  # lazy: pulls chromadb

    settings = get_settings()
    return Chroma(
        collection_name=collection or settings.rag_collection,
        embedding_function=get_embeddings(),
        persist_directory=persist_dir or settings.chroma_persist_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )
