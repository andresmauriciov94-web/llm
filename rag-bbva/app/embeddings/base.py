"""Interfaz de embeddings (patron Strategy).

Define el contrato que cualquier proveedor de embeddings debe cumplir. Permite
intercambiar la implementacion (sentence-transformers, OpenAI, etc.) sin tocar
la logica de ingesta ni de recuperacion.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Embedder(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimension de los vectores que produce (necesaria para Qdrant)."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Vectoriza una lista de textos (documentos/chunks)."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Vectoriza una consulta del usuario."""
