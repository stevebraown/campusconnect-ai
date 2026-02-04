"""Events and communities recommendation graph."""

from __future__ import annotations

from datetime import datetime

from langgraph.graph import StateGraph

from src.config import config
from src.graphs.base_graph import BaseGraph
from src.state import EventsCommunitiesState
from src.tools.llm_client import get_llm
from src.tools.firestore_tools import (
    get_all_events,
    get_all_groups,
    get_user_profile,
)
from src.tools.llm_tools import get_recommendations_ranking_chain, log_llm_error
from src.utils.errors import FirestoreUnavailableError


def _with_state(state: EventsCommunitiesState, **updates) -> EventsCommunitiesState:
    """Return a new state dict with updates applied."""

    return {**state, **updates}


def _parse_event_time(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value)
    return None


def _score_event(event: dict, user_profile: dict) -> float:
    """Score an event using time, category, and attendance signals."""

    score = 50.0
    interests = set(user_profile.get("interests", []))
    category = event.get("category")
    if category and category in interests:
        score += 15.0

    start_time = _parse_event_time(event.get("startTime"))
    if start_time:
        hours_until = (start_time - datetime.utcnow()).total_seconds() / 3600
        if 0 <= hours_until <= 72:
            score += 10.0

    attendees = event.get("attendeesCount", 0) or 0
    score += min(float(attendees) / 10.0, 15.0)
    return score


def _score_group(group: dict, user_profile: dict) -> float:
    """Score a community group by interest and activity signals."""

    score = 50.0
    interests = set(user_profile.get("interests", []))
    tags = set(group.get("tags", []))
    common = len(interests.intersection(tags))
    score += min(common * 5.0, 20.0)

    members = group.get("memberCount", 0) or 0
    score += min(float(members) / 50.0, 15.0)
    return score


class EventsCommunitiesGraph(BaseGraph):
    """Graph that recommends campus events or communities."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(EventsCommunitiesState)
        graph.add_node("fetch_user_profile", self.node_fetch_user_profile)
        graph.add_node(
            "query_events_and_groups", self.node_query_events_and_groups
        )
        graph.add_node("rank_events", self.node_rank_events)
        graph.add_node("rank_communities", self.node_rank_communities)
        graph.add_node(
            "generate_event_reasoning", self.node_generate_reasoning
        )
        graph.add_node(
            "finalize_recommendations", self.node_finalize_recommendations
        )

        graph.set_entry_point("fetch_user_profile")
        graph.add_edge("fetch_user_profile", "query_events_and_groups")
        graph.add_edge("query_events_and_groups", "rank_events")
        graph.add_edge("rank_events", "rank_communities")
        graph.add_edge("rank_communities", "generate_event_reasoning")
        graph.add_edge("generate_event_reasoning", "finalize_recommendations")
        graph.set_finish_point("finalize_recommendations")
        return graph

    def node_fetch_user_profile(
        self, state: EventsCommunitiesState
    ) -> EventsCommunitiesState:
        """Fetch the user profile to drive recommendations."""

        try:
            self._log_node_execution("fetch_user_profile", state)
            profile = get_user_profile(state["user_id"], state["tenant_id"])
            if not profile:
                return _with_state(
                    state,
                    error=f"User profile not found: {state['user_id']}",
                )
            return _with_state(
                state,
                user_profile=profile,
                campus_id=str(profile.get("campusId", "")),
            )
        except FirestoreUnavailableError as exc:
            self._log_node_error("fetch_user_profile", exc)
            return _with_state(
                state,
                error="Firestore unavailable. Returning empty recommendations.",
            )

    def node_query_events_and_groups(
        self, state: EventsCommunitiesState
    ) -> EventsCommunitiesState:
        """Fetch event and group candidates for the campus."""

        if state.get("error"):
            return state

        try:
            self._log_node_execution("query_events_and_groups", state)
            events = get_all_events(
                state["campus_id"], state["tenant_id"], status="published"
            )
            groups = get_all_groups(
                state["campus_id"], state["tenant_id"], status="published"
            )
            return _with_state(state, candidates={"events": events, "groups": groups})
        except FirestoreUnavailableError as exc:
            self._log_node_error("query_events_and_groups", exc)
            return _with_state(
                state,
                error="Failed to load events or groups.",
                candidates={"events": [], "groups": []},
            )

    def node_rank_events(
        self, state: EventsCommunitiesState
    ) -> EventsCommunitiesState:
        """Rank events for relevance and time sensitivity."""

        if state.get("error"):
            return state

        self._log_node_execution("rank_events", state)
        events = state.get("candidates", {}).get("events", [])
        scored = [
            {**event, "score": _score_event(event, state["user_profile"])}
            for event in events
        ]
        ranked = sorted(scored, key=lambda x: x.get("score", 0), reverse=True)
        return _with_state(state, ranked_events=ranked[:10])

    def node_rank_communities(
        self, state: EventsCommunitiesState
    ) -> EventsCommunitiesState:
        """Rank communities by interest overlap and activity."""

        if state.get("error"):
            return state

        self._log_node_execution("rank_communities", state)
        groups = state.get("candidates", {}).get("groups", [])
        scored = [
            {**group, "score": _score_group(group, state["user_profile"])}
            for group in groups
        ]
        ranked = sorted(scored, key=lambda x: x.get("score", 0), reverse=True)
        return _with_state(state, ranked_groups=ranked[:10])

    def node_generate_reasoning(
        self, state: EventsCommunitiesState
    ) -> EventsCommunitiesState:
        """Use LLM to explain why items are relevant."""

        if state.get("error"):
            return state

        self._log_node_execution("generate_event_reasoning", state)
        llm = get_llm(temperature=0.7, timeout=30)
        chain = get_recommendations_ranking_chain(llm)
        candidates = (
            state.get("ranked_events", [])
            if state.get("request_type") == "events"
            else state.get("ranked_groups", [])
        )

        try:
            result = chain.invoke(
                {
                    "user_profile": state.get("user_profile", {}),
                    "candidates": candidates,
                }
            )
            return _with_state(state, reasoning=result.get("reasons", {}))
        except Exception as exc:
            log_llm_error("recommendations_reasoning", exc)
            return _with_state(state, reasoning={})

    def node_finalize_recommendations(
        self, state: EventsCommunitiesState
    ) -> EventsCommunitiesState:
        """Finalize recommendation response structure."""

        self._log_node_execution("finalize_recommendations", state)
        request_type = state.get("request_type", "events")
        items = (
            state.get("ranked_events", [])
            if request_type == "events"
            else state.get("ranked_groups", [])
        )
        reasoning = state.get("reasoning", {})
        enriched = [
            {
                **item,
                "reason": reasoning.get(item.get("id") or item.get("uid"), ""),
            }
            for item in items
        ]
        return _with_state(state, ranked_recommendations=enriched)


def create_events_communities_graph():
    """Build and compile the recommendations graph."""

    graph_builder = EventsCommunitiesGraph(timeout=config.GRAPH_TIMEOUT)
    return graph_builder.compile()
