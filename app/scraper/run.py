"""Entrypoint del scraping (crawl -> clean).

Uso:
    python -m app.scraper.run
"""
from __future__ import annotations

from app.config import get_settings
from app.scraper.cleaner import HtmlCleaner
from app.scraper.crawler import WebCrawler


def main() -> None:
    settings = get_settings()

    print(
        f"[scraper] Iniciando crawl de {settings.scrape_base_url} "
        f"(max {settings.scrape_max_pages} paginas)"
    )
    crawler = WebCrawler(
        base_url=settings.scrape_base_url,
        max_pages=settings.scrape_max_pages,
        delay_seconds=settings.scrape_delay_seconds,
        respect_robots=settings.scrape_respect_robots,
        raw_dir=settings.raw_dir,
    )
    manifest = crawler.crawl()
    ok = sum(1 for m in manifest if m["status"] == "ok")
    errors = sum(1 for m in manifest if m["status"] == "error")
    print(f"[scraper] Crudo: {ok} OK, {errors} errores -> {settings.raw_dir}")

    cleaner = HtmlCleaner(raw_dir=settings.raw_dir, clean_dir=settings.clean_dir)
    documents = cleaner.clean_all()
    print(f"[scraper] Limpio: {len(documents)} documentos -> {settings.clean_dir}")

    if not documents:
        print(
            "[scraper] AVISO: no se genero contenido limpio. Revisa que el sitio "
            "sea accesible o ajusta SCRAPE_BASE_URL (puede ser otro banco)."
        )


if __name__ == "__main__":
    main()