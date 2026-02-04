"""Matching graph using deterministic scoring and LLM reasoning."""

from __future__ import annotations

from langgraph.graph import StateGraph

from src.config import config
from src.graphs.base_graph import BaseGraph
from src.state import MatchingState
from src.tools.firestore_tools import (
    get_all_profiles_in_campus,
    get_recent_matches,
    get_user_connections,
    get_user_profile,
    save_match,
)
from src.tools.llm_client import get_llm
from src.tools.llm_tools import get_matching_reasoning_chain, log_llm_error
from src.tools.scoring_tools import (
    calculate_base_compatibility_score,
    calculate_distance_score,
    filter_candidates_basic,
)
from src.utils.errors import FirestoreUnavailableError
from src.utils.logging_config import logger


def _with_state(state: MatchingState, **updates) -> MatchingState:
    """Return a new state dict with updates applied."""

    return {**state, **updates}


class MatchingGraph(BaseGraph):
    """Multi-step matching graph using deterministic + LLM approach."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(MatchingState)

        graph.add_node("fetch_user_profile", self.node_fetch_user_profile)
        graph.add_node("query_candidates", self.node_query_candidates)
        graph.add_node("filter_candidates", self.node_filter_candidates)
        graph.add_node("score_matches", self.node_score_matches)
        graph.add_node("rank_top_matches", self.node_rank_top_matches)
        graph.add_node("generate_reasoning", self.node_generate_reasoning)
        graph.add_node("finalize_response", self.node_finalize_response)

        graph.set_entry_point("fetch_user_profile")
        graph.add_edge("fetch_user_profile", "query_candidates")
        graph.add_edge("query_candidates", "filter_candidates")
        graph.add_edge("filter_candidates", "score_matches")
        graph.add_edge("score_matches", "rank_top_matches")
        graph.add_edge("rank_top_matches", "generate_reasoning")
        graph.add_edge("generate_reasoning", "finalize_response")
        graph.set_finish_point("finalize_response")

        return graph

    def node_fetch_user_profile(self, state: MatchingState) -> MatchingState:
        """Load the requesting user's profile."""

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
                error="Firestore unavailable. Returning empty matches.",
            )

    def node_query_candidates(self, state: MatchingState) -> MatchingState:
        """Query all profiles in the same campus and tenant."""

        if state.get("error"):
            return state

        try:
            self._log_node_execution("query_candidates", state)
            candidates = get_all_profiles_in_campus(
                campus_id=state.get("campus_id", ""),
                tenant_id=state["tenant_id"],
                limit=config.MAX_CANDIDATES,
            )
            return _with_state(state, candidates=candidates)
        except FirestoreUnavailableError as exc:
            self._log_node_error("query_candidates", exc)
            return _with_state(
                state,
                error="Failed to query candidates. Returning empty matches.",
                candidates=[],
            )

    def node_filter_candidates(self, state: MatchingState) -> MatchingState:
        """Filter out ineligible candidates before scoring."""

        if state.get("error"):
            return state

        try:
            self._log_node_execution("filter_candidates", state)
            try:
                connections = get_user_connections(
                    state["user_id"], state["tenant_id"]
                )
            except Exception as exc:
                logger.warning(
                    "Failed to fetch connections; proceeding without exclusions: %s",
                    str(exc),
                )
                connections = {"accepted": [], "pending": [], "blocked": []}

            excluded_uids = (
                set(connections.get("accepted", []))
                | set(connections.get("pending", []))
                | set(connections.get("blocked", []))
            )

            try:
                recent = get_recent_matches(
                    state["user_id"], state["tenant_id"], days=30
                )
            except Exception as exc:
                logger.warning(
                    "Failed to fetch recent matches; proceeding without exclusions: %s",
                    str(exc),
                )
                recent = []

            excluded_uids |= {
                m.get("matchedUserId") for m in recent if m.get("matchedUserId")
            }

            candidates = [
                c
                for c in state.get("candidates", [])
                if c.get("uid") not in excluded_uids
                and c.get("uid") != state["user_id"]
            ]

            radius = int(state.get("preferences", {}).get("radiusMeters", 200000))
            min_score = int(state.get("preferences", {}).get("minScore", 30))

            filtered = filter_candidates_basic(
                candidates,
                state.get("user_profile", {}),
                radius_meters=radius,
                min_score_threshold=min_score,
            )

            return _with_state(state, filtered_candidates=filtered)
        except Exception as exc:
            self._log_node_error("filter_candidates", exc)
            return _with_state(
                state,
                error="Filtering failed. Returning empty matches.",
                filtered_candidates=[],
            )

    def node_score_matches(self, state: MatchingState) -> MatchingState:
        """Calculate deterministic scores for each filtered candidate."""

        if state.get("error"):
            return state

        try:
            self._log_node_execution("score_matches", state)
            radius = int(state.get("preferences", {}).get("radiusMeters", 200000))
            scored: list[dict] = []

            user_profile = state.get("user_profile", {})
            user_lat = user_profile.get("locationLat")
            user_lng = user_profile.get("locationLng")

            for candidate in state.get("filtered_candidates", []):
                base_score = calculate_base_compatibility_score(
                    user_profile, candidate
                )
                cand_lat = candidate.get("locationLat")
                cand_lng = candidate.get("locationLng")

                if (
                    user_lat is not None
                    and user_lng is not None
                    and cand_lat is not None
                    and cand_lng is not None
                ):
                    distance_mult = calculate_distance_score(
                        user_lat,
                        user_lng,
                        cand_lat,
                        cand_lng,
                        max_distance_m=radius,
                    )
                else:
                    distance_mult = 1.0

                scored.append(
                    {
                        **candidate,
                        "deterministic_score": int(base_score * distance_mult),
                        "base_score": base_score,
                        "distance_multiplier": distance_mult,
                    }
                )

            return _with_state(state, scored_matches=scored)
        except Exception as exc:
            self._log_node_error("score_matches", exc)
            return _with_state(
                state,
                error="Scoring failed. Returning empty matches.",
                scored_matches=[],
            )

    def node_rank_top_matches(self, state: MatchingState) -> MatchingState:
        """Sort scored matches and return the top 10."""

        if state.get("error"):
            return state

        try:
            self._log_node_execution("rank_top_matches", state)
            sorted_matches = sorted(
                state.get("scored_matches", []),
                key=lambda x: x.get("deterministic_score", 0),
                reverse=True,
            )
            return _with_state(state, top_matches=sorted_matches[:10])
        except Exception as exc:
            self._log_node_error("rank_top_matches", exc)
            return _with_state(
                state,
                error="Ranking failed. Returning empty matches.",
                top_matches=[],
            )

    def node_generate_reasoning(self, state: MatchingState) -> MatchingState:
        """Use the LLM to generate compatibility reasoning."""

        if state.get("error") or not state.get("top_matches"):
            return _with_state(state, llm_reasoning={})

        llm = get_llm(temperature=0.7, timeout=30)
        chain = get_matching_reasoning_chain(llm)
        reasoning: dict[str, dict] = {}

        for match in state.get("top_matches", []):
            try:
                result = chain.invoke(
                    {
                        "name1": state["user_profile"].get("name", "User"),
                        "major1": state["user_profile"].get("major", "Unknown"),
                        "year1": state["user_profile"].get("year", 0),
                        "bio1": state["user_profile"].get("bio", ""),
                        "interests1": ", ".join(
                            state["user_profile"].get("interests", [])
                        ),
                        "name2": match.get("name", "Match"),
                        "major2": match.get("major", "Unknown"),
                        "year2": match.get("year", 0),
                        "bio2": match.get("bio", ""),
                        "interests2": ", ".join(match.get("interests", [])),
                        "score": match.get("deterministic_score", 0),
                    }
                )
                reasoning[match["uid"]] = {
                    "why_compatible": result.get("why_compatible", ""),
                    "conversation_starter": result.get(
                        "conversation_starter", ""
                    ),
                    "adjusted_score": result.get(
                        "compatibility_score",
                        match.get("deterministic_score", 0),
                    ),
                }
            except Exception as exc:
                log_llm_error("matching_reasoning", exc)
                reasoning[match["uid"]] = {
                    "why_compatible": "Based on shared interests and proximity.",
                    "conversation_starter": "Hey! Want to connect on CampusConnect?",
                    "adjusted_score": match.get("deterministic_score", 0),
                }

        return _with_state(state, llm_reasoning=reasoning)

    def node_finalize_response(self, state: MatchingState) -> MatchingState:
        """Construct final matches and response metadata."""

        if state.get("error"):
            return _with_state(
                state,
                final_matches=[],
                response_metadata={
                    "success": False,
                    "error": state.get("error"),
                    "reasoning_applied": False,
                    "total_candidates": len(state.get("candidates", [])),
                    "filtered_count": 0,
                },
            )

        final_matches: list[dict] = []
        reasoning = state.get("llm_reasoning", {})

        for match in state.get("top_matches", []):
            match_id = match.get("uid", "")
            match_reasoning = reasoning.get(match_id, {})
            final_match = {
                "id": match_id,
                "name": match.get("name"),
                "major": match.get("major"),
                "year": match.get("year"),
                "bio": match.get("bio"),
                "interests": match.get("interests", []),
                "score": match_reasoning.get(
                    "adjusted_score", match.get("deterministic_score", 0)
                ),
                "why_compatible": match_reasoning.get("why_compatible", ""),
                "conversation_starter": match_reasoning.get(
                    "conversation_starter", ""
                ),
            }
            final_matches.append(final_match)

            try:
                save_match(
                    user_id=state["user_id"],
                    matched_user_id=match_id,
                    score=float(final_match["score"]),
                    reasoning=str(final_match["why_compatible"]),
                    tenant_id=state["tenant_id"],
                )
            except Exception as exc:
                logger.warning("Failed to save match: %s", str(exc))

        metadata = {
            "success": True,
            "error": None,
            "reasoning_applied": bool(reasoning),
            "total_candidates": len(state.get("candidates", [])),
            "filtered_count": len(state.get("filtered_candidates", [])),
        }

        return _with_state(
            state, final_matches=final_matches, response_metadata=metadata
        )


def create_matching_graph():
    """Build and compile the matching graph for server usage."""

    graph_builder = MatchingGraph(timeout=config.GRAPH_TIMEOUT)
    return graph_builder.compile()
