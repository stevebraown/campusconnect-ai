"""Base class for LangGraph graphs to share common behavior."""

from __future__ import annotations

from abc import ABC, abstractmethod
from langgraph.graph import StateGraph

from src.utils.logging_config import logger


class BaseGraph(ABC):
    """Abstract base class for all LangGraph implementations.

    Centralizes logging and provides a consistent compile pattern so graph
    subclasses focus on node logic rather than boilerplate.
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.logger = logger

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Build and return the StateGraph instance."""

    def _log_node_execution(self, node_name: str, state: dict) -> None:
        """Log node execution start with minimal state context."""

        self.logger.debug("Executing node: %s", node_name)

    def _log_node_error(self, node_name: str, error: Exception) -> None:
        """Log node execution error without leaking user data."""

        self.logger.error("Node %s failed: %s", node_name, str(error))

    def compile(self):
        """Build and compile the graph for execution."""

        graph = self.build_graph()
        return graph.compile()
