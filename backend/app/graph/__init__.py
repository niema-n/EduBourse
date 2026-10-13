"""J3 LangGraph orchestration core.

The public names are loaded lazily so lightweight contracts and quiz models do
not initialize the complete graph as an import side effect.
"""

__all__ = ["build_graph", "create_initial_state", "create_turn_input", "invoke_graph"]


def __getattr__(name):
    if name in {"build_graph", "invoke_graph"}:
        from app.graph.core import build_graph, invoke_graph
        return {"build_graph": build_graph, "invoke_graph": invoke_graph}[name]
    if name in {"create_initial_state", "create_turn_input"}:
        from app.graph.state import create_initial_state, create_turn_input
        return {
            "create_initial_state": create_initial_state,
            "create_turn_input": create_turn_input,
        }[name]
    raise AttributeError(name)
