"""Proveedor de LLM basado en Ollama (local, gratis, por defecto).

Habla con el endpoint /api/chat de un servidor Ollama. Maneja errores de red y
de servicio con mensajes claros en vez de dejar escapar excepciones crudas.
"""
from __future__ import annotations

import httpx

from app.llm.base import GenerationResult, LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float = 0.1,
        max_tokens: int = 512,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def generate(self, system_prompt: str, user_prompt: str) -> GenerationResult:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama respondio {exc.response.status_code}. "
                f"Verifica que el modelo '{self.model}' este descargado "
                f"(ollama pull {self.model})."
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"No se pudo conectar con Ollama en {self.base_url}. "
                "Verifica que el servicio este arriba."
            ) from exc

        data = resp.json()
        return GenerationResult(
            text=data.get("message", {}).get("content", "").strip(),
            prompt_tokens=int(data.get("prompt_eval_count", 0) or 0),
            completion_tokens=int(data.get("eval_count", 0) or 0),
        )
