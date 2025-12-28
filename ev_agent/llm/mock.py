from __future__ import annotations

from .base import ChatMessage


class MockLLM:
    """Deterministic mock backend: useful to verify control-flow without external LLM."""

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        # Very small, predictable behavior: echo last user request with a stub.
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return (
            "【MOCK 模式】我收到了需求：\n"
            f"{last_user}\n\n"
            "接下来（真实 LLM 模式）我会输出结构化 PRD / 架构 / 代码补丁。"
        )


