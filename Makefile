-include .env
export

LLM_MODEL ?= qwen2.5:0.5b

.PHONY: help build up up-ollama down logs pull-model scrape ingest setup setup-ollama metrics reset ps

help:
	@echo "Comandos disponibles:"
	@echo "  --- Modo API (Groq/OpenAI) — recomendado, sin Ollama ---"
	@echo "  make setup        - up + scrape + ingest (LLM por API)"
	@echo "  make up           - Levanta qdrant, api, ui (sin Ollama)"
	@echo ""
	@echo "  --- Modo Ollama local ---"
	@echo "  make setup-ollama - up-ollama + pull-model + scrape + ingest"
	@echo "  make up-ollama    - Levanta todo incluyendo Ollama (--profile ollama)"
	@echo "  make pull-model   - Descarga el modelo LLM en Ollama"
	@echo ""
	@echo "  --- Utilidades ---"
	@echo "  make scrape       - Ejecuta el scraping (raw + clean)"
	@echo "  make ingest       - Chunk + embed + index en Qdrant"
	@echo "  make metrics      - Reporte de analitica del historico"
	@echo "  make logs         - Sigue los logs"
	@echo "  make down         - Detiene los servicios"
	@echo "  make reset        - Detiene y borra volumenes (datos incluidos)"

build:
	docker compose build

# --- Arranque ---
up:
	docker compose up -d

up-ollama:
	docker compose --profile ollama up -d

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs -f

# --- Ollama ---
pull-model:
	docker compose --profile ollama up -d ollama
	docker compose exec ollama ollama pull $(LLM_MODEL)

# --- Datos ---
scrape:
	docker compose run --rm api python -m app.scraper.run

ingest:
	docker compose run --rm api python -m app.ingestion.run

metrics:
	docker compose run --rm api python -m app.analytics.run

# --- Setup en un comando ---
# Modo API (Groq/OpenAI): NO necesita Ollama ni pull-model.
setup: up scrape ingest
	@echo ""
	@echo "  Sistema listo (modo API por Groq/OpenAI)."
	@echo "  UI:  http://localhost:8501"
	@echo "  API: http://localhost:8000/docs"

# Modo Ollama local: levanta Ollama, descarga el modelo, scrape e ingest.
setup-ollama: up-ollama pull-model scrape ingest
	@echo ""
	@echo "  Sistema listo (modo Ollama local)."
	@echo "  UI:  http://localhost:8501"
	@echo "  API: http://localhost:8000/docs"

reset:
	docker compose down -v
