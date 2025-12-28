from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    llm_backend: str

    ollama_base_url: str
    ollama_model: str

    anthropic_api_key: str | None
    anthropic_model: str

    openai_api_key: str | None
    openai_model: str

    max_iters: int
    workdir: Path


def load_settings() -> Settings:
    # Allow users to keep secrets in a local `.env` (not committed).
    load_dotenv(override=False)

    def getenv(key: str, default: str | None = None) -> str | None:
        v = os.getenv(key)
        if v is None or v == "":
            return default
        return v

    llm_backend = (getenv("EV_LLM_BACKEND", "mock") or "mock").strip().lower()

    ollama_base_url = getenv("EV_OLLAMA_BASE_URL", "http://localhost:11434") or ""
    ollama_model = getenv("EV_OLLAMA_MODEL", "deepseek-r1:latest") or ""

    anthropic_api_key = getenv("ANTHROPIC_API_KEY", None)
    anthropic_model = getenv("EV_ANTHROPIC_MODEL", "claude-3-5-sonnet-latest") or ""

    openai_api_key = getenv("OPENAI_API_KEY", None)
    openai_model = getenv("EV_OPENAI_MODEL", "gpt-4o-mini") or ""

    max_iters = int(getenv("EV_MAX_ITERS", "3") or "3")
    workdir = Path(getenv("EV_WORKDIR", "game") or "game").resolve()

    return Settings(
        llm_backend=llm_backend,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        anthropic_api_key=anthropic_api_key,
        anthropic_model=anthropic_model,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        max_iters=max_iters,
        workdir=workdir,
    )


