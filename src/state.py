"""Shared LangGraph state definitions.

All graph states are TypedDicts so state is explicit, serializable, and
consistent across graph nodes.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict

JsonDict = dict[str, object]
JsonList = list[JsonDict]


class MatchingState(TypedDict, total=False):
    """State for the matching graph.

    Fields are optional at runtime because nodes populate them progressively.
    Every field is JSON-serializable for LangGraph persistence/debugging.
    """

    # Identifies the requesting user.
    user_id: str
    # User profile loaded from profiles/{user_id}.
    user_profile: JsonDict
    # Campus scope derived from the user's profile.
    campus_id: str
    # Tenant for multi-tenant isolation.
    tenant_id: str
    # User preferences (radius, filters, etc.) from the request.
    preferences: JsonDict
    # All candidates in the same campus + tenant.
    candidates: JsonList
    # Candidates after distance/score filtering.
    filtered_candidates: JsonList
    # Candidates with deterministic scores.
    scored_matches: JsonList
    # LLM reasoning keyed by match_id.
    llm_reasoning: JsonDict
    # Final matches returned to the caller.
    final_matches: JsonList
    # Error string if any node fails.
    error: str
    # Response metadata for observability.
    response_metadata: JsonDict
    # Ranked list of top candidates.
    top_matches: JsonList


class SafetyState(TypedDict, total=False):
    """State for safety moderation."""

    # Text being moderated (post, message, bio, etc.).
    content: str
    # Content category used to tune moderation logic.
    content_type: str
    # User performing the action.
    user_id: str
    # Tenant for multi-tenant isolation.
    tenant_id: str
    # List of flags for any suspicious patterns.
    flags: JsonList
    # Final safety decision.
    safe: bool
    # Action recommendation: allow, review, reject.
    recommended_action: str
    # Error message if processing fails.
    error: str
    # Confidence score 0-1.
    confidence: float


class OnboardingState(TypedDict, total=False):
    """State for onboarding flow."""

    # User identity and tenant.
    user_id: str
    tenant_id: str
    # Current step in the onboarding flow (1-5).
    current_step: int
    # Partial form data from the user (name, major, year, etc.).
    form_data: JsonDict
    # Validation errors by field.
    validation_errors: JsonDict
    # Whether current step is valid.
    is_valid: bool
    # Whether profile is complete.
    profile_complete: bool
    # Conversation history with role/content pairs.
    conversation_history: JsonList
    # Next prompt returned by the LLM.
    next_prompt: str
    # Optional guidance text to help the user.
    guidance: str
    # Error message if any node fails.
    error: str


class ChatAssistantState(TypedDict, total=False):
    """State for the chat assistant graph."""

    # From input – action determines which path to take.
    action: str  # "list_conversations" | "summarise_conversation" | "draft_reply"
    conversation_id: str
    message: str  # Optional user hint for draft_reply (tone/style).
    auth_token: str
    user_id: str
    tenant_id: str
    # Populated by nodes.
    conversations: JsonList
    messages: JsonList
    conversation_metadata: JsonDict
    summary: str
    draft_reply: str
    response_metadata: JsonDict
    error: str


class EventsCommunitiesState(TypedDict, total=False):
    """State for events/communities recommendations."""

    # User and tenant context.
    user_id: str
    user_profile: JsonDict
    campus_id: str
    tenant_id: str
    # Request type: "events" or "communities".
    request_type: str
    # Filters to narrow recommendations.
    filters: JsonDict
    # All candidates (events or groups).
    candidates: JsonDict
    # Ranked top recommendations.
    ranked_recommendations: JsonList
    # Ranked events and groups before final selection.
    ranked_events: JsonList
    ranked_groups: JsonList
    # LLM reasoning keyed by item_id.
    reasoning: JsonDict
    # Error message if any step fails.
    error: str
