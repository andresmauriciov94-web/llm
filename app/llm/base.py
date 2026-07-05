"""Interfaz de proveedor de LLM (patron Strategy).

Define el contrato comun para cualquier LLM. `generate` devuelve un
`GenerationResult` con el texto y el conteo de tokens, de modo que el rastreo de
tokens es transversal a cualquier proveedor (Ollama, OpenAI, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GenerationResult:
    """Resultado de una generacion: texto + tokens consumidos."""
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> GenerationResult:
        """Genera una respuesta (texto + tokens) a partir de los prompts."""