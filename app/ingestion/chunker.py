"""Divide los documentos limpios en fragmentos (chunks) con solapamiento.

Estrategia: se respeta el limite de parrafo y oracion siempre que se pueda
(evita cortar a mitad de palabra), empacando unidades hasta `chunk_size` y
arrastrando un solapamiento de `chunk_overlap` caracteres entre chunks para no
perder contexto en las fronteras.
"""
from __future__ import annotations

import re


def _normalize_ws(text: str) -> str:
    """Colapsa espacios dentro de cada linea, conserva saltos como separadores."""
    text = text.replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


class Chunker:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap debe ser menor que chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> list[str]:
        text = _normalize_ws(text)
        if not text:
            return []

        units = self._split_units(text)
        chunks: list[str] = []
        current = ""

        for unit in units:
            candidate = f"{current} {unit}".strip() if current else unit
            if len(candidate) <= self.chunk_size or not current:
                current = candidate
            else:
                chunks.append(current)
                tail = self._overlap_tail(current)
                current = f"{tail} {unit}".strip() if tail else unit

        if current:
            chunks.append(current)
        return chunks

    def chunk_document(self, doc: dict) -> list[dict]:
        """Convierte un documento limpio en una lista de chunks con metadatos."""
        chunks = self.chunk_text(doc.get("text", ""))
        return [
            {
                "url": doc.get("url", ""),
                "title": doc.get("title", ""),
                "chunk_index": i,
                "text": chunk,
            }
            for i, chunk in enumerate(chunks)
        ]

    # -- internos ----------------------------------------------------------
    def _split_units(self, text: str) -> list[str]:
        """Parte en unidades <= chunk_size: parrafos -> oraciones -> corte duro."""
        units: list[str] = []
        for paragraph in (p.strip() for p in text.split("\n") if p.strip()):
            if len(paragraph) <= self.chunk_size:
                units.append(paragraph)
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
                sentence = sentence.strip()
                if not sentence:
                    continue
                if len(sentence) <= self.chunk_size:
                    units.append(sentence)
                else:
                    for i in range(0, len(sentence), self.chunk_size):
                        units.append(sentence[i : i + self.chunk_size])
        return units

    def _overlap_tail(self, text: str) -> str:
        """Ultimos `chunk_overlap` caracteres, recortados a frontera de palabra."""
        if self.chunk_overlap <= 0:
            return ""
        tail = text[-self.chunk_overlap :]
        space = tail.find(" ")
        return tail[space + 1 :] if space != -1 else tail