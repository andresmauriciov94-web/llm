"""API FastAPI.

En el Paso 1 expone solo /health para validar que el contenedor arranca y la
config se carga bien. En pasos siguientes se agregan /chat, /sessions y /metrics.
"""
from fastapi import FastAPI

from app.config import get_settings

settings = get_settings()

app = FastAPI(title="RAG Bank Assistant", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
        "conversation_window": settings.conversation_window,
    }
