"""RAG layer (§1, §2) — PDF/text ingestion -> Chroma -> retrieval — Phase 2.

Every module here imports its heavy dependency (PyMuPDF/sentence-transformers/chromadb)
LAZILY inside functions, so importing the package never blocks the API from booting.
"""
