from __future__ import annotations

from ev_agent.config import Settings

from .anthropic import AnthropicLLM
from .mock import MockLLM
from .ollama import OllamaLLM
from .openai_compat import OpenAICompatLLM


def build_llm(settings: Settings):
    backend = settings.llm_backend
    if backend == "mock":
        return MockLLM()
    if backend == "ollama":
        return OllamaLLM(base_url=settings.ollama_base_url, model=settings.ollama_model)
    if backend == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 未配置，但 EV_LLM_BACKEND=anthropic")
        return AnthropicLLM(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
    if backend == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY 未配置，但 EV_LLM_BACKEND=openai")
        return OpenAICompatLLM(api_key=settings.openai_api_key, model=settings.openai_model)
    raise ValueError(f"未知 EV_LLM_BACKEND={backend!r}，可选：mock|ollama|anthropic|openai")


def build_llms(settings: Settings):
    """
    Build (general_llm, coder_llm).

    - For Ollama: can use different models per role via EV_OLLAMA_MODEL_GENERAL / EV_OLLAMA_MODEL_CODER
    - For other backends: returns the same client twice.
    """
    backend = settings.llm_backend
    if backend == "ollama":
        general = OllamaLLM(base_url=settings.ollama_base_url, model=settings.ollama_model_general)
        coder = OllamaLLM(base_url=settings.ollama_base_url, model=settings.ollama_model_coder)
        return general, coder

    llm = build_llm(settings)
    return llm, llm


