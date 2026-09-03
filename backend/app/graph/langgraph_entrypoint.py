"""LangGraph CLI entrypoint for the existing application graph."""

from typing import Any

from app.graph.core import build_graph
from app.llm.base import ProviderUnavailable


class StudioUnavailableProvider:
    def invoke_structured(self, request: object) -> object:
        raise ProviderUnavailable("No supervisor provider configured for local Studio")


def financial_assistant(config: Any):
    """Build the graph for LangGraph Studio's RunnableConfig contract."""
    del config
    return build_graph(supervisor_provider=StudioUnavailableProvider())
