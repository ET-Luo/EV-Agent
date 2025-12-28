from __future__ import annotations

import httpx

from .base import ChatMessage


class AnthropicLLM:
    """Minimal Anthropic Messages API client via raw HTTP."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.anthropic.com/v1",
        timeout_s: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        # Anthropic "messages" API: separate system string; user/assistant messages list.
        system = "\n".join([m.content for m in messages if m.role == "system"]).strip()
        convo = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        url = f"{self.base_url}/messages"
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "temperature": temperature,
            "system": system or None,
            "messages": convo,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        # Anthropic returns: content: [{type:"text", text:"..."}]
        blocks = data.get("content") or []
        texts: list[str] = []
        for b in blocks:
            if (b or {}).get("type") == "text":
                texts.append((b or {}).get("text", ""))
        return "\n".join(t for t in texts if t)


