"""Pipeline de ingesta: documentos limpios -> chunks -> embeddings -> Qdrant.

Une las piezas de los pasos anteriores. Procesa por lotes para no cargar todos
los vectores en memoria de golpe y reporta el progreso.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.embeddings.base import Embedder
from app.ingestion.chunker import Chunker
from app.vectorstore.qdrant_store import QdrantStore


class Indexer:
    def __init__(
        self,
        chunker: Chunker,
        embedder: Embedder,
        store: QdrantStore,
        clean_dir: str,
        batch_size: int = 64,
    ) -> None:
        self.chunker = chunker
        self.embedder = embedder
        self.store = store
        self.clean_dir = Path(clean_dir)
        self.batch_size = batch_size

    def _load_clean_documents(self) -> list[dict]:
        docs: list[dict] = []
        for path in sorted(self.clean_dir.glob("*.json")):
            try:
                docs.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                print(f"[indexer] archivo ilegible, se omite: {path.name}")
        return docs

    def run(self, recreate: bool = True) -> dict:
        documents = self._load_clean_documents()
        if not documents:
            raise RuntimeError(
                "No hay documentos limpios. Ejecuta primero el scraper "
                "(python -m app.scraper.run)."
            )

        # 1) Chunking de todos los documentos
        all_chunks: list[dict] = []
        for doc in documents:
            all_chunks.extend(self.chunker.chunk_document(doc))
        print(f"[indexer] {len(documents)} documentos -> {len(all_chunks)} chunks")

        # 2) Coleccion lista (dimension segun el embedder)
        self.store.vector_size = self.embedder.dimension
        self.store.ensure_collection(recreate=recreate)

        # 3) Embeddings + upsert por lotes (un lote fallido no aborta todo)
        total = 0
        errores = 0
        for start in range(0, len(all_chunks), self.batch_size):
            batch = all_chunks[start : start + self.batch_size]
            try:
                vectors = self.embedder.embed_texts([c["text"] for c in batch])
                total += self.store.upsert_chunks(batch, vectors)
                print(f"[indexer] indexados {total}/{len(all_chunks)}")
            except Exception as exc:  # noqa: BLE001
                errores += len(batch)
                print(f"[indexer] lote {start} fallo, se omite: {type(exc).__name__}: {exc}")

        count = self.store.count()
        if errores:
            print(f"[indexer] AVISO: {errores} chunks no se indexaron por errores.")
        print(f"[indexer] Listo. Puntos en la coleccion: {count}")
        return {
            "documents": len(documents),
            "chunks": len(all_chunks),
            "indexed": count,
            "errors": errores,
        }