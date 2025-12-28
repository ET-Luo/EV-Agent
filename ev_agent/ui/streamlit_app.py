from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st


def read_jsonl(path: Path, limit: int = 5000) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) > limit:
        lines = lines[-limit:]
    out: list[dict] = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def list_files_tree(root: Path) -> list[str]:
    if not root.exists():
        return []
    files: list[str] = []
    for p in sorted(root.rglob("*"), key=lambda x: str(x).lower()):
        if p.is_dir():
            continue
        rel = str(p.relative_to(root))
        if "__pycache__" in rel:
            continue
        files.append(rel)
    return files


st.set_page_config(page_title="EV-Agent Monitor", layout="wide")
st.title("EV-Agent 可视化面板")

log_dir = Path(st.sidebar.text_input("EV_LOG_DIR", value="logs")).resolve()
log_dir.mkdir(parents=True, exist_ok=True)
log_files = sorted(log_dir.glob("run_*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)

selected = st.sidebar.selectbox(
    "选择运行日志",
    options=[str(p) for p in log_files],
    index=0 if log_files else None,
    placeholder="没有找到 run_*.jsonl（请先运行 python -m ev_agent.run ...）",
)

auto = st.sidebar.checkbox("自动刷新", value=True)
interval = st.sidebar.slider("刷新间隔(秒)", min_value=1, max_value=10, value=2)

if not selected:
    st.info("暂无日志。先运行一次 `python -m ev_agent.run ...`，它会在 `logs/` 下生成 `run_*.jsonl`。")
    st.stop()

log_path = Path(selected)
events = read_jsonl(log_path)
if not events:
    st.warning("日志文件为空或不可解析。")
    st.stop()

# Find latest state + workdir
latest = events[-1]
state = latest.get("state") or {}
code_files = latest.get("code_files") or []
workdir = None
for e in events:
    if "workdir" in e:
        workdir = e.get("workdir")
        break
workdir_path = Path(workdir).resolve() if workdir else None

col1, col2, col3, col4 = st.columns(4)
col1.metric("run_id", latest.get("run_id", ""))
col2.metric("iterations", state.get("iteration", 0))
col3.metric("qa_passed", str(not bool(state.get("error_log"))))
col4.metric("files(in-mem)", str(len(code_files)))

st.caption(f"log: `{log_path}`")
if workdir_path:
    st.caption(f"workdir: `{workdir_path}`")

tabs = st.tabs(["Trace", "QA", "Files", "Review"])

with tabs[0]:
    trace = state.get("trace") or []
    st.subheader("Trace（最近）")
    st.dataframe(trace[-200:], use_container_width=True)
    st.subheader("每一步文件变更摘要（added / modified / removed）")
    rows = []
    for e in events:
        ch = e.get("workdir_changes") or {}
        last_trace = e.get("last_trace") or {}
        rows.append(
            {
                "ts": e.get("ts"),
                "event": e.get("event"),
                "node": last_trace.get("node"),
                "message": last_trace.get("message"),
                "added": len(ch.get("added") or []),
                "modified": len(ch.get("modified") or []),
                "removed": len(ch.get("removed") or []),
            }
        )
    st.dataframe(rows[-300:], use_container_width=True)

with tabs[1]:
    st.subheader("QA 报告 / 报错")
    err = state.get("error_log") or ""
    qa_report = state.get("qa_report") or ""
    if err:
        st.error("当前存在 error_log（会触发重试或失败退出）")
        st.code(err)
    st.text_area("qa_report", value=qa_report, height=280)

with tabs[2]:
    st.subheader("文件树（workdir）")
    if not workdir_path:
        st.info("日志里没有 workdir 信息。")
    else:
        tree = list_files_tree(workdir_path)
        left, right = st.columns([1, 2])
        with left:
            picked = st.selectbox("选择文件查看", options=tree)
        with right:
            p = workdir_path / picked
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                content = f"<read error: {e}>"
            st.code(content, language="python" if picked.endswith(".py") else None)

    st.subheader("当前 workdir 文件哈希（最新 snapshot）")
    fps = latest.get("workdir_fingerprints") or {}
    if not fps:
        st.info("暂无 workdir_fingerprints（请用最新版本运行一次 ev_agent.run）。")
    else:
        fp_rows = [{"path": k, "size": v.get("size"), "sha256": v.get("sha256")} for k, v in fps.items()]
        st.dataframe(fp_rows, use_container_width=True, height=260)

    st.subheader("当前 snapshot 变更详情（文件列表）")
    ch = latest.get("workdir_changes") or {}
    c1, c2, c3 = st.columns(3)
    c1.text_area("added", value="\n".join(ch.get("added") or []), height=160)
    c2.text_area("modified", value="\n".join(ch.get("modified") or []), height=160)
    c3.text_area("removed", value="\n".join(ch.get("removed") or []), height=160)

with tabs[3]:
    st.subheader("Reviewer 输出")
    st.text_area("review_notes", value=state.get("review_notes") or "", height=320)

if auto:
    time.sleep(interval)
    st.rerun()


