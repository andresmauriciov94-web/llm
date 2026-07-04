# Arquitectura del sistema RAG

Documento de diseno de alto nivel. Consolida decisiones, componentes, flujos,
patrones y la trazabilidad de cada requisito de la prueba.

---

## 1. Contexto y objetivo

Asistente conversacional que permite consultar informacion publicada en el
sitio institucional de un banco sin busquedas manuales. Se resuelve con un
pipeline **RAG** (Retrieval-Augmented Generation): se scrapea el sitio, se
indexa en una base vectorial y un LLM responde **grounded** en ese contenido,
con memoria por sesion y analitica de las conversaciones.

Principio rector: **arquitectura limpia y desacoplada, decisiones justificadas,
arranque con un solo comando y cero friccion para quien evalua.** Todo
open-source / self-hosted por defecto; sin costo obligatorio.

---

## 2. Vista de alto nivel

```
                        ┌───────────────────────────┐
   navegador  ────────▶ │   Streamlit UI   :8501     │
                        └────────────┬──────────────┘
                                     │ REST (httpx)
                        ┌────────────▼──────────────┐
                        │     FastAPI API  :8000     │
                        │  /chat /sessions /metrics  │
                        │  /health                   │
                        └───┬───────┬────────┬───────┘
                            │       │        │
             embeddings ┌───▼──┐ ┌──▼───┐ ┌──▼─────────┐
             (S-Trans)  │Embed │ │ LLM  │ │  Memoria   │
                        └───┬──┘ │Ollama│ │  SQLite    │
                            │    └──────┘ │(historial +│
                        ┌───▼──────┐      │ metricas)  │
                        │  Qdrant  │      └────────────┘
                        │  :6333   │
                        │(vectores)│
                        └──────────┘

   OFFLINE (comando aparte, no bloquea el arranque):
   Scraper ──▶ data/raw (HTML crudo) + data/clean (texto limpio)
           ──▶ Ingesta (chunk ▸ embed ▸ upsert) ──▶ Qdrant
```

Cuatro servicios en Docker Compose: `qdrant`, `ollama`, `api`, `ui`.
SQLite es un archivo en volumen (no un servicio). El scraping/ingesta es un
**comando separado**, ejecutado dentro del contenedor `api` para reutilizar la
misma red interna.

---

## 3. Decisiones de stack (con justificacion)

| Componente        | Eleccion                                   | Por que |
|-------------------|--------------------------------------------|---------|
| Lenguaje          | Python 3.11                                | Requisito obligatorio. |
| Scraping          | `requests` + `BeautifulSoup` + `trafilatura` | Estatico y suficiente; trafilatura extrae texto principal limpio quitando menus/footers. Playwright solo si el sitio exige JS. |
| Embeddings        | `sentence-transformers`, modelo **multilingue** (`multilingual-e5-small`) | Gratis, self-hosted. Multilingue es **critico**: el contenido esta en espanol. |
| Vector store      | **Qdrant** self-hosted                     | Grado produccion, gratis, corre como servicio propio en compose (demuestra arquitectura multi-servicio real vs. una libreria embebida). |
| LLM               | **Ollama** local, swappable a API vía env  | Cumple "herramientas gratis preferidas" y permite al evaluador correrlo sin API keys. La abstraccion permite cambiar a OpenAI con una variable. |
| Reranker (bonus)  | CrossEncoder `bge-reranker-v2-m3`          | Multilingue, mejora la precision del top-k antes del LLM. Activable/desactivable por env. |
| Memoria + metricas| **SQLite**                                 | Cero friccion, persistente en volumen y **consultable con SQL** para la analitica. |
| API               | **FastAPI**                                | Tipado, docs OpenAPI automaticas, async. |
| UI                | **Streamlit**                              | Chat funcional y limpio con minimo codigo (la prueba pide funcional, no bonito). |
| Config            | `pydantic-settings` + `.env`               | Config externalizada (bonus), validada y centralizada. |
| Orquestacion      | Docker Compose                             | Requisito: todo levanta con un comando. |

---

## 4. Flujos principales

**A. Scraping (offline).** Recorre un subconjunto acotado del sitio respetando
`robots.txt` con rate-limit. Guarda `data/raw/<hash>.html` (crudo) y
`data/clean/<hash>.json` (URL + titulo + texto limpio). Cumple el requisito de
almacenar crudos y limpios.

**B. Ingesta (offline).** Carga los limpios, hace *chunking* con solapamiento,
genera embeddings y hace *upsert* en Qdrant con metadatos (url, titulo, chunk).

**C. Chat (online).** `{session_id, message}` ▸ recupera ultimos **N** turnos de
SQLite ▸ embebe la query ▸ top-k en Qdrant ▸ (rerank) ▸ arma prompt
(system + contexto + historial + pregunta) ▸ LLM genera ▸ persiste el turno con
metadatos ▸ responde con fuentes.

**D. Analitica (offline/online).** Recorre el historico en SQLite y calcula
metricas de impacto (ver seccion 7).

---

## 5. Responsabilidad por componente

