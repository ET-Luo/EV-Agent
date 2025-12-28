from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CoderFile(BaseModel):
    path: str
    content: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("path 不能为空")
        # Normalize slashes for validation only (we still write as provided).
        vv = v.replace("\\", "/")
        if vv.startswith("/") or vv.startswith("./") or vv.startswith("../"):
            raise ValueError("path 必须是相对路径，且不能以 ./ 或 ../ 或 / 开头")
        if ":" in vv.split("/")[0]:
            raise ValueError("path 不能包含盘符或协议头")
        if "\x00" in vv:
            raise ValueError("path 非法字符")
        parts = [p for p in vv.split("/") if p]
        if any(p == ".." for p in parts):
            raise ValueError("path 不能包含 ..")
        return v


class CoderOutput(BaseModel):
    """Strict contract for the Coder agent output."""

    files: list[CoderFile] = Field(default_factory=list)
    notes: str = ""

    @field_validator("files")
    @classmethod
    def validate_files(cls, files: list[CoderFile]) -> list[CoderFile]:
        if not files:
            raise ValueError("files 不能为空")
        if len(files) > 50:
            raise ValueError("files 数量过多（>50）")
        seen: set[str] = set()
        for f in files:
            key = f.path.lower()
            if key in seen:
                raise ValueError(f"重复 path: {f.path}")
            seen.add(key)
            if len(f.content) > 300_000:
                raise ValueError(f"文件过大: {f.path}")
        return files


