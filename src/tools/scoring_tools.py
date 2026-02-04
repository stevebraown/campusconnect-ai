"""Deterministic scoring utilities for matching."""

from __future__ import annotations

from src.utils.geo import haversine_meters
from src.utils.logging_config import logger


def calculate_base_compatibility_score(
    user: dict, candidate: dict
) -> int:
    """Calculate deterministic compatibility score (0-100).

    The algorithm favors shared interests and academic proximity while keeping
    weights simple and explainable for debugging.
    """

    score = 40

    user_interests = set(user.get("interests", []))
    candidate_interests = set(candidate.get("interests", []))
    common = len(user_interests.intersection(candidate_interests))
    score += min(common * 3, 30)

    if user.get("major") == candidate.get("major"):
        score += 15

    user_year = user.get("year")
    candidate_year = candidate.get("year")
    if isinstance(user_year, int) and isinstance(candidate_year, int):
        if abs(user_year - candidate_year) <= 1:
            score += 10

    if user.get("bio") and candidate.get("bio"):
        score += 5

    return min(score, 100)


def calculate_distance_score(
    user_lat: float,
    user_lng: float,
    candidate_lat: float,
    candidate_lng: float,
    max_distance_m: int = 5000,
) -> float:
    """Calculate distance-based score multiplier.

    Returns a multiplier between 0-1 to reduce the deterministic score when
    users are outside the preferred radius.
    """

    distance = haversine_meters(
        user_lat, user_lng, candidate_lat, candidate_lng
    )

    if distance <= max_distance_m:
        return 1.0

    decay = 1.0 - (distance - max_distance_m) / max_distance_m
    return max(decay, 0.0)


def filter_candidates_basic(
    candidates: list[dict],
    user: dict,
    radius_meters: int = 5000,
    min_score_threshold: int = 50,
) -> list[dict]:
    """Pre-filter candidates based on distance and base score.

    The filtering order is optimized for performance: cheap checks first,
    expensive checks (Haversine) only if needed.
    """

    filtered: list[dict] = []
    user_lat = user.get("locationLat")
    user_lng = user.get("locationLng")

    for candidate in candidates:
        if candidate.get("uid") == user.get("uid"):
            continue

        if user_lat is not None and user_lng is not None:
            cand_lat = candidate.get("locationLat")
            cand_lng = candidate.get("locationLng")
            if cand_lat is not None and cand_lng is not None:
                distance = haversine_meters(
                    user_lat, user_lng, cand_lat, cand_lng
                )
                if distance > radius_meters:
                    continue

        score = calculate_base_compatibility_score(user, candidate)
        if score < min_score_threshold:
            continue

        filtered.append(candidate)

    logger.debug("filter_candidates_basic result=%s", len(filtered))
    return filtered
