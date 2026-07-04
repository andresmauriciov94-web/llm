"""Factory de proveedores de LLM (patron Factory Method).

Unico punto de creacion: decide que implementacion instanciar segun la config
(LLM_PROVIDER) e inyecta sus parametros. El resto del sistema pide "un LLM" sin
conocer los detalles de construccion de cada proveedor.
"""
from __future__ import annotations

from app.config import Settings
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider


def create_llm(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider.lower()

    if provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    if provider == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key or "",
            model=settings.llm_model,
            base_url=settings.openai_base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

    raise ValueError(
        f"LLM_PROVIDER '{settings.llm_provider}' no soportado. "
        "Usa 'ollama' u 'openai'."
    )