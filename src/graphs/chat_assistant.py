"""Chat assistant graph – list conversations, summarise, draft reply.

Uses chat_tools.py to call CampusConnect backend with user JWT.
All backend calls pass Authorization: Bearer {auth_token} via context.
"""

from __future__ import annotations

from langgraph.graph import StateGraph

from src.config import config
from src.graphs.base_graph import BaseGraph
from src.models.chat_context import ChatContext
from src.state import ChatAssistantState
from src.tools.chat_tools import (
    get_conversation_by_id,
    get_conversation_messages,
    list_user_conversations,
)
from src.tools.llm_client import get_llm
from src.tools.llm_tools import (
    get_conversation_summary_chain,
    get_draft_reply_chain,
    log_llm_error,
)
from src.utils.logging_config import logger


def _with_state(state: ChatAssistantState, **updates) -> ChatAssistantState:
    """Return a new state dict with updates applied."""
    return {**state, **updates}


def _check_backend_error(result: dict, context: str) -> str | None:
    """Return error string if backend returned success: False."""
    if result.get("success") is False:
        return result.get("error", f"{context} failed")
    return None


class ChatAssistantGraph(BaseGraph):
    """Graph for chat assistant: list, summarise, draft reply."""

    def __init__(self, timeout: int = 30):
        super().__init__(timeout=timeout)
        self._ctx: ChatContext | None = None

    def _context(self, state: ChatAssistantState) -> ChatContext:
        """Get ChatContext from state. Never use user_id from tools – use context.user_id."""
        if self._ctx is None:
            self._ctx = ChatContext(
                auth_token=state["auth_token"],
                user_id=state["user_id"],
                tenant_id=state.get("tenant_id") or None,
            )
        return self._ctx

    def build_graph(self) -> StateGraph:
        graph = StateGraph(ChatAssistantState)

        graph.add_node("validate_input", self.node_validate_input)
        graph.add_node("list_conversations", self.node_list_conversations)
        graph.add_node("summarise_conversation", self.node_summarise_conversation)
        graph.add_node("generate_draft_reply", self.node_draft_reply)
        graph.add_node("finalize_response", self.node_finalize_response)

        graph.set_entry_point("validate_input")

        def route_after_validate(state: ChatAssistantState) -> str:
            if state.get("error"):
                return "finalize_response"
            return state.get("action", "list_conversations")

        graph.add_conditional_edges(
            "validate_input",
            route_after_validate,
            {
                "list_conversations": "list_conversations",
                "summarise_conversation": "summarise_conversation",
                "draft_reply": "generate_draft_reply",
                "finalize_response": "finalize_response",
            },
        )
        graph.add_edge("list_conversations", "finalize_response")
        graph.add_edge("summarise_conversation", "finalize_response")
        graph.add_edge("generate_draft_reply", "finalize_response")
        graph.set_finish_point("finalize_response")

        return graph

    def node_validate_input(self, state: ChatAssistantState) -> ChatAssistantState:
        """Validate auth_token, user_id; require conversation_id for summarise/draft_reply."""
        self._log_node_execution("validate_input", state)
        auth_token = state.get("auth_token") or ""
        user_id = state.get("user_id") or ""
        action = (state.get("action") or "list_conversations").strip().lower()
        conversation_id = (state.get("conversation_id") or "").strip()

        if not auth_token:
            return _with_state(state, error="auth_token is required for chat_assistant graph")
        if not user_id:
            return _with_state(state, error="user_id is required for chat_assistant graph")

        if action in ("summarise_conversation", "draft_reply") and not conversation_id:
            return _with_state(
                state,
                error=f"conversation_id is required when action is {action}",
            )

        valid_actions = ("list_conversations", "summarise_conversation", "draft_reply")
        if action not in valid_actions:
            return _with_state(
                state,
                error=f"action must be one of: {', '.join(valid_actions)}",
            )

        return _with_state(
            state,
            auth_token=auth_token,
            user_id=user_id,
            action=action,
            conversation_id=conversation_id or state.get("conversation_id", ""),
        )

    def node_list_conversations(self, state: ChatAssistantState) -> ChatAssistantState:
        """List user's conversations via backend API."""
        self._log_node_execution("list_conversations", state)
        ctx = self._context(state)
        result = list_user_conversations(
            auth_token=ctx.auth_token,
            limit=50,
            offset=0,
        )
        err = _check_backend_error(result, "List conversations")
        if err:
            return _with_state(state, error=err)
        conversations = result.get("conversations", [])
        total = result.get("total", len(conversations))
        return _with_state(
            state,
            conversations=conversations,
            response_metadata={"total": total},
        )

    def node_summarise_conversation(self, state: ChatAssistantState) -> ChatAssistantState:
        """Fetch messages and summarise via LLM."""
        self._log_node_execution("summarise_conversation", state)
        ctx = self._context(state)
        conv_id = state.get("conversation_id", "")

        meta = get_conversation_by_id(conv_id, auth_token=ctx.auth_token)
        err = _check_backend_error(meta, "Get conversation")
        if err:
            return _with_state(state, error=err)
        state = _with_state(
            state,
            conversation_metadata=meta.get("conversation", {}),
        )

        msg_result = get_conversation_messages(
            conv_id,
            auth_token=ctx.auth_token,
            limit=50,
        )
        err = _check_backend_error(msg_result, "Get messages")
        if err:
            return _with_state(state, error=err)
        messages = msg_result.get("messages", [])
        state = _with_state(state, messages=messages)

        messages_text = "\n".join(
            f"{m.get('senderName', 'Unknown')}: {m.get('content', '')}"
            for m in messages
        )
        if not messages_text.strip():
            return _with_state(state, summary="No messages in this conversation yet.")

        llm = get_llm(temperature=0.3, timeout=20)
        chain = get_conversation_summary_chain(llm)
        try:
            out = chain.invoke({"messages_text": messages_text})
            summary = (
                getattr(out, "summary", None)
                or (out.get("summary", "") if isinstance(out, dict) else "")
                or str(out)
            )
            return _with_state(state, summary=summary or "No summary available.")
        except Exception as exc:
            log_llm_error("conversation_summary", exc)
            return _with_state(
                state,
                error="Failed to summarise conversation",
            )

    def node_draft_reply(self, state: ChatAssistantState) -> ChatAssistantState:
        """Fetch recent messages and draft a reply via LLM. Does NOT send."""
        self._log_node_execution("draft_reply", state)
        ctx = self._context(state)
        conv_id = state.get("conversation_id", "")
        user_hint = (state.get("message") or "").strip() or "friendly and natural"

        msg_result = get_conversation_messages(
            conv_id,
            auth_token=ctx.auth_token,
            limit=20,
        )
        err = _check_backend_error(msg_result, "Get messages")
        if err:
            return _with_state(state, error=err)
        messages = msg_result.get("messages", [])

        messages_text = "\n".join(
            f"{m.get('senderName', 'Unknown')}: {m.get('content', '')}"
            for m in messages
        )
        if not messages_text.strip():
            return _with_state(state, draft_reply="Hi! How can I help?")

        llm = get_llm(temperature=0.7, timeout=20)
        chain = get_draft_reply_chain(llm)
        try:
            out = chain.invoke({
                "messages_text": messages_text,
                "user_hint": user_hint,
            })
            draft = (
                getattr(out, "draft_reply", None)
                or (out.get("draft_reply", "") if isinstance(out, dict) else "")
                or str(out)
            )
            return _with_state(state, draft_reply=draft or "Hi!")
        except Exception as exc:
            log_llm_error("draft_reply", exc)
            return _with_state(
                state,
                error="Failed to draft reply",
            )

    def node_finalize_response(self, state: ChatAssistantState) -> ChatAssistantState:
        """Shape final output for the caller."""
        self._log_node_execution("finalize_response", state)
        return state


def create_chat_assistant_graph():
    """Build and compile the chat assistant graph for server usage."""
    graph_builder = ChatAssistantGraph(timeout=config.GRAPH_TIMEOUT)
    return graph_builder.compile()
