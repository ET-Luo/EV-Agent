from __future__ import annotations

from datetime import datetime

from rich.console import Console

from ev_agent.llm import ChatMessage, LLMClient
from ev_agent.llm.mock import MockLLM
from ev_agent.schema import CoderOutput, TeamState
from ev_agent.utils.code_digest import build_code_digest, format_code_digest
from ev_agent.utils.exec import run_compileall
from ev_agent.utils.files import write_code_files
from ev_agent.utils.json_extract import extract_first_json_object

from .prompts import ARCH_SYSTEM, CODER_SYSTEM, PM_SYSTEM, QA_SYSTEM, REVIEW_SYSTEM

console = Console()

def _ensure_state(state) -> TeamState:
    if isinstance(state, TeamState):
        return state
    return TeamState.model_validate(state)


def _log(state: TeamState, who: str, msg: str) -> TeamState:
    state.trace.append(
        {
            "ts": datetime.utcnow().isoformat(),
            "node": who,
            "message": msg,
            "iteration": state.iteration,
        }
    )
    return state


def pm_node(state: TeamState, llm: LLMClient) -> TeamState:
    state = _ensure_state(state)
    if state.requirements:
        return state

    if isinstance(llm, MockLLM):
        state.requirements = (
            "目标：实现一个 pygame 贪吃蛇小游戏。\n"
            "用户故事：玩家用方向键控制蛇移动，吃到食物变长，撞墙/撞到自己则结束。\n"
            "范围：单机、单窗口、基础计分。\n"
            "非目标：联网、皮肤商店、复杂动画。\n"
            "验收：能启动窗口；能移动；能吃食物变长；能判定失败并显示结束。\n"
            "风险：pygame 未安装；不同平台窗口事件处理差异。"
        )
        return _log(state, "pm", "Mock PRD ready")

    out = llm.chat(
        [
            ChatMessage("system", PM_SYSTEM),
            ChatMessage("user", state.user_goal),
        ]
    )
    state.requirements = out.strip()
    return _log(state, "pm", "PRD generated")


def architect_node(state: TeamState, llm: LLMClient) -> TeamState:
    state = _ensure_state(state)
    if state.architecture:
        return state

    if isinstance(llm, MockLLM):
        state.architecture = (
            "文件结构：\n"
            "- main.py: 游戏主循环与渲染\n"
            "- snake.py: 蛇的数据结构与移动\n"
            "- food.py: 食物生成\n"
            "- ui.py: 文字渲染/结束画面\n"
            "- requirements.txt: pygame 依赖\n"
        )
        return _log(state, "architect", "Mock architecture ready")

    out = llm.chat(
        [
            ChatMessage("system", ARCH_SYSTEM),
            ChatMessage("user", f"PRD:\n{state.requirements}\n\n请给出架构方案。"),
        ]
    )
    state.architecture = out.strip()
    return _log(state, "architect", "Architecture generated")


def coder_node(state: TeamState, llm: LLMClient, *, workdir) -> TeamState:
    state = _ensure_state(state)
    # Always try to (re)generate code when there's an error, until max iters stops the graph.
    if state.error_log:
        state.iteration += 1

    if isinstance(llm, MockLLM):
        state.code_files = _mock_snake_project()
        write_code_files(workdir, state.code_files)
        state.error_log = ""  # reset before QA
        return _log(state, "coder", f"Mock code written: {len(state.code_files)} files")

    prompt = (
        "基于以下信息生成可运行的代码文件（JSON 格式输出）：\n\n"
        f"PRD:\n{state.requirements}\n\n"
        f"ARCH:\n{state.architecture}\n\n"
        f"上一次报错（如有）:\n{state.error_log}\n\n"
        "输出严格为 JSON：{\"files\":[{\"path\":\"...\",\"content\":\"...\"},...],\"notes\":\"...\"}\n"
        "路径必须是相对路径，根目录为 game/（例如：\"main.py\"）。"
    )
    out = llm.chat([ChatMessage("system", CODER_SYSTEM), ChatMessage("user", prompt)])

    try:
        obj = extract_first_json_object(out)
        parsed = CoderOutput.model_validate(obj)
        code_files: dict[str, str] = {}
        for f in parsed.files:
            path = f.path.strip().replace("\\", "/")
            # Be tolerant: some models output paths like "game/main.py"
            if path.lower().startswith("game/"):
                path = path[5:]
            if path.startswith("/"):
                path = path[1:]
            if not path:
                continue
            code_files[path] = f.content

        if "main.py" not in code_files:
            raise ValueError("缺少必需文件：main.py（注意 path 应该是 workdir 内的相对路径，例如 main.py，而不是 game/main.py）")

        state.code_files = code_files
        write_code_files(workdir, state.code_files)
        state.error_log = ""
        return _log(state, "coder", f"Code written: {len(state.code_files)} files")
    except Exception as e:
        # Do not write anything. Turn this into an error so QA routes back to coder.
        state.error_log = f"CODER_OUTPUT_PARSE_ERROR: {type(e).__name__}: {e}\nRawOutput:\n{out[:2000]}"
        state.qa_report = state.error_log
        return _log(state, "coder", "Coder output invalid; will retry")


