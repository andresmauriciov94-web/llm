"""Reranker: reordena los chunks recuperados por relevancia real (bonus).

Tras la búsqueda vectorial (que es rápida pero aproximada), un cross-encoder
evalúa cada par (pregunta, chunk) de forma conjunta y produce un score de
relevancia más preciso. Se reordena por ese score y se recorta a `top_n`, de
modo que el LLM reciba solo los fragmentos realmente pertinentes.

Sigue el patrón Strategy (interfaz + implementación) para poder desactivarlo o
cambiar de modelo sin tocar el pipeline. El modelo se carga de forma perezosa.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, chunks: list[dict], top_n: int) -> list[dict]:
        """Devuelve los `top_n` chunks más relevantes, reordenados."""


class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str) -> None:
        # Import perezoso: no carga torch si el reranker está desactivado.
        from sentence_transformers import CrossEncoder

        self.model_name = model_name
        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: list[dict], top_n: int) -> list[dict]:
        if not chunks:
            return []
        pairs = [(query, chunk.get("text", "")) for chunk in chunks]
        scores = self._model.predict(pairs)

        ranked = sorted(
            zip(chunks, scores), key=lambda pair: pair[1], reverse=True
        )
        result: list[dict] = []
        for chunk, score in ranked[:top_n]:
            enriched = dict(chunk)
            enriched["rerank_score"] = float(score)
            result.append(enriched)
        return result
