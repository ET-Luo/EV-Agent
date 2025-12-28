from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CmdResult:
    returncode: int
    stdout: str
    stderr: str


def run_compileall(workdir: Path) -> CmdResult:
    # compileall does not import modules; it only compiles source to bytecode.
    cmd = ["python", "-m", "compileall", str(workdir)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return CmdResult(p.returncode, p.stdout, p.stderr)


