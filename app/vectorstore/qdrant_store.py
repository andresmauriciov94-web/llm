"""Adapter sobre el cliente de Qdrant (patron Adapter).

Encapsula todos los detalles de Qdrant (crear coleccion, upsert, busqueda)
detras de una interfaz propia y simple. El resto del sistema no conoce el
cliente de Qdrant directamente, lo que permite cambiar de motor vectorial sin
tocar la logica de ingesta ni de recuperacion.

Soporta modo servidor (url http) y modo en memoria (":memory:") util para
pruebas o ejecucion 100% local sin levantar el contenedor.
"""
from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class QdrantStore:
    def __init__(self, url: str, collection_name: str, vector_size: int) -> None:
        if url == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(url=url)
        self.collection = collection_name
        self.vector_size = vector_size

    # -- coleccion ---------------------------------------------------------
    def ensure_collection(self, recreate: bool = False) -> None:
        exists = self.client.collection_exists(self.collection)
        if exists and recreate:
            self.client.delete_collection(self.collection)
            exists = False
        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
            )

    # -- escritura ---------------------------------------------------------
    @staticmethod
    def _point_id(url: str, chunk_index: int) -> str:
        # ID determinista: reingestar el mismo chunk sobreescribe, no duplica.
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{url}#{chunk_index}"))

    def upsert_chunks(
        self, chunks: list[dict], vectors: list[list[float]]
    ) -> int:
        points = [
            PointStruct(
                id=self._point_id(chunk["url"], chunk["chunk_index"]),
                vector=vector,
                payload={
                    "url": chunk["url"],
                    "title": chunk["title"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        self.client.upsert(collection_name=self.collection, points=points)
        return len(points)

    # -- lectura -----------------------------------------------------------
    def search(self, query_vector: list[float], top_k: int) -> list[dict]:
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        return [
            {"score": point.score, **point.payload} for point in response.points
        ]

    def count(self) -> int:
        return self.client.count(collection_name=self.collection, exact=True).count