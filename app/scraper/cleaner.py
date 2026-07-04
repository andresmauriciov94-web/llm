"""Extrae el texto principal del HTML crudo y lo guarda limpio.

Usa trafilatura para descartar menus, headers, footers y publicidad, quedandose
con el contenido util. Cada documento limpio se guarda como
`data/clean/<hash>.json` con {url, title, text}.
"""
from __future__ import annotations

import json
from pathlib import Path

import trafilatura
from bs4 import BeautifulSoup

MIN_TEXT_LENGTH = 100  # descarta paginas casi vacias


class HtmlCleaner:
    """Convierte el HTML crudo del manifiesto en documentos de texto limpio."""

    def __init__(self, raw_dir: str, clean_dir: str) -> None:
        self.raw_dir = Path(raw_dir)
        self.clean_dir = Path(clean_dir)
        self.clean_dir.mkdir(parents=True, exist_ok=True)

    def clean_all(self) -> list[dict]:
        manifest_path = self.raw_dir / "_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                "No existe el manifiesto. Ejecuta primero el crawler."
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        documents: list[dict] = []

        for entry in manifest:
            if entry.get("status") != "ok":
                continue
            raw_file = self.raw_dir / f"{entry['hash']}.html"
            if not raw_file.exists():
                continue

            html = raw_file.read_text(encoding="utf-8")
            text = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
            )
            if not text or len(text.strip()) < MIN_TEXT_LENGTH:
                continue

            document = {
                "url": entry["url"],
                "title": self._extract_title(html),
                "text": text.strip(),
            }
            (self.clean_dir / f"{entry['hash']}.json").write_text(
                json.dumps(document, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            documents.append(document)

        return documents

    @staticmethod
    def _extract_title(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return ""