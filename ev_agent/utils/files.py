from __future__ import annotations

from pathlib import Path


def write_code_files(workdir: Path, code_files: dict[str, str]) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    for rel_path, content in sorted(code_files.items(), key=lambda kv: kv[0].lower()):
        p = (workdir / rel_path).resolve()
        if not str(p).startswith(str(workdir.resolve())):
            raise ValueError(f"Refuse to write outside workdir: {rel_path}")
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8", newline="\n")
        tmp.replace(p)


