"""Analitica del historico de conversaciones.

Recorre todos los mensajes persistidos (via el Repository) y calcula metricas
de impacto: volumen, latencia (p50/p95), preguntas mas frecuentes, fuentes mas
recuperadas y tasa de respuestas sin contexto (senal de cobertura del corpus).

No depende de la infra (Qdrant/LLM): solo lee SQLite, por eso puede correr como
script independiente o exponerse por la API.
"""
from __future__ import annotations

from collections import Counter

from app.memory.repository import ConversationRepository


def _percentile(values: list[float], p: float) -> float:
    """Percentil por interpolacion lineal (robusto con muestras pequenas)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    k = (len(ordered) - 1) * p
    low = int(k)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return float(ordered[low])
    return ordered[low] + (ordered[high] - ordered[low]) * (k - low)


class ConversationAnalytics:
    def __init__(self, repo: ConversationRepository) -> None:
        self.repo = repo

    def compute(self) -> dict:
        messages = self.repo.all_messages()
        sessions = {m["session_id"] for m in messages}
        user_msgs = [m for m in messages if m["role"] == "user"]
        asst_msgs = [m for m in messages if m["role"] == "assistant"]
        latencies = [
            m["latency_ms"] for m in asst_msgs if m.get("latency_ms") is not None
        ]
        no_context = [m for m in asst_msgs if not m.get("retrieved_ids")]
        prompt_tokens = sum(int(m.get("prompt_tokens") or 0) for m in asst_msgs)
        completion_tokens = sum(int(m.get("completion_tokens") or 0) for m in asst_msgs)
        total_tokens = prompt_tokens + completion_tokens

        return {
            "totales": {
                "sesiones": len(sessions),
                "mensajes": len(messages),
                "mensajes_usuario": len(user_msgs),
                "mensajes_asistente": len(asst_msgs),
                "promedio_mensajes_por_sesion": (
                    round(len(messages) / len(sessions), 2) if sessions else 0
                ),
            },
            "latencia_ms": {
                "promedio": round(sum(latencies) / len(latencies), 1) if latencies else 0,
                "p50": round(_percentile(latencies, 0.50), 1),
                "p95": round(_percentile(latencies, 0.95), 1),
                "maxima": max(latencies) if latencies else 0,
            },
            "tokens": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": total_tokens,
                "promedio_por_respuesta": (
                    round(total_tokens / len(asst_msgs), 1) if asst_msgs else 0
                ),
            },
            "cobertura": {
                "respuestas_sin_contexto": len(no_context),
                "pct_sin_contexto": (
                    round(100 * len(no_context) / len(asst_msgs), 1)
                    if asst_msgs
                    else 0
                ),
            },
            "preguntas_frecuentes": self._top_questions(user_msgs),
            "fuentes_mas_usadas": self._top_sources(asst_msgs),
        }

    @staticmethod
    def _top_questions(user_msgs: list[dict], limit: int = 5) -> list[dict]:
        counter = Counter(m["content"].strip().lower() for m in user_msgs if m["content"].strip())
        return [{"pregunta": q, "veces": c} for q, c in counter.most_common(limit)]

    @staticmethod
    def _top_sources(asst_msgs: list[dict], limit: int = 5) -> list[dict]:
        counter: Counter = Counter()
        for m in asst_msgs:
            for rid in m.get("retrieved_ids") or []:
                url = rid.split("#")[0]
                if url:
                    counter[url] += 1
        return [{"fuente": s, "veces": c} for s, c in counter.most_common(limit)]