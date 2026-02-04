"""Onboarding graph for conversational profile setup."""

from __future__ import annotations

import re

import firebase_admin
from firebase_admin import firestore
from langgraph.graph import StateGraph

from src.config import config
from src.graphs.base_graph import BaseGraph
from src.state import OnboardingState
from src.tools.llm_client import get_llm
from src.tools.llm_tools import get_onboarding_guidance_chain, log_llm_error
from src.utils.errors import FirestoreUnavailableError
from src.utils.logging_config import logger


def _with_state(state: OnboardingState, **updates) -> OnboardingState:
    """Return a new state dict with updates applied."""

    return {**state, **updates}


def _ensure_db():
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    return firestore.client()


def _is_valid_email(value: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", value))


def _validate_step_one(form_data: dict) -> dict:
    errors: dict[str, str] = {}
    if not form_data.get("name"):
        errors["name"] = "Name is required."
    email = form_data.get("email")
    if not email or not _is_valid_email(email):
        errors["email"] = "Valid email is required."
    return errors


def _validate_step_two(form_data: dict) -> dict:
    errors: dict[str, str] = {}
    if not form_data.get("major"):
        errors["major"] = "Major is required."
    year = form_data.get("year")
    if not isinstance(year, int) or year < 1 or year > 8:
        errors["year"] = "Year must be a valid integer."
    return errors


def _validate_step_three(form_data: dict) -> dict:
    errors: dict[str, str] = {}
    if not form_data.get("bio"):
        errors["bio"] = "Bio is required."
    interests = form_data.get("interests", [])
    if not interests:
        errors["interests"] = "Add at least one interest."
    return errors


def _validate_step_four(form_data: dict) -> dict:
    errors: dict[str, str] = {}
    if not form_data.get("photoUrl"):
        errors["photoUrl"] = "Profile photo is required."
    return errors


def _validate_step_five(form_data: dict) -> dict:
    errors: dict[str, str] = {}
    if form_data.get("locationLat") is None or form_data.get("locationLng") is None:
        errors["location"] = "Location permission required."
    return errors


class OnboardingGraph(BaseGraph):
    """Graph that guides onboarding and validation step-by-step."""

    def build_graph(self) -> StateGraph:
        graph = StateGraph(OnboardingState)
        graph.add_node("determine_current_step", self.node_determine_step)
        graph.add_node("validate_step_data", self.node_validate_step_data)
        graph.add_node("generate_next_prompt", self.node_generate_next_prompt)
        graph.add_node("save_progress", self.node_save_progress)
        graph.add_node("check_completion", self.node_check_completion)
        graph.add_node("finalize_onboarding", self.node_finalize_onboarding)

        graph.set_entry_point("determine_current_step")
        graph.add_edge("determine_current_step", "validate_step_data")
        graph.add_edge("validate_step_data", "generate_next_prompt")
        graph.add_edge("generate_next_prompt", "save_progress")
        graph.add_edge("save_progress", "check_completion")
        graph.add_edge("check_completion", "finalize_onboarding")
        graph.set_finish_point("finalize_onboarding")
        return graph

    def node_determine_step(self, state: OnboardingState) -> OnboardingState:
        """Determine current onboarding step based on form data."""

        self._log_node_execution("determine_current_step", state)
        if state.get("current_step"):
            return state

        form_data = state.get("form_data", {})
        if not form_data.get("name") or not form_data.get("email"):
            return _with_state(state, current_step=1)
        if not form_data.get("major") or not form_data.get("year"):
            return _with_state(state, current_step=2)
        if not form_data.get("bio") or not form_data.get("interests"):
            return _with_state(state, current_step=3)
        if not form_data.get("photoUrl"):
            return _with_state(state, current_step=4)
        if (
            form_data.get("locationLat") is None
            or form_data.get("locationLng") is None
        ):
            return _with_state(state, current_step=5)

        return _with_state(state, current_step=5)

    def node_validate_step_data(self, state: OnboardingState) -> OnboardingState:
        """Validate data for the current onboarding step."""

        self._log_node_execution("validate_step_data", state)
        step = int(state.get("current_step", 1))
        form_data = state.get("form_data", {})

        validators = {
            1: _validate_step_one,
            2: _validate_step_two,
            3: _validate_step_three,
            4: _validate_step_four,
            5: _validate_step_five,
        }
        errors = validators.get(step, _validate_step_one)(form_data)
        return _with_state(
            state, validation_errors=errors, is_valid=not bool(errors)
        )

    def node_generate_next_prompt(self, state: OnboardingState) -> OnboardingState:
        """Use LLM to generate the next onboarding question."""

        self._log_node_execution("generate_next_prompt", state)
        if not state.get("is_valid"):
            return _with_state(
                state,
                next_prompt="Please fix the highlighted fields to continue.",
            )

        llm = get_llm(temperature=0.7, timeout=30)
        chain = get_onboarding_guidance_chain(llm)
        try:
            result = chain.invoke(
                {
                    "current_step": state.get("current_step", 1),
                    "form_data": state.get("form_data", {}),
                }
            )
            return _with_state(
                state,
                next_prompt=result.get("next_prompt", ""),
                guidance=result.get("guidance", ""),
            )
        except Exception as exc:
            log_llm_error("onboarding_guidance", exc)
            return _with_state(
                state,
                next_prompt="What would you like to share next?",
                guidance="Provide the next piece of profile information.",
            )

    def node_save_progress(self, state: OnboardingState) -> OnboardingState:
        """Persist partial onboarding data to Firestore."""

        self._log_node_execution("save_progress", state)
        if not state.get("is_valid"):
            return state

        try:
            db = _ensure_db()
            doc_ref = db.collection("profiles").document(state["user_id"])
            payload = {**state.get("form_data", {}), "tenantId": state["tenant_id"]}
            doc_ref.set(payload, merge=True)
            return state
        except Exception as exc:
            logger.error("Failed to save onboarding progress: %s", str(exc))
            raise FirestoreUnavailableError(str(exc)) from exc

    def node_check_completion(self, state: OnboardingState) -> OnboardingState:
        """Check if the onboarding flow is complete."""

        self._log_node_execution("check_completion", state)
        is_valid = bool(state.get("is_valid"))
        step = int(state.get("current_step", 1))
        complete = is_valid and step >= 5
        return _with_state(state, profile_complete=complete)

    def node_finalize_onboarding(self, state: OnboardingState) -> OnboardingState:
        """Finalize onboarding response."""

        self._log_node_execution("finalize_onboarding", state)
        return _with_state(
            state,
            profile_complete=bool(state.get("profile_complete", False)),
        )


def create_onboarding_graph():
    """Build and compile the onboarding graph for server usage."""

    graph_builder = OnboardingGraph(timeout=config.GRAPH_TIMEOUT)
    return graph_builder.compile()
