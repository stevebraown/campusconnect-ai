"""LLM chains and prompt templates for graph reasoning.

This module provides reusable LangChain chains for various AI tasks:
  - Matching: Compatibility reasoning between student profiles
  - Safety: Content moderation classification
  - Onboarding: Guided profile setup prompts and guidance
  - Recommendations: Event/community ranking explanations

All chains use the LLM client factory (llm_client.py) which implements
Perplexity-first, OpenAI-fallback strategy.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.utils.logging_config import logger


class CompatibilityReasoning(BaseModel):
    """Output schema for compatibility reasoning."""

    why_compatible: str = Field(..., description="Why these two are compatible")
    conversation_starter: str = Field(
        ..., description="Suggested conversation starter"
    )
    compatibility_score: float = Field(..., description="Score 0-100")


def get_matching_reasoning_chain(llm):
    """Chain for compatibility reasoning between two profiles."""

    prompt = ChatPromptTemplate.from_template(
        """You are a student relationship advisor for a university.

User Profile:
Name: {name1}
Major: {major1}
Year: {year1}
Bio: {bio1}
Interests: {interests1}

Potential Match:
Name: {name2}
Major: {major2}
Year: {year2}
Bio: {bio2}
Interests: {interests2}

Initial Compatibility Score (deterministic): {score}/100

Generate:
1. Why they're compatible (100-150 words)
2. A conversation starter they could use
3. Adjusted compatibility score (0-100) based on LLM reasoning

Respond in JSON format."""
    )

    parser = JsonOutputParser(pydantic_object=CompatibilityReasoning)
    return prompt | llm | parser


class SafetyClassification(BaseModel):
    """Output schema for safety classification."""

    is_safe: bool = Field(..., description="Is content safe?")
    flags: list[str] = Field(..., description="List of flags")
    confidence: float = Field(..., description="Confidence 0-1")
    action: str = Field(..., description="allow, review, or reject")


def get_safety_classification_chain(llm):
    """Chain for nuanced safety classification."""

    prompt = ChatPromptTemplate.from_template(
        """You are a content moderator for a university social platform.

Content Type: {content_type}
Content: "{content}"

Analyze for:
1. Spam/Advertising
2. Harassment/Abuse
3. Explicit content
4. Misinformation
5. External links/phishing

Respond in JSON format with is_safe (bool), flags (list), confidence (0-1), and action (allow/review/reject)."""
    )

    parser = JsonOutputParser(pydantic_object=SafetyClassification)
    return prompt | llm | parser


class OnboardingGuidance(BaseModel):
    """Output schema for onboarding guidance."""

    next_prompt: str = Field(..., description="Next question to ask user")
    guidance: str = Field(..., description="Help text for user")


def get_onboarding_guidance_chain(llm):
    """Chain for onboarding step guidance."""

    prompt = ChatPromptTemplate.from_template(
        """You are a friendly onboarding assistant for a campus networking app.

Current step: {current_step}
Form data so far: {form_data}

Provide:
1. next_prompt: A concise question to ask the user next.
2. guidance: Short helpful guidance (1-2 sentences).

Respond in JSON format."""
    )

    parser = JsonOutputParser(pydantic_object=OnboardingGuidance)
    return prompt | llm | parser


class RecommendationScoring(BaseModel):
    """Output schema for event/community ranking reasoning."""

    reasons: dict[str, str] = Field(
        ..., description="Mapping of item_id to reason"
    )


def get_recommendations_ranking_chain(llm):
    """Chain that explains why events/communities match the user."""

    prompt = ChatPromptTemplate.from_template(
        """You are recommending campus events or student communities.

User profile: {user_profile}
Candidates: {candidates}

Return JSON mapping {item_id: reason} explaining why each item fits the user."""
    )

    parser = JsonOutputParser(pydantic_object=RecommendationScoring)
    return prompt | llm | parser


def log_llm_error(context: str, exc: Exception) -> None:
    """Log LLM errors with context for easier debugging."""

    logger.warning("LLM error in %s: %s", context, str(exc))
