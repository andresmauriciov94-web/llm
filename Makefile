-include .env
export

LLM_MODEL ?= qwen2.5:3b

.PHONY: help build up down logs pull-model scrape ingest setup reset ps

help:
	@echo "Comandos disponibles:"
	@echo "  make build       - Construye las imagenes"
	@echo "  make up          - Levanta todos los servicios"
	@echo "  make pull-model  - Descarga el modelo LLM en Ollama"
	@echo "  make scrape      - Ejecuta el scraping (raw + clean)"
	@echo "  make ingest      - Chunk + embed + index en Qdrant"
	@echo "  make setup       - up + pull-model + scrape + ingest (todo en uno)"
	@echo "  make logs        - Sigue los logs"
	@echo "  make down        - Detiene los servicios"
	@echo "  make reset       - Detiene y borra volumenes (datos incluidos)"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs -f

pull-model:
	docker compose exec ollama ollama pull $(LLM_MODEL)

scrape:
	docker compose run --rm api python -m app.scraper.run

ingest:
	docker compose run --rm api python -m app.ingestion.run

setup: up pull-model scrape ingest
	@echo ""
	@echo "  Sistema listo."
	@echo "  UI:  http://localhost:8501"
	@echo "  API: http://localhost:8000/docs"

reset:
	docker compose down -v
