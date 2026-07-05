"""Pipeline RAG como Chain of Responsibility.

Cada etapa recibe un contexto compartido (RagContext), hace su parte y lo pasa a
la siguiente. Esto hace el flujo legible y extensible: agregar/quitar un paso
(por ejemplo el reranker) es insertar o remover un eslabon, sin tocar los demas.

Etapas: Retrieve -> (Rerank opcional) -> BuildPrompt -> Generate.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.llm.base import LLMProvider
from app.rag.prompt_builder import SYSTEM_PROMPT, PromptBuilder
from app.rag.reranker import Reranker
from app.rag.retriever import Retriever


@dataclass
class RagContext:
    """Estado que viaja por la cadena."""
    question: str
    history: list[dict] = field(default_factory=list)
    chunks: list[dict] = field(default_factory=list)
    user_prompt: str = ""
    answer: str = ""
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class Stage(ABC):
    """Eslabon de la cadena."""
    @abstractmethod
    def handle(self, ctx: RagContext) -> RagContext:
        ...


class RetrieveStage(Stage):
    def __init__(self, retriever: Retriever) -> None:
        self.retriever = retriever

    def handle(self, ctx: RagContext) -> RagContext:
        ctx.chunks = self.retriever.retrieve(ctx.question)
        return ctx


class RerankStage(Stage):
    """Eslabon opcional: reordena los chunks por relevancia antes del prompt."""

    def __init__(self, reranker: Reranker, top_n: int) -> None:
        self.reranker = reranker
        self.top_n = top_n

    def handle(self, ctx: RagContext) -> RagContext:
        ctx.chunks = self.reranker.rerank(ctx.question, ctx.chunks, self.top_n)
        return ctx


class BuildPromptStage(Stage):
    def __init__(self, builder: PromptBuilder) -> None:
        self.builder = builder

    def handle(self, ctx: RagContext) -> RagContext:
        ctx.user_prompt = self.builder.build_user_prompt(
            question=ctx.question, chunks=ctx.chunks, history=ctx.history
        )
        return ctx


class GenerateStage(Stage):
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    def handle(self, ctx: RagContext) -> RagContext:
        result = self.llm.generate(SYSTEM_PROMPT, ctx.user_prompt)
        ctx.answer = result.text
        ctx.prompt_tokens = result.prompt_tokens
        ctx.completion_tokens = result.completion_tokens
        return ctx


class RagPipeline:
    def __init__(self, stages: list[Stage]) -> None:
        self.stages = stages

    def run(self, question: str, history: list[dict] | None = None) -> RagContext:
        ctx = RagContext(question=question, history=history or [])
        start = time.perf_counter()
        for stage in self.stages:
            ctx = stage.handle(ctx)
        ctx.latency_ms = int((time.perf_counter() - start) * 1000)
        return ctx