"""Construccion de prompts para el LLM.

Arma el prompt de sistema (rol + reglas anti-alucinacion + instruccion de citar
fuentes) y el prompt de usuario (contexto recuperado + historial reciente +
pregunta actual). Centralizar esto aqui mantiene el prompt versionado y testeable.
"""
from __future__ import annotations

SYSTEM_PROMPT = (
    "Eres un asistente que responde preguntas sobre la informacion publicada en "
    "el sitio web de un banco. Responde SIEMPRE en espanol, de forma clara y "
    "concisa.\n"
    "REGLAS:\n"
    "1. Usa UNICAMENTE la informacion de los bloques del CONTEXTO. Cada bloque "
    "viene numerado como [1], [2], etc.\n"
    "2. Cuando uses un bloque, cita su numero en linea, por ejemplo: 'la cuenta "
    "no cobra cuota [1]'.\n"
    "3. Al final, agrega una linea 'Fuentes:' listando los titulos o URLs de los "
    "bloques que realmente usaste.\n"
    "4. Si el CONTEXTO no contiene la respuesta, dilo con honestidad "
    "('No encontre esa informacion en el sitio') y NO inventes datos."
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
