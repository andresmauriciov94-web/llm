# Asistente RAG con Web Scraping

Sistema RAG (Retrieval-Augmented Generation) que scrapea el sitio de un banco,
lo indexa en una base vectorial y responde preguntas por una interfaz
conversacional, con memoria por sesion y analitica de conversaciones.

> **Estado:** en construccion (Paso 1 - scaffold). El README completo, con
> instrucciones de arranque, patrones de diseno y stack, se entrega al final.

## Stack (resumen)

| Componente        | Eleccion                              |
|-------------------|---------------------------------------|
| Lenguaje          | Python 3.11                           |
| LLM               | Ollama (local) — swappable a API      |
| Embeddings        | sentence-transformers (multilingue)   |
| Vector store      | Qdrant (self-hosted)                  |
| Memoria/metricas  | SQLite                                |
| API               | FastAPI                               |
| UI                | Streamlit                             |
| Orquestacion      | Docker Compose                        |

## Arranque rapido (preview)

```bash
cp .env.example .env
make setup      # levanta servicios + descarga modelo + scrape + ingest
```

- UI:  http://localhost:8501
- API: http://localhost:8000/docs
