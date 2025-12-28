from __future__ import annotations

import httpx

from .base import ChatMessage


class OpenAICompatLLM:
    """
    Minimal OpenAI-compatible ChatCompletions client via raw HTTP.
    Works with OpenAI or any OpenAI-compatible gateway if you point base_url accordingly.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_s: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        # OpenAI returns: choices[0].message.content
        choices = data.get("choices") or []
        if not choices:
            return ""
        msg = (choices[0] or {}).get("message") or {}
        return msg.get("content", "") or ""


