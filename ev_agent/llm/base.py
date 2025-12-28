from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMClient(Protocol):
    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        """Return assistant text output."""
        raise NotImplementedError


