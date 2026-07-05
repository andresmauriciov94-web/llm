-include .env
export

LLM_MODEL ?= qwen2.5:0.5b

.PHONY: help env build up up-ollama down logs pull-model scrape ingest setup setup-api metrics reset ps

help:
	@echo "=== Comandos principales ==="
	@echo "  make setup       - TODO en uno (Ollama local, gratis, sin API key)"
	@echo "  make setup-api   - TODO en uno usando LLM por API (Groq/OpenAI, requiere key)"
	@echo ""
	@echo "=== Utilidades ==="
	@echo "  make up          - Levanta qdrant, api, ui (sin Ollama)"
	@echo "  make up-ollama   - Levanta todo incluyendo Ollama"
	@echo "  make pull-model  - Descarga el modelo LLM en Ollama"
	@echo "  make scrape      - Scraping (raw + clean)"
	@echo "  make ingest      - Chunk + embed + index en Qdrant"
	@echo "  make metrics     - Reporte de analitica del historico"
	@echo "  make logs        - Sigue los logs"
	@echo "  make down        - Detiene los servicios"
	@echo "  make reset       - Detiene y borra volumenes (datos incluidos)"

# Crea el .env desde el ejemplo si no existe (evita el error 'env file not found')
env:
	@test -f .env || (cp .env.example .env && echo "  -> Creado .env desde .env.example")

build:
	docker compose build

up: env
	docker compose up -d

up-ollama: env
	docker compose --profile ollama up -d

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs -f

pull-model:
	docker compose --profile ollama up -d ollama
	@echo "  -> Esperando a que Ollama este listo..."
	@sleep 5
	docker compose exec ollama ollama pull $(LLM_MODEL)

scrape:
	docker compose run --rm api python -m app.scraper.run

ingest:
	docker compose run --rm api python -m app.ingestion.run

metrics:
	docker compose run --rm api python -m app.analytics.run

# ---- Setup en un comando ----
# Por defecto: Ollama local (gratis, sin API key). Es el modo que espera el evaluador.
setup: env up-ollama pull-model scrape ingest
	@echo ""
	@echo "  Sistema listo (Ollama local)."
	@echo "  UI:  http://localhost:8501"
	@echo "  API: http://localhost:8000/docs"

# Alternativo: LLM por API (Groq/OpenAI). Requiere OPENAI_API_KEY en el .env.
setup-api: env up scrape ingest
	@echo ""
	@echo "  Sistema listo (modo API)."
	@echo "  UI:  http://localhost:8501"
	@echo "  API: http://localhost:8000/docs"

reset:
	docker compose down -v
