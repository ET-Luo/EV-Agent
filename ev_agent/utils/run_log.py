from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ev_agent.schema import TeamState


@dataclass(frozen=True)
class RunLogPaths:
    run_id: str
    jsonl_path: Path


def make_run_id() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def init_run_log(log_dir: Path, run_id: str) -> RunLogPaths:
    log_dir.mkdir(parents=True, exist_ok=True)
    return RunLogPaths(run_id=run_id, jsonl_path=log_dir / f"run_{run_id}.jsonl")


def append_snapshot(paths: RunLogPaths, state: TeamState, *, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {
        "ts": datetime.utcnow().isoformat(),
        "run_id": paths.run_id,
        "state": state.model_dump(exclude={"code_files"}),
        "code_files": list(state.code_files.keys()),
    }
    if extra:
        payload.update(extra)
    with paths.jsonl_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