def qa_node(state: TeamState, *, workdir, fault_inject: bool = False) -> TeamState:
    state = _ensure_state(state)
    # If coder already produced a parse/protocol error, short-circuit QA as failure.
    if state.error_log.startswith("CODER_OUTPUT_PARSE_ERROR"):
        return _log(state, "qa", "Coder output invalid (parse/protocol).")

    if fault_inject and not state.fault_injected:
        # Deterministic way to verify self-correction loop:
        # make the first QA run fail with a syntax error, then ensure coder fixes it.
        main_py = workdir / "main.py"
        if main_py.exists():
            original = main_py.read_text(encoding="utf-8")
            injected = original + "\n\n# EV_FAULT_INJECT\n\ndef broken(:\n    pass\n"
            main_py.write_text(injected, encoding="utf-8", newline="\n")
            state.fault_injected = True
            _log(state, "qa", "Fault injected into main.py (intentional).")
    res = run_compileall(workdir)
    state.qa_report = f"returncode={res.returncode}\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    if res.returncode != 0:
        state.error_log = state.qa_report
        return _log(state, "qa", "Compileall failed")
    state.error_log = ""
    return _log(state, "qa", "Compileall passed")


def reviewer_node(state: TeamState, llm: LLMClient, *, workdir) -> TeamState:
    state = _ensure_state(state)
    if isinstance(llm, MockLLM):
        state.review_notes = "Mock review：建议后续加入单元测试与配置化参数（格子大小、帧率）。"
        return _log(state, "reviewer", "Mock review ready")

    rel_paths = list(state.code_files.keys())
    digests = build_code_digest(workdir, rel_paths)
    digest_text = format_code_digest(digests)

    out = llm.chat(
        [
            ChatMessage("system", REVIEW_SYSTEM),
            ChatMessage(
                "user",
                "你将收到完整的“代码摘要/关键片段”（可能含截断）。你【禁止】回复“未提供代码/请粘贴代码”。\n\n"
                "请审计以下内容，并给出改进建议：\n\n"
                "```text\n"
                f"{digest_text}\n"
                "```\n\n"
                "输出格式（必须遵守）：\n"
                "1) 高优先级问题（含原因与修复建议）\n"
                "2) 中优先级问题\n"
                "3) 低优先级/可选优化\n"
                "4) 如果信息仍不足：列出“最小补充信息清单”（具体到文件/函数/位置）",
            ),
        ]
    )
    state.review_notes = out.strip()
    return _log(state, "reviewer", "Review notes generated")


def _mock_snake_project() -> dict[str, str]:
    # Minimal, compile-safe snake project. Running requires `pip install pygame`.
    return {
        "requirements.txt": "pygame>=2.5.2\n",
        "main.py": _MOCK_MAIN,
    }


_MOCK_MAIN = r'''import random
import sys

import pygame


CELL = 20
GRID_W, GRID_H = 30, 20
W, H = GRID_W * CELL, GRID_H * CELL
FPS = 12

BLACK = (0, 0, 0)
WHITE = (240, 240, 240)
GREEN = (0, 200, 0)
RED = (220, 40, 40)


def rand_cell(exclude: set[tuple[int, int]]) -> tuple[int, int]:
    while True:
        p = (random.randrange(GRID_W), random.randrange(GRID_H))
        if p not in exclude:
            return p


def draw_cell(screen: pygame.Surface, pos: tuple[int, int], color: tuple[int, int, int]) -> None:
    x, y = pos
    r = pygame.Rect(x * CELL, y * CELL, CELL, CELL)
    pygame.draw.rect(screen, color, r)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Snake (EV-Agent MVP)")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 28)

    snake: list[tuple[int, int]] = [(GRID_W // 2, GRID_H // 2)]
    direction = (1, 0)
    pending_dir = direction
    food = rand_cell(set(snake))
    score = 0
    game_over = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit
                if game_over and event.key == pygame.K_r:
                    return main()
                if event.key == pygame.K_UP:
                    pending_dir = (0, -1)
                elif event.key == pygame.K_DOWN:
                    pending_dir = (0, 1)
                elif event.key == pygame.K_LEFT:
                    pending_dir = (-1, 0)
                elif event.key == pygame.K_RIGHT:
                    pending_dir = (1, 0)

        # prevent 180-degree turn
        if (pending_dir[0] + direction[0], pending_dir[1] + direction[1]) != (0, 0):
            direction = pending_dir

        if not game_over:
            head_x, head_y = snake[0]
            nx, ny = head_x + direction[0], head_y + direction[1]
            new_head = (nx, ny)

            # wall / self collision
            if nx < 0 or nx >= GRID_W or ny < 0 or ny >= GRID_H or new_head in snake:
                game_over = True
            else:
                snake.insert(0, new_head)
                if new_head == food:
                    score += 1
                    food = rand_cell(set(snake))
                else:
                    snake.pop()

        screen.fill(BLACK)
        draw_cell(screen, food, RED)
        for i, seg in enumerate(snake):
            draw_cell(screen, seg, GREEN if i == 0 else WHITE)

        text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(text, (8, 6))

        if game_over:
            msg = font.render("Game Over! Press R to restart.", True, WHITE)
            screen.blit(msg, (8, 34))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
'''


