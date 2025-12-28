from __future__ import annotations

from langgraph.graph import END, StateGraph

from ev_agent.agents.nodes import architect_node, coder_node, pm_node, qa_node, reviewer_node
from ev_agent.schema import TeamState


def build_team_graph(*, llm_general, llm_coder, workdir, max_iters: int, fault_inject: bool = False):
    graph = StateGraph(TeamState)

    # Wrap nodes to inject deps
    graph.add_node("pm", lambda s: pm_node(s, llm_general))
    graph.add_node("architect", lambda s: architect_node(s, llm_general))
    graph.add_node("coder", lambda s: coder_node(s, llm_coder, workdir=workdir))
    graph.add_node("qa", lambda s: qa_node(s, workdir=workdir, fault_inject=fault_inject))
    graph.add_node("reviewer", lambda s: reviewer_node(s, llm_general, workdir=workdir))

    graph.set_entry_point("pm")
    graph.add_edge("pm", "architect")
    graph.add_edge("architect", "coder")
    graph.add_edge("coder", "qa")

    def route_after_qa(state: TeamState) -> str:
        if state.error_log:
            if state.iteration >= max_iters:
                return END
            return "coder"
        return "reviewer"

    graph.add_conditional_edges("qa", route_after_qa, {"coder": "coder", "reviewer": "reviewer", END: END})
    graph.add_edge("reviewer", END)

    compiled = graph.compile()
    return compiled


