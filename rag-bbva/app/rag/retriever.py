"""Recuperador: convierte la pregunta en vector y trae los chunks relevantes."""
from __future__ import annotations

from app.embeddings.base import Embedder
from app.vectorstore.qdrant_store import QdrantStore


class Retriever:
    def __init__(self, embedder: Embedder, store: QdrantStore, top_k: int) -> None:
        self.embedder = embedder
        self.store = store
        self.top_k = top_k

    def retrieve(self, query: str) -> list[dict]:
        query_vector = self.embedder.embed_query(query)
        return self.store.search(query_vector=query_vector, top_k=self.top_k)
