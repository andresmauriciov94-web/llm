"""Interfaz de proveedor de LLM (patron Strategy).

Define el contrato comun para cualquier LLM. Gracias a esto, el pipeline RAG
genera respuestas sin saber si por detras hay Ollama, OpenAI u otro proveedor:
todos exponen el mismo metodo `generate`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Genera una respuesta a partir de un prompt de sistema y de usuario."""