- **config** — settings unicas (`pydantic-settings`), cacheadas.
- **scraper/** — `crawler` (descarga + guarda crudo), `cleaner` (texto limpio), `run` (entrypoint).
- **ingestion/** — `chunker` (chunk + overlap), `indexer` (embed + upsert), `run`.
- **embeddings/** — interfaz + impl sentence-transformers.
- **llm/** — interfaz + `OllamaProvider` / `OpenAIProvider` + `factory`.
- **vectorstore/** — adapter sobre el cliente Qdrant (crear coleccion, upsert, search).
- **rag/** — `pipeline` (orquesta), `retriever`, `reranker`, `prompt_builder`, `generator`.
- **memory/** — `repository` (persistencia SQLite) + modelos.
- **analytics/** — calculo de metricas.
- **api/** — endpoints FastAPI. **ui/** — cliente Streamlit.

---

## 6. Patrones de diseno (donde y por que)

| Patron | Ubicacion | Justificacion |
|--------|-----------|---------------|
| **Strategy** | `llm/base.py`, `embeddings/base.py` | Proveedores intercambiables tras una interfaz comun; permite cambiar LLM/embedder sin tocar la logica. |
| **Factory** | `llm/factory.py` | Crea el proveedor correcto segun la config; unico punto de creacion, dependencias inyectadas. |
| **Repository** | `memory/repository.py` | Aisla la persistencia del historial; migrar a Postgres/Redis no afecta la logica de negocio. |
| **Chain of Responsibility** (4o, suma) | `rag/pipeline.py` | Etapas del RAG (retrieve ▸ rerank ▸ context ▸ generate) encadenadas, legibles y extensibles. |

Con 3 se cumple el requisito; el 4o suma puntos.

---

## 7. Modelo de datos

**Qdrant** — coleccion `bank_web`, vectores del embedder, payload:
`{url, title, chunk_index, text}`.

**SQLite** — tabla `messages`:

| campo          | tipo    | uso |
|----------------|---------|-----|
| id             | INTEGER | PK |
| session_id     | TEXT    | agrupa la conversacion (memoria por ID) |
| role           | TEXT    | user / assistant |
| content        | TEXT    | texto del turno |
| created_at     | TEXT    | timestamp |
| latency_ms     | INTEGER | metrica de rendimiento |
| retrieved_ids  | TEXT    | ids de chunks usados (trazabilidad / analitica) |
| model          | TEXT    | modelo que respondio |

El historial se filtra por `session_id` y se limita a los ultimos **N**
(`CONVERSATION_WINDOW`). Como todo queda en SQLite, la analitica calcula:
numero de sesiones y mensajes, promedio de mensajes por sesion, latencia
p50/p95, preguntas mas frecuentes, chunks mas recuperados y tasa de respuestas
sin contexto recuperado. Se expone por CLI y como pestana en la UI.

---

## 8. Ciclo de vida de una consulta (`POST /chat`)

1. Llega `{session_id, message}`.
2. `repository.get_last_n(session_id, N)` trae el historial reciente.
3. Se embebe la pregunta y se recuperan top-k chunks de Qdrant.
4. (bonus) el reranker reordena por relevancia real y recorta a `RERANK_TOP_N`.
5. `prompt_builder` compone system + contexto + historial + pregunta.
6. El LLM (via Strategy/Factory) genera la respuesta.
7. `repository` persiste el turno del usuario y del asistente con metadatos.
8. Se devuelve `{answer, sources, session_id}`.

---

## 9. Configuracion (externalizada, bonus)

Todo por `.env`: `LLM_PROVIDER/MODEL`, `EMBEDDING_MODEL`, `QDRANT_URL`,
`CHUNK_SIZE/OVERLAP`, `TOP_K`, `RERANK_ENABLED`, `CONVERSATION_WINDOW` (N),
`SCRAPE_BASE_URL/MAX_PAGES`, etc. Un solo lugar, validado por pydantic.

---

## 10. Alcance, supuestos y limites

- Se scrapea un **subconjunto acotado** de paginas (`SCRAPE_MAX_PAGES`), no el
  sitio completo. Se respeta `robots.txt` con rate-limit; si el sitio bloquea,
  se usa otro banco (la prueba lo permite explicitamente).
- Embeddings y LLM corren en CPU: la latencia depende del hardware. Modelo LLM
  pequeno por defecto para que sea ejecutable en cualquier maquina.
- SQLite es suficiente para un solo nodo; para alta concurrencia se migraria a
  Postgres (aislado tras el Repository, sin cambios en la logica).

---

## 11. Trazabilidad de requisitos

| Requisito | Donde se resuelve | Estado |
|-----------|-------------------|--------|
| Scraping del sitio | `scraper/` | plan |
| Guardar crudos y limpios | `data/raw` + `data/clean` | plan |
| Vectorizar e indexar | `embeddings/` + `ingestion/indexer` + Qdrant | plan |
| Interfaz conversacional | `api/` + `ui/` | plan |
| Historial por ID, N configurable | `memory/repository` + `CONVERSATION_WINDOW` | plan |
| Python | todo | ✔ |
| Dockerizacion (1 comando) | `Dockerfile` + `docker-compose.yml` + `make setup` | ✔ scaffold |
| Repo con historial de commits | git, progresion por pasos | en curso |
| >=3 patrones de diseno | Strategy, Factory, Repository (+CoR) | plan |
| Persistir historial | SQLite | plan |
| Interfaz funcional | Streamlit + FastAPI | plan |
| Herramientas sin costo | Ollama, S-Transformers, Qdrant | ✔ |
| Analisis de datos | `analytics/metrics` | plan |
| README completo | `README.md` | final |
| **Bonus:** reranker | `rag/reranker` | plan |
| **Bonus:** manejo de errores | transversal | plan |
| **Bonus:** config externalizada | `config.py` + `.env` | ✔ |

---

## 12. Plan de trabajo (commits)

1. scaffold + docker + config ✔
2. scraper (raw + clean)
3. chunking + embeddings
4. vector store (Qdrant)
5. pipeline de ingesta
6. abstraccion LLM (Strategy + Factory)
7. pipeline RAG (retrieve + generate)
8. memoria (Repository + SQLite, N configurable)
9. API + UI (chat)
10. reranker (bonus)
11. analitica
12. manejo de errores + pulido
13. README completo