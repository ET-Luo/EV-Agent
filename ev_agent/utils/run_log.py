from __future__ import annotations

import hashlib
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


FileFingerprints = dict[str, dict[str, Any]]  # rel_path -> {"size": int, "sha256": str}


def make_run_id() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def init_run_log(log_dir: Path, run_id: str) -> RunLogPaths:
    log_dir.mkdir(parents=True, exist_ok=True)
    return RunLogPaths(run_id=run_id, jsonl_path=log_dir / f"run_{run_id}.jsonl")


def fingerprint_workdir(workdir: Path, *, max_bytes: int = 8_000_000) -> FileFingerprints:
    """
    Compute a lightweight fingerprint of files under workdir.
    - No full content stored in logs
    - sha256 computed from file bytes (streaming). If file is huge, hash only first/last chunks.
    """
    out: FileFingerprints = {}
    if not workdir.exists():
        return out
    root = workdir.resolve()
    for p in sorted(root.rglob("*"), key=lambda x: str(x).lower()):
        if p.is_dir():
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        if "__pycache__" in rel:
            continue
        try:
            size = p.stat().st_size
            sha = _sha256_file(p, max_bytes=max_bytes)
            out[rel] = {"size": size, "sha256": sha}
        except Exception:
            continue
    return out


def diff_fingerprints(prev: FileFingerprints, cur: FileFingerprints) -> dict[str, list[str]]:
    prev_keys = set(prev.keys())
    cur_keys = set(cur.keys())
    added = sorted(cur_keys - prev_keys)
    removed = sorted(prev_keys - cur_keys)
    modified: list[str] = []
    for k in sorted(prev_keys & cur_keys):
        if prev[k].get("sha256") != cur[k].get("sha256") or prev[k].get("size") != cur[k].get("size"):
            modified.append(k)
    return {"added": added, "modified": modified, "removed": removed}


def _sha256_file(path: Path, *, max_bytes: int) -> str:
    h = hashlib.sha256()
    size = path.stat().st_size
    with path.open("rb") as f:
        if size <= max_bytes:
            for chunk in iter(lambda: f.read(1024 * 256), b""):
                h.update(chunk)
        else:
            head = f.read(max_bytes // 2)
            h.update(head)
            f.seek(max(size - (max_bytes // 2), 0))
            tail = f.read(max_bytes // 2)
            h.update(tail)
            h.update(str(size).encode("utf-8"))
    return h.hexdigest()


def append_snapshot(
    paths: RunLogPaths,
    state: TeamState,
    *,
    workdir: Path | None = None,
    prev_fingerprints: FileFingerprints | None = None,
    extra: dict[str, Any] | None = None,
) -> FileFingerprints:
    payload: dict[str, Any] = {
        "ts": datetime.utcnow().isoformat(),
        "run_id": paths.run_id,
        "state": state.model_dump(exclude={"code_files"}),
        "code_files": list(state.code_files.keys()),
    }
    cur_fp: FileFingerprints | None = None
    if workdir is not None:
        cur_fp = fingerprint_workdir(workdir)
        payload["workdir_fingerprints"] = cur_fp
        if prev_fingerprints is not None:
            payload["workdir_changes"] = diff_fingerprints(prev_fingerprints, cur_fp)
    if state.trace:
        payload["last_trace"] = state.trace[-1]
    if extra:
        payload.update(extra)
    with paths.jsonl_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return cur_fp or {}


