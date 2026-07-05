"""Proveedor de LLM basado en la API de OpenAI (o compatible).

Es el modo "swappable": cambiando LLM_PROVIDER=openai en el .env, el sistema usa
esta implementacion sin tocar el resto del codigo (gracias al patron Strategy).
Sirve tambien para endpoints compatibles (Together, Groq, etc.) via OPENAI_BASE_URL.
"""
from __future__ import annotations

import httpx

from app.llm.base import GenerationResult, LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 512,
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY es requerida cuando LLM_PROVIDER=openai."
            )
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def generate(self, system_prompt: str, user_prompt: str) -> GenerationResult:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"La API respondio {exc.response.status_code}. "
                "Revisa la API key, el modelo y el saldo."
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"No se pudo conectar con {self.base_url}."
            ) from exc

        data = resp.json()
        usage = data.get("usage", {}) or {}
        return GenerationResult(
            text=data["choices"][0]["message"]["content"].strip(),
            prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage.get("completion_tokens", 0) or 0),
        )