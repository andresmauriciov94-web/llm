"""Crawler que descarga paginas del sitio y guarda el HTML crudo.

Mejoras clave para sitios con proteccion anti-bot o mucho JS:
- Headers de navegador realistas (reduce los 403).
- Siembra el crawl desde sitemap.xml (mas fiable que seguir links en SPAs).
- Acepta subdominios del mismo sitio (no solo www).
- Reintentos y logging por URL.

Respeta robots.txt y rate-limit. Escribe cada pagina en data/raw/<hash>.html y
un manifiesto data/raw/_manifest.json con la relacion hash -> url y el estado.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}
# UA corto para consultar robots.txt (algunos servidores lo esperan simple)
ROBOTS_AGENT = "rag-bank-assistant"


def url_hash(url: str) -> str:
    """Hash estable y corto de una URL, usado como nombre de archivo."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WebCrawler:
    """Recorre el sitio (sitemap + BFS) y persiste el HTML crudo."""

    def __init__(
        self,
        base_url: str,
        max_pages: int,
        delay_seconds: float,
        respect_robots: bool,
        raw_dir: str,
    ) -> None:
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.max_pages = max_pages
        self.delay = delay_seconds
        self.respect_robots = respect_robots
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        base_netloc = urlparse(self.base_url).netloc
        # dominio raiz: sin el www inicial, para aceptar subdominios del sitio
        self.root_domain = (
            base_netloc[4:] if base_netloc.startswith("www.") else base_netloc
        )

        self.session = requests.Session()
        self.session.headers.update(BROWSER_HEADERS)
        self._robots = self._load_robots()

    # -- robots.txt --------------------------------------------------------
    def _load_robots(self) -> RobotFileParser | None:
        if not self.respect_robots:
            return None
        rp = RobotFileParser()
        try:
            resp = self.session.get(urljoin(self.base_url, "/robots.txt"), timeout=10)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp.allow_all = True
        except requests.RequestException:
            rp.allow_all = True
        return rp

    def _can_fetch(self, url: str) -> bool:
        if self._robots is None:
            return True
        try:
            return self._robots.can_fetch(ROBOTS_AGENT, url)
        except Exception:  # noqa: BLE001
            return True

    # -- utilidades de URL -------------------------------------------------
    def _same_site(self, url: str) -> bool:
        net = urlparse(url).netloc
        return net == self.root_domain or net.endswith("." + self.root_domain)

    @staticmethod
    def _normalize(url: str) -> str:
        clean, _ = urldefrag(url)
        return clean.rstrip("/") or clean

    def _extract_links(self, html: str, base: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            absolute = self._normalize(urljoin(base, anchor["href"]))
            if absolute.startswith("http") and self._same_site(absolute):
                links.append(absolute)
        return links

    # -- sitemap -----------------------------------------------------------
    def _seed_from_sitemap(self) -> list[str]:
        """Intenta obtener URLs desde sitemap.xml (incluye indices anidados)."""
        found: list[str] = []
        try:
            resp = self.session.get(urljoin(self.base_url, "/sitemap.xml"), timeout=15)
            if resp.status_code != 200:
                return found
            locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", resp.text)
            for loc in locs:
                if loc.endswith(".xml"):
                    # indice de sitemaps: bajamos un nivel
                    try:
                        sub = self.session.get(loc, timeout=15)
                        found.extend(re.findall(r"<loc>\s*(.*?)\s*</loc>", sub.text))
                    except requests.RequestException:
                        continue
                else:
                    found.append(loc)
        except requests.RequestException:
            return found
        # normaliza, filtra al sitio y deduplica conservando orden
        seen: set[str] = set()
        result: list[str] = []
        for u in (self._normalize(x) for x in found):
            if u.startswith("http") and self._same_site(u) and u not in seen:
                seen.add(u)
                result.append(u)
        return result

    # -- fetch con un reintento -------------------------------------------
    def _fetch(self, url: str) -> requests.Response | None:
        for attempt in (1, 2):
            try:
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                if attempt == 2:
                    print(f"  [error] {url} -> {exc}")
                    return None
                time.sleep(self.delay)
        return None

    # -- crawl -------------------------------------------------------------
    def crawl(self) -> list[dict]:
        seeds = self._seed_from_sitemap()
        if seeds:
            print(f"[crawler] sitemap.xml aporto {len(seeds)} URLs")
        else:
            print("[crawler] sin sitemap util; se seguira por links (BFS)")

        queue: deque[str] = deque([self._normalize(self.base_url), *seeds])
        visited: set[str] = set()
        manifest: list[dict] = []

        while queue and len(visited) < self.max_pages:
            url = queue.popleft()
            if url in visited or not self._can_fetch(url):
                continue
            visited.add(url)

            resp = self._fetch(url)
            if resp is None:
                manifest.append(
                    {"hash": url_hash(url), "url": url, "status": "error",
                     "fetched_at": _now()}
                )
                continue

            if "text/html" not in resp.headers.get("Content-Type", ""):
                continue

            h = url_hash(url)
            (self.raw_dir / f"{h}.html").write_text(resp.text, encoding="utf-8")
            manifest.append(
                {"hash": h, "url": url, "status": "ok", "fetched_at": _now()}
            )
            print(f"  [ok] ({len(visited)}/{self.max_pages}) {url}")

            for link in self._extract_links(resp.text, url):
                if link not in visited:
                    queue.append(link)

            time.sleep(self.delay)

        (self.raw_dir / "_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return manifest
