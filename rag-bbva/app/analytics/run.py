"""Reporte de analitica del historico de conversaciones.

Uso:
    python -m app.analytics.run          # reporte legible
    python -m app.analytics.run --json   # salida JSON (para integraciones)
"""
from __future__ import annotations

import json
import sys

from app.analytics.metrics import ConversationAnalytics
from app.config import get_settings
from app.memory.repository import ConversationRepository


def _print_human(report: dict) -> None:
    t = report["totales"]
    lat = report["latencia_ms"]
    cov = report["cobertura"]
    tok = report["tokens"]

    print("=" * 52)
    print("  ANALITICA DE CONVERSACIONES")
    print("=" * 52)
    print(f"  Sesiones ..................... {t['sesiones']}")
    print(f"  Mensajes totales ............. {t['mensajes']}")
    print(f"    - de usuario ............... {t['mensajes_usuario']}")
    print(f"    - de asistente ............. {t['mensajes_asistente']}")
    print(f"  Promedio mensajes/sesion ..... {t['promedio_mensajes_por_sesion']}")
    print("-" * 52)
    print(f"  Latencia promedio ............ {lat['promedio']} ms")
    print(f"  Latencia p50 / p95 ........... {lat['p50']} / {lat['p95']} ms")
    print(f"  Latencia maxima .............. {lat['maxima']} ms")
    print("-" * 52)
    print(f"  Tokens totales ............... {tok['total']}")
    print(f"    - prompt / completion ...... {tok['prompt']} / {tok['completion']}")
    print(f"  Tokens promedio/respuesta .... {tok['promedio_por_respuesta']}")
    print("-" * 52)
    print(f"  Respuestas sin contexto ...... {cov['respuestas_sin_contexto']} "
          f"({cov['pct_sin_contexto']}%)")
    print("-" * 52)
    print("  Preguntas mas frecuentes:")
    for i, q in enumerate(report["preguntas_frecuentes"], 1):
        print(f"    {i}. ({q['veces']}x) {q['pregunta'][:60]}")
    print("  Fuentes mas usadas:")
    for i, s in enumerate(report["fuentes_mas_usadas"], 1):
        print(f"    {i}. ({s['veces']}x) {s['fuente'][:60]}")
    print("=" * 52)


def main() -> None:
    settings = get_settings()
    repo = ConversationRepository(settings.db_path)
    report = ConversationAnalytics(repo).compute()

    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report)


if __name__ == "__main__":
    main()
