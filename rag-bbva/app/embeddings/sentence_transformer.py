"""Embeddings con sentence-transformers (local, gratis, multilingue).

Detalle importante: los modelos de la familia e5 (como multilingual-e5) rinden
mucho mejor si se les antepone "query: " a las consultas y "passage: " a los
documentos. Esta clase lo maneja automaticamente segun el nombre del modelo.

El modelo se carga de forma perezosa en __init__ (es un recurso caro): se
instancia una sola vez y se reutiliza.
"""
from __future__ import annotations

from app.embeddings.base import Embedder


def _apply_prefix(text: str, kind: str, is_e5: bool) -> str:
    """Antepone el prefijo e5 ('query'/'passage') solo si el modelo lo requiere."""
    return f"{kind}: {text}" if is_e5 else text


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str) -> None:
        # Import perezoso: evita cargar torch si nunca se usa el embedder.
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._is_e5 = "e5" in model_name.lower()
        self._model = SentenceTransformer(model_name)

    @property
    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        prepared = [_apply_prefix(t, "passage", self._is_e5) for t in texts]
        vectors = self._model.encode(
            prepared,
            normalize_embeddings=True,   # cosine == dot product
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        prepared = _apply_prefix(text, "query", self._is_e5)
        vector = self._model.encode(
            prepared,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vector.tolist()
