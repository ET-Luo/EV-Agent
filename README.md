# EV-Agent

一个基于 **LangGraph** 的“多智能体 AI 团队”工程骨架：通过 **PM / Architect / Coder / QA / Reviewer** 五个角色的闭环协作，端到端自动开发一个小游戏/轻量应用（MVP 先从“贪吃蛇”开始）。

## 目标（MVP）

- **输入**：一句自然语言需求
- **输出**：在本地生成 `game/` 目录（`main.py` 等），并由 QA 节点自动运行基础检查
- **关键能力**：**Self-Correction Loop**（根据报错自动修复，再次验证）

## 快速开始

1) 安装依赖（建议 Python 3.10+）：

```bash
pip install -r requirements.txt
```

2) 配置环境变量（复制一份示例，按需修改）：

- 参考 `env.example`
- 你可以在本地自行创建 `.env`（仓库不提交）

3) 运行（Mock 模式也能跑通流程）：

```bash
python -m ev_agent.run "写一个 pygame 贪吃蛇小游戏，支持方向键控制，撞墙/撞到自己则游戏结束。"
```

## 可视化面板（Streamlit）

运行面板：

```bash
streamlit run ev_agent/ui/streamlit_app.py
```

再启动一次 Agent（它会把过程写入 `logs/run_*.jsonl`，面板会自动刷新展示 trace / QA 报错 / 文件树）：

```bash
python -m ev_agent.run "Build a minimal pygame snake game"
```

## 目录结构（将逐步完善）

- `ev_agent/`: 主包（配置、LLM 适配、LangGraph 编排、agents）
- `game/`: Agent 生成的目标项目目录（默认不提交）
