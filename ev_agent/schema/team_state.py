from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TeamState(BaseModel):
    """LangGraph shared state for the multi-agent dev team."""

    # Inputs / planning artifacts
    user_goal: str = ""
    requirements: str = ""
    architecture: str = ""

    # Code artifacts (in-memory before writing to disk)
    code_files: dict[str, str] = Field(default_factory=dict)  # path -> content

    # Execution / feedback
    error_log: str = ""
    qa_report: str = ""
    review_notes: str = ""

    # Control / routing
    iteration: int = 0
    next_node: str = "pm"
    fault_injected: bool = False

    # Observability
    trace: list[dict[str, Any]] = Field(default_factory=list)  # simple structured log


