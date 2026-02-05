"""Help graph for user support queries and FAQ responses."""

from __future__ import annotations

from langgraph.graph import StateGraph

from src.config import config
from src.graphs.base_graph import BaseGraph
from src.state import HelpState
from src.tools.firestore_tools import get_help_articles
from src.tools.llm_client import get_llm
from src.tools.llm_tools import get_help_answer_chain, log_llm_error
from src.utils.logging_config import logger

MAX_RESPONSE_CHARS = 500


def _with_state(state: HelpState, **updates) -> HelpState:
    """Return a new state dict with updates applied."""
    return {**state, **updates}


class HelpGraph(BaseGraph):
    """Graph that answers support/FAQ queries using Perplexity and optional Firestore FAQs."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(HelpState)
        graph.add_node("fetch_faq", self.node_fetch_faq)
        graph.add_node("generate_answer", self.node_generate_answer)
        graph.add_node("finalize_response", self.node_finalize_response)

        graph.set_entry_point("fetch_faq")
        graph.add_edge("fetch_faq", "generate_answer")
        graph.add_edge("generate_answer", "finalize_response")
        graph.set_finish_point("finalize_response")
        return graph

    def node_fetch_faq(self, state: HelpState) -> HelpState:
        """Optionally load FAQ/help articles from Firestore for context."""
        self._log_node_execution("fetch_faq", state)
        tenant_id = state.get("tenant_id") or ""
        if not tenant_id:
            return _with_state(state, faq_articles=[])

        try:
            articles = get_help_articles(tenant_id=tenant_id, limit=20)
            return _with_state(state, faq_articles=articles)
        except Exception as exc:
            logger.warning("Help: could not fetch FAQ articles: %s", str(exc))
            return _with_state(state, faq_articles=[])

    def node_generate_answer(self, state: HelpState) -> HelpState:
        """Use Perplexity LLM to generate a concise, contextual answer."""
        self._log_node_execution("generate_answer", state)
        query = (state.get("query") or "").strip()
        if not query:
            return _with_state(
                state,
                response="Please ask a question about CampusConnect (e.g. how to edit your profile, how matching works).",
                sources=[],
                confidence=0.5,
            )

        faq_articles = state.get("faq_articles") or []
        faq_context = ""
        if faq_articles:
            faq_context = "Relevant FAQ/help articles:\n"
            for a in faq_articles:
                faq_context += f"- [{a.get('id', '')}] Q: {a.get('question', '')} A: {a.get('answer', '')}\n"
        else:
            faq_context = "No FAQ articles in database. Use general knowledge about CampusConnect: profile editing, matching, events, safety."

        llm = get_llm(temperature=0.3, timeout=25)
        chain = get_help_answer_chain(llm)
        try:
            result = chain.invoke({
                "query": query,
                "faq_context": faq_context,
            })
            response = (result.get("response") or "").strip()
            if len(response) > MAX_RESPONSE_CHARS:
                response = response[: MAX_RESPONSE_CHARS - 3] + "..."
            sources = result.get("sources") or []
            if not isinstance(sources, list):
                sources = []
            confidence = float(result.get("confidence", 0.8))
            confidence = max(0.0, min(1.0, confidence))
            return _with_state(
                state,
                response=response,
                sources=sources,
                confidence=confidence,
            )
        except Exception as exc:
            log_llm_error("help_answer", exc)
            return _with_state(
                state,
                response="Sorry, I couldn't generate an answer right now. Try asking about profile settings, matching, or events.",
                sources=[],
                confidence=0.3,
            )

    def node_finalize_response(self, state: HelpState) -> HelpState:
        """Ensure output shape: response, sources, confidence."""
        self._log_node_execution("finalize_response", state)
        return _with_state(
            state,
            response=state.get("response", ""),
            sources=state.get("sources", []),
            confidence=state.get("confidence", 0.0),
        )


def create_help_graph():
    """Build and compile the help graph for server usage."""
    graph_builder = HelpGraph(timeout=config.GRAPH_TIMEOUT)
    return graph_builder.compile()
