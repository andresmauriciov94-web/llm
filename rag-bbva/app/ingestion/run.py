"""Entrypoint de la ingesta.

Uso:
    python -m app.ingestion.run
"""
from __future__ import annotations

from app.config import get_settings
from app.embeddings.sentence_transformer import SentenceTransformerEmbedder
from app.ingestion.chunker import Chunker
from app.ingestion.indexer import Indexer
from app.vectorstore.qdrant_store import QdrantStore


def main() -> None:
    settings = get_settings()

    print(f"[ingesta] cargando embedder: {settings.embedding_model}")
    embedder = SentenceTransformerEmbedder(settings.embedding_model)

    chunker = Chunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    store = QdrantStore(
        url=settings.qdrant_url,
        collection_name=settings.collection_name,
        vector_size=embedder.dimension,
    )

    indexer = Indexer(
        chunker=chunker,
        embedder=embedder,
        store=store,
        clean_dir=settings.clean_dir,
    )
    result = indexer.run(recreate=True)
    print(f"[ingesta] resumen -> {result}")


if __name__ == "__main__":
    main()
