"""Safety moderation graph using pattern matching + LLM fallback."""

from __future__ import annotations

import re

from langgraph.graph import StateGraph

from src.config import config
from src.graphs.base_graph import BaseGraph
from src.state import SafetyState
from src.tools.llm_client import get_llm
from src.tools.llm_tools import get_safety_classification_chain, log_llm_error
from src.utils.logging_config import logger


SPAM_KEYWORDS = ["click here", "buy now", "limited offer"]
BANNED_WORDS = ["slur1", "slur2"]
PHISHING_PATTERNS = [r"verify.*account", r"confirm.*password"]


def _with_state(state: SafetyState, **updates) -> SafetyState:
    """Return a new state dict with updates applied."""

    return {**state, **updates}


class SafetyGraph(BaseGraph):
    """Content moderation graph with fast pattern checks and LLM fallback."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(SafetyState)
        graph.add_node("detect_spam_patterns", self.node_detect_spam_patterns)
        graph.add_node("check_explicit_content", self.node_check_explicit_content)
        graph.add_node("classify_uncertain", self.node_classify_uncertain)
        graph.add_node("determine_action", self.node_determine_action)
        graph.add_node("finalize_safety_response", self.node_finalize_response)

        graph.set_entry_point("detect_spam_patterns")
        graph.add_edge("detect_spam_patterns", "check_explicit_content")
        graph.add_edge("check_explicit_content", "classify_uncertain")
        graph.add_edge("classify_uncertain", "determine_action")
        graph.add_edge("determine_action", "finalize_safety_response")
        graph.set_finish_point("finalize_safety_response")
        return graph

    def node_detect_spam_patterns(self, state: SafetyState) -> SafetyState:
        """Detect obvious spam patterns with fast keyword matching."""

        self._log_node_execution("detect_spam_patterns", state)
        content = state.get("content", "").lower()
        flags: list[dict] = state.get("flags", []).copy()

        for keyword in SPAM_KEYWORDS:
            if keyword in content:
                flags.append(
                    {
                        "flag": "spam",
                        "confidence": 0.8,
                        "rule": "keyword_match",
                    }
                )

        for pattern in PHISHING_PATTERNS:
            if re.search(pattern, content):
                flags.append(
                    {
                        "flag": "phishing",
                        "confidence": 0.9,
                        "rule": "regex_pattern",
                    }
                )

        return _with_state(state, flags=flags)

    def node_check_explicit_content(self, state: SafetyState) -> SafetyState:
        """Detect explicit content using banned word list."""

        self._log_node_execution("check_explicit_content", state)
        content = state.get("content", "").lower()
        flags: list[dict] = state.get("flags", []).copy()

        for word in BANNED_WORDS:
            if word in content:
                flags.append(
                    {
                        "flag": "explicit",
                        "confidence": 0.95,
                        "rule": "banned_word",
                    }
                )

        return _with_state(state, flags=flags)

    def node_classify_uncertain(self, state: SafetyState) -> SafetyState:
        """Use LLM when pattern confidence is low or missing."""

        self._log_node_execution("classify_uncertain", state)
        flags = state.get("flags", [])
        max_conf = max([f.get("confidence", 0) for f in flags], default=0)

        if flags and max_conf >= 0.75:
            return _with_state(state, confidence=max_conf)

        llm = get_llm(temperature=0.7, timeout=30)
        chain = get_safety_classification_chain(llm)
        try:
            result = chain.invoke(
                {
                    "content_type": state.get("content_type", "message"),
                    "content": state.get("content", ""),
                }
            )
            llm_flags = result.get("flags", [])
            llm_conf = float(result.get("confidence", 0))
            llm_action = result.get("action", "review")
            llm_safe = bool(result.get("is_safe", False))

            return _with_state(
                state,
                flags=flags
                + [
                    {
                        "flag": flag,
                        "confidence": llm_conf,
                        "rule": "llm_classification",
                    }
                    for flag in llm_flags
                ],
                confidence=llm_conf,
                recommended_action=llm_action,
                safe=llm_safe,
            )
        except Exception as exc:
            log_llm_error("safety_classification", exc)
            return _with_state(state, confidence=max_conf or 0.5)

    def node_determine_action(self, state: SafetyState) -> SafetyState:
        """Determine final action based on flags and confidence."""

        self._log_node_execution("determine_action", state)
        flags = state.get("flags", [])
        flag_names = {f.get("flag") for f in flags}
        confidence = float(state.get("confidence", 0))

        if "explicit" in flag_names or "phishing" in flag_names:
            action = "reject"
        elif flags and confidence >= 0.7:
            action = "review"
        else:
            action = "allow"

        return _with_state(
            state,
            recommended_action=state.get("recommended_action", action),
            safe=action == "allow",
        )

    def node_finalize_response(self, state: SafetyState) -> SafetyState:
        """Finalize structured response for the API."""

        self._log_node_execution("finalize_safety_response", state)
        return _with_state(
            state,
            safe=bool(state.get("safe", False)),
            recommended_action=state.get("recommended_action", "review"),
        )


def create_safety_graph():
    """Build and compile the safety graph for server usage."""

    graph_builder = SafetyGraph(timeout=config.GRAPH_TIMEOUT)
    return graph_builder.compile()
