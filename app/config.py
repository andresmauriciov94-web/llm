"""Configuracion centralizada del sistema.

Unica fuente de verdad para todos los parametros. Se lee desde variables de
entorno / archivo .env. `get_settings()` esta cacheada, actuando como un
Singleton ligero: la config se instancia una sola vez por proceso.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- LLM -------------------------------------------------------------
    llm_provider: str = "ollama"          # ollama | openai
    llm_model: str = "qwen2.5:3b"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 512
    ollama_base_url: str = "http://ollama:11434"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None  # permite proveedores compatibles

    # ---- Embeddings ------------------------------------------------------
    # Modelo multilingue: el contenido del banco esta en espanol.
    embedding_model: str = "intfloat/multilingual-e5-small"

    # ---- Vector store (Qdrant) ------------------------------------------
    qdrant_url: str = "http://qdrant:6333"
    collection_name: str = "bank_web"

    # ---- Chunking --------------------------------------------------------
    chunk_size: int = 800
    chunk_overlap: int = 120

    # ---- Recuperacion ----------------------------------------------------
    top_k: int = 5
    rerank_enabled: bool = True
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_top_n: int = 3

    # ---- Conversacion ----------------------------------------------------
    conversation_window: int = 6          # N mensajes previos (configurable)

    # ---- Scraper ---------------------------------------------------------
    scrape_base_url: str = "https://www.bbva.com.co/"
    scrape_max_pages: int = 40
    scrape_delay_seconds: float = 1.0
    scrape_respect_robots: bool = True

    # ---- Almacenamiento --------------------------------------------------
    db_path: str = "data/app.db"
    raw_dir: str = "data/raw"
    clean_dir: str = "data/clean"

    # ---- API / UI --------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_url: str = "http://api:8000"      # usado por la UI para llamar a la API


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia unica de configuracion (cacheada)."""
    return Settings()
