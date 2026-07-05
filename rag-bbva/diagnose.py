"""Diagnostico rapido del scraping.

Uso:
    python diagnose.py                       # usa BBVA por defecto
    python diagnose.py https://otrobanco.com/

Te dice, para esa URL: codigo HTTP, tamano del HTML, cuantos links tiene, algo
de texto visible, y si existen robots.txt y sitemap.xml. Con eso sabemos si el
problema es bloqueo (403), sitio JS (HTML vacio) o falta de links.
"""
import sys
from urllib.parse import urljoin

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

url = sys.argv[1] if len(sys.argv) > 1 else "https://www.bbva.com.co/"
print(f"== Diagnostico de {url} ==\n")

try:
    r = requests.get(url, headers=BROWSER_HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")
    links = soup.find_all("a", href=True)
    text = soup.get_text(" ", strip=True)
    print(f"Status HTTP        : {r.status_code}")
    print(f"Content-Type       : {r.headers.get('Content-Type')}")
    print(f"Tamano HTML        : {len(r.text):,} chars")
    print(f"Links <a href>     : {len(links)}")
    print(f"Texto visible      : {len(text):,} chars")
    print(f"Muestra de texto   : {text[:200]!r}")
except requests.RequestException as exc:
    print(f"ERROR al pedir la pagina: {exc}")

print()
for path in ("/robots.txt", "/sitemap.xml"):
    try:
        rr = requests.get(urljoin(url, path), headers=BROWSER_HEADERS, timeout=15)
        print(f"{path:14}: status {rr.status_code}, {len(rr.text):,} chars")
    except requests.RequestException as exc:
        print(f"{path:14}: ERROR {exc}")

print("\n== Como leer esto ==")
print("- Status 403/401        -> bloqueo anti-bot. Usa headers de navegador (ya en el crawler mejorado) o cambia de banco.")
print("- HTML grande pero texto/links ~0 -> sitio JS (SPA). Usa sitemap.xml o Playwright, o cambia a una seccion mas estatica (blog/ayuda).")
print("- sitemap.xml status 200 -> excelente: sembramos el crawl desde ahi (mucho mas fiable).")
