from __future__ import annotations

from pathlib import Path


def write_code_files(workdir: Path, code_files: dict[str, str]) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    for rel_path, content in code_files.items():
        p = (workdir / rel_path).resolve()
        if not str(p).startswith(str(workdir.resolve())):
            raise ValueError(f"Refuse to write outside workdir: {rel_path}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


