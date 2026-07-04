"""Construccion de prompts para el LLM.

Arma el prompt de sistema (rol + reglas anti-alucinacion + instruccion de citar
fuentes) y el prompt de usuario (contexto recuperado + historial reciente +
pregunta actual). Centralizar esto aqui mantiene el prompt versionado y testeable.
"""
from __future__ import annotations

SYSTEM_PROMPT = (
    "Eres un asistente que responde preguntas sobre la informacion publicada "
    "en el sitio web de un banco. Responde SIEMPRE en espanol, de forma clara y "
    "concisa. Usa UNICAMENTE la informacion del CONTEXTO proporcionado; si el "
    "contexto no contiene la respuesta, dilo con honestidad y no inventes datos. "
    "Cuando uses informacion del contexto, cita la fuente indicando el titulo o "
    "la URL correspondiente."
)


class PromptBuilder:
    @staticmethod
    def build_context(chunks: list[dict]) -> str:
        if not chunks:
            return "(No se encontro informacion relevante en el sitio.)"
        bloques = []
        for i, chunk in enumerate(chunks, start=1):
            fuente = chunk.get("title") or chunk.get("url", "fuente desconocida")
            url = chunk.get("url", "")
            bloques.append(
                f"[{i}] Fuente: {fuente} ({url})\n{chunk.get('text', '')}"
            )
        return "\n\n".join(bloques)

    @staticmethod
    def build_history(history: list[dict]) -> str:
        if not history:
            return ""
        lineas = []
        for turno in history:
            rol = "Usuario" if turno.get("role") == "user" else "Asistente"
            lineas.append(f"{rol}: {turno.get('content', '')}")
        return "\n".join(lineas)

    def build_user_prompt(
        self, question: str, chunks: list[dict], history: list[dict]
    ) -> str:
        context = self.build_context(chunks)
        history_text = self.build_history(history)

        partes = [f"CONTEXTO:\n{context}"]
        if history_text:
            partes.append(f"HISTORIAL DE LA CONVERSACION:\n{history_text}")
        partes.append(f"PREGUNTA ACTUAL:\n{question}")
        partes.append("RESPUESTA:")
        return "\n\n".join(partes)