from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileDigest:
    rel_path: str
    size_bytes: int
    head: str
    tail: str


def build_code_digest(
    workdir: Path,
    rel_paths: list[str],
    *,
    head_lines: int = 120,
    tail_lines: int = 80,
    max_chars_per_file: int = 18_000,
) -> list[FileDigest]:
    out: list[FileDigest] = []
    for rel in sorted(set(rel_paths), key=lambda s: s.lower()):
        p = (workdir / rel).resolve()
        if not str(p).startswith(str(workdir.resolve())):
            continue
        if not p.exists() or not p.is_file():
            continue

        try:
            raw = p.read_bytes()
        except Exception:
            continue

        text = _decode_best_effort(raw)

        lines = text.splitlines()
        head = "\n".join(lines[:head_lines])
        tail = "\n".join(lines[-tail_lines:]) if len(lines) > head_lines else ""

        # Hard cap to keep prompts bounded
        if len(head) > max_chars_per_file:
            head = head[:max_chars_per_file] + "\n...<truncated>..."
        if len(tail) > max_chars_per_file:
            tail = tail[:max_chars_per_file] + "\n...<truncated>..."

        out.append(
            FileDigest(
                rel_path=rel,
                size_bytes=p.stat().st_size,
                head=head,
                tail=tail,
            )
        )
    return out


def _decode_best_effort(raw: bytes) -> str:
    # Try utf-8 first; fallback to gbk for some Windows-generated files.
    try:
        return raw.decode("utf-8")
    except Exception:
        pass
    try:
        return raw.decode("gbk")
    except Exception:
        return raw.decode("utf-8", errors="replace")


def format_code_digest(digests: list[FileDigest]) -> str:
    parts: list[str] = []
    for d in digests:
        parts.append(f"== File: {d.rel_path} ({d.size_bytes} bytes) ==")
        if d.head.strip():
            parts.append("[HEAD]")
            parts.append(d.head)
        if d.tail.strip():
            parts.append("[TAIL]")
            parts.append(d.tail)
        parts.append("")  # spacer
    return "\n".join(parts).strip()


