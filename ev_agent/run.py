from __future__ import annotations

import argparse
import sys

from rich.console import Console

from ev_agent.chains import build_team_graph
from ev_agent.config import load_settings
from ev_agent.llm import build_llm
from ev_agent.schema import TeamState


def main() -> int:
    # Best-effort fix for Windows terminals defaulting to GBK.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(prog="ev-agent")
    parser.add_argument("goal", type=str, help="一句话需求，例如：写一个 pygame 贪吃蛇")
    args = parser.parse_args()

    console = Console()
    settings = load_settings()
    llm = build_llm(settings)

    settings.workdir.mkdir(parents=True, exist_ok=True)

    graph = build_team_graph(llm=llm, workdir=settings.workdir, max_iters=settings.max_iters)

    state = TeamState(user_goal=args.goal)
    result = graph.invoke(state)
    final_state = TeamState.model_validate(result)

    console.rule("EV-Agent Result")
    console.print(f"[bold]workdir[/bold]: {settings.workdir}")
    console.print(f"[bold]files[/bold]: {list(final_state.code_files.keys())}")
    console.print(f"[bold]qa_passed[/bold]: {final_state.error_log == ''}")
    if final_state.error_log:
        console.print("[bold red]error_log[/bold red]")
        console.print(final_state.error_log)
    if final_state.review_notes:
        console.print("[bold]review_notes[/bold]")
        console.print(final_state.review_notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


