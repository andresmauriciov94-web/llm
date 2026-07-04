"""Modelos de datos de la memoria de conversacion."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    session_id: str
    role: str            # "user" | "assistant"
    content: str
    created_at: str
    latency_ms: Optional[int] = None
    retrieved_ids: list[str] = field(default_factory=list)
    model: Optional[str] = None
    id: Optional[int] = None
