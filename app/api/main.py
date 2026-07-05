"""API FastAPI: chat conversacional RAG.

Ensambla las dependencias una sola vez al arrancar (embedder, vector store, LLM,
repositorio y pipeline) y expone los endpoints. El armado esta en build_services
para poder inyectar dobles en tests sin cargar el modelo real.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.embeddings.sentence_transformer import SentenceTransformerEmbedder
from app.llm.factory import create_llm
from app.memory.repository import ConversationRepository
from app.rag.pipeline import (
    BuildPromptStage,
    GenerateStage,
    RagPipeline,
    RerankStage,
    RetrieveStage,
)
from app.rag.prompt_builder import PromptBuilder
from app.rag.reranker import CrossEncoderReranker
from app.rag.retriever import Retriever
from app.vectorstore.qdrant_store import QdrantStore


@dataclass
class Services:
    settings: Settings
    repo: ConversationRepository
    pipeline: RagPipeline
    llm_model: str


def build_services(settings: Settings) -> Services:
    embedder = SentenceTransformerEmbedder(settings.embedding_model)
    store = QdrantStore(
        url=settings.qdrant_url,
        collection_name=settings.collection_name,
        vector_size=embedder.dimension,
    )
    llm = create_llm(settings)
    repo = ConversationRepository(settings.db_path)
    retriever = Retriever(embedder, store, settings.top_k)

    # Cadena base; el reranker se inserta como eslabon si esta habilitado.
    stages = [RetrieveStage(retriever)]
    if settings.rerank_enabled:
        reranker = CrossEncoderReranker(settings.reranker_model)
        stages.append(RerankStage(reranker, settings.rerank_top_n))
    stages += [BuildPromptStage(PromptBuilder()), GenerateStage(llm)]

    pipeline = RagPipeline(stages)
    return Services(settings, repo, pipeline, settings.llm_model)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Si un test ya inyecto services, no reconstruimos (evita cargar el modelo).
    if not getattr(app.state, "services", None):
        app.state.services = build_services(get_settings())
    yield


app = FastAPI(title="RAG Bank Assistant", version="1.0.0", lifespan=lifespan)


# -- esquemas ----------------------------------------------------------------
class ChatRequest(BaseModel):
    session_id: str
    message: str


class Source(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[Source]
    latency_ms: int


def _services(request: Request) -> Services:
    return request.app.state.services


# -- endpoints ---------------------------------------------------------------
@app.get("/health")
def health():
    s = get_settings()
    return {
        "status": "ok",
        "llm_provider": s.llm_provider,
        "llm_model": s.llm_model,
        "conversation_window": s.conversation_window,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacio.")

    svc = _services(request)
    n = svc.settings.conversation_window

    # Historial PREVIO (sin el mensaje actual) para dar contexto al pipeline.
    history = svc.repo.get_last_messages(req.session_id, n)

    try:
        ctx = svc.pipeline.run(req.message, history=history)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    retrieved_ids = [
        f"{c.get('url', '')}#{c.get('chunk_index', 0)}" for c in ctx.chunks
    ]
    # Persistimos ambos turnos.
    svc.repo.add_message(req.session_id, "user", req.message)
    svc.repo.add_message(
        req.session_id,
        "assistant",
        ctx.answer,
        latency_ms=ctx.latency_ms,
        retrieved_ids=retrieved_ids,
        model=svc.llm_model,
    )

    # Fuentes unicas para mostrar en la UI.
    seen: set[tuple[str, str]] = set()
    sources: list[Source] = []
    for c in ctx.chunks:
        key = (c.get("title", ""), c.get("url", ""))
        if key not in seen and key[1]:
            seen.add(key)
            sources.append(Source(title=key[0], url=key[1]))

    return ChatResponse(
        session_id=req.session_id,
        answer=ctx.answer,
        sources=sources,
        latency_ms=ctx.latency_ms,
    )


@app.get("/sessions")
def list_sessions(request: Request):
    return {"sessions": _services(request).repo.list_sessions()}


@app.get("/sessions/{session_id}")
def session_detail(session_id: str, request: Request):
    messages = _services(request).repo.get_session(session_id)
    return {"session_id": session_id, "messages": messages}


@app.get("/metrics")
def metrics(request: Request):
    """Metricas de impacto calculadas sobre el historico de conversaciones."""
    from app.analytics.metrics import ConversationAnalytics

    return ConversationAnalytics(_services(request).repo).compute()