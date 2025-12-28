from __future__ import annotations

import argparse
import sys
import traceback

from rich.console import Console

from ev_agent.chains import build_team_graph
from ev_agent.config import load_settings
from ev_agent.llm import build_llms
from ev_agent.schema import TeamState
from ev_agent.utils.run_log import append_snapshot, init_run_log, make_run_id


def main() -> int:
    # Best-effort fix for Windows terminals defaulting to GBK.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(prog="ev-agent")
    parser.add_argument("goal", type=str, help="一句话需求，例如：写一个 pygame 贪吃蛇")
    parser.add_argument(
        "--fault-inject",
        action="store_true",
        help="（调试用）在首次 QA 时注入一个语法错误，用于验证自纠错循环是否生效",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="不写运行日志（默认会写入 logs/run_*.jsonl，供 Streamlit 实时展示）",
    )
    args = parser.parse_args()

    console = Console()
    settings = load_settings()
    llm_general, llm_coder = build_llms(settings)

    settings.workdir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    graph = build_team_graph(
        llm_general=llm_general,
        llm_coder=llm_coder,
        workdir=settings.workdir,
        max_iters=settings.max_iters,
        fault_inject=bool(args.fault_inject or settings.fault_inject),
    )

    do_log = not bool(args.no_log)
    run_id = make_run_id()
    log_paths = init_run_log(settings.log_dir, run_id)

    state = TeamState(user_goal=args.goal)
    if do_log:
        append_snapshot(log_paths, state, extra={"event": "start", "workdir": str(settings.workdir)})

    # Prefer streaming so UI can update in real time.
    final_state: TeamState
    try:
        last = None
        for step in graph.stream(state, stream_mode="values"):
            last = step
            s = TeamState.model_validate(step)
            if do_log:
                append_snapshot(log_paths, s, extra={"event": "step"})
        if last is None:
            last = graph.invoke(state)
        final_state = TeamState.model_validate(last)
    except Exception:
        tb = traceback.format_exc()
        if do_log:
            append_snapshot(log_paths, state, extra={"event": "exception", "traceback": tb})
        raise

    if do_log:
        append_snapshot(log_paths, final_state, extra={"event": "final"})

    console.rule("EV-Agent Result")
    console.print(f"[bold]workdir[/bold]: {settings.workdir}")
    if do_log:
        console.print(f"[bold]run_log[/bold]: {log_paths.jsonl_path}")
    console.print(f"[bold]files[/bold]: {list(final_state.code_files.keys())}")
    console.print(f"[bold]qa_passed[/bold]: {final_state.error_log == ''}")
    console.print(f"[bold]iterations[/bold]: {final_state.iteration}")
    if final_state.error_log:
        console.print("[bold red]error_log[/bold red]")
        console.print(final_state.error_log)
    if final_state.review_notes:
        console.print("[bold]review_notes[/bold]")
        console.print(final_state.review_notes)

    # Show a compact trace for debugging loops.
    if final_state.trace:
        console.print("[bold]trace[/bold]")
        for e in final_state.trace[-12:]:
            console.print(f"- {e.get('node')} :: {e.get('message')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


