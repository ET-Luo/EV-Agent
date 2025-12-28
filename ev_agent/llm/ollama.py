from __future__ import annotations

import httpx

from .base import ChatMessage


class OllamaLLM:
    def __init__(self, *, base_url: str, model: str, timeout_s: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {"temperature": temperature},
        }
        url = f"{self.base_url}/api/chat"
        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        # Ollama returns: {"message": {"role": "...", "content": "..."}, ...}
        return (data.get("message") or {}).get("content", "")


