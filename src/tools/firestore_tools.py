"""Firestore wrappers used by graph nodes.

These helpers centralize multi-tenant filtering, error handling, and logging
so graph nodes stay focused on orchestration logic.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, firestore


from src.utils.errors import FirestoreUnavailableError
from src.utils.logging_config import logger

_db: firestore.Client | None = None
def get_db() -> firestore.Client:
    """Get a Firestore client, initializing Firebase lazily."""
    global _db

    if _db is not None:
        return _db

    try:
        if not firebase_admin._apps:
            cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if not cred_path:
                raise RuntimeError(
                    "GOOGLE_APPLICATION_CREDENTIALS is not set"
                )

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        _db = firestore.client()
        return _db

    except Exception as exc:
        logger.error("Failed to initialize Firestore: %s", exc)
        raise FirestoreUnavailableError(str(exc)) from exc


def _get_user_doc(user_id: str) -> dict | None:
    """Fetch user document from users/{user_id}."""

    doc = get_db().collection("users").document(user_id).get()
    if not doc.exists:
        return None
    return doc.to_dict() or {}


def _merge_profile_fields(profile: dict, user_doc: dict | None) -> dict:
    """Normalize profile fields expected by matching logic."""

    merged = dict(profile)
    if user_doc:
        merged.setdefault("tenantId", user_doc.get("tenantId"))
        merged.setdefault("email", user_doc.get("email"))
        merged.setdefault("name", user_doc.get("name"))

    if "name" not in merged and merged.get("displayName"):
        merged["name"] = merged.get("displayName")
    if "major" not in merged and merged.get("degree"):
        merged["major"] = merged.get("degree")
    return merged

        
def get_user_profile(user_id: str, tenant_id: str) -> dict | None:
    """Fetch user profile from profiles/{user_id}.

    Returns None if user not found or tenant mismatch.
    """

    try:
        doc = get_db().collection("profiles").document(user_id).get()
        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        user_doc = _get_user_doc(user_id)
        if user_doc and user_doc.get("tenantId") != tenant_id:
            return None

        return _merge_profile_fields(data, user_doc)
    except Exception as exc:
        logger.error("Failed to fetch user profile: %s", str(exc))
        raise FirestoreUnavailableError(str(exc)) from exc


def get_all_profiles_in_campus(
    campus_id: str, tenant_id: str, limit: int = 100
) -> list[dict]:
    """Query all profiles in a campus for matching.

    Uses campusId + tenantId filters to ensure tenant isolation. Firestore
    composite indexes are required for multi-field queries in production.
    """

    try:
        query = get_db().collection("profiles")
        if campus_id:
            query = query.where("campusId", "==", campus_id)
        query = query.limit(limit)

        profiles = [doc.to_dict() or {} for doc in query.stream()]

        if not tenant_id:
            return profiles

        tenant_users = (
            get_db()
            .collection("users")
            .where("tenantId", "==", tenant_id)
            .stream()
        )
        tenant_uids = {
            (doc.to_dict() or {}).get("uid") or doc.id for doc in tenant_users
        }

        return [
            _merge_profile_fields(profile, _get_user_doc(profile.get("uid", "")))
            for profile in profiles
            if profile.get("uid") in tenant_uids
        ]
    except Exception as exc:
        logger.error("Failed to query profiles: %s", str(exc))
        raise FirestoreUnavailableError(str(exc)) from exc


def get_user_connections(user_id: str, tenant_id: str) -> dict:
    """Fetch user's connection status (accepted, pending, blocked)."""

    try:
        doc = get_db().collection("connections").document(user_id).get()
        if not doc.exists:
            return {"accepted": [], "pending": [], "blocked": []}

        data = doc.to_dict() or {}
        if data.get("tenantId") != tenant_id:
            return {"accepted": [], "pending": [], "blocked": []}

        return {
            "accepted": data.get("accepted", []),
            "pending": data.get("pending", []),
            "blocked": data.get("blocked", []),
        }
    except Exception as exc:
        logger.error("Failed to fetch connections: %s", str(exc))
        raise FirestoreUnavailableError(str(exc)) from exc


def get_recent_matches(
    user_id: str, tenant_id: str, days: int = 30
) -> list[dict]:
    """Fetch recent matches for this user to avoid re-suggesting.
    
    Note: Uses single-field index on userId for efficiency.
    Date filtering is done in-memory to avoid requiring composite indexes.
    """

    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = (
            get_db().collection("matches")
            .where("userId", "==", user_id)
        )
        all_matches = [doc.to_dict() or {} for doc in query.stream()]
        
        # Filter by tenant and recency in memory
        return [
            m for m in all_matches
            if m.get("tenantId") == tenant_id and 
               m.get("createdAt") and
               m["createdAt"] >= cutoff
        ]
    except Exception as exc:
        logger.error("Failed to fetch recent matches: %s", str(exc))
        raise FirestoreUnavailableError(str(exc)) from exc


def save_match(
    user_id: str,
    matched_user_id: str,
    score: float,
    reasoning: str,
    tenant_id: str,
) -> bool:
    """Save a match to the matches collection."""

    try:
        get_db().collection("matches").add(
            {
                "userId": user_id,
                "matchedUserId": matched_user_id,
                "score": score,
                "reasoning": reasoning,
                "tenantId": tenant_id,
                "createdAt": firestore.SERVER_TIMESTAMP,
            }
        )
        return True
    except Exception as exc:
        logger.error("Failed to save match: %s", str(exc))
        raise FirestoreUnavailableError(str(exc)) from exc


def get_all_events(
    campus_id: str, tenant_id: str, status: str = "published"
) -> list[dict]:
    """Query events for the events/communities graph."""

    try:
        query = (
            get_db().collection("events")
            .where("campusId", "==", campus_id)
            .where("tenantId", "==", tenant_id)
            .where("status", "==", status)
        )
        return [doc.to_dict() or {} for doc in query.stream()]
    except Exception as exc:
        logger.error("Failed to query events: %s", str(exc))
        raise FirestoreUnavailableError(str(exc)) from exc


def get_all_groups(
    campus_id: str, tenant_id: str, status: str = "published"
) -> list[dict]:
    """Query groups/communities for the recommendations graph."""

    try:
        query = (
            get_db().collection("groups")
            .where("campusId", "==", campus_id)
            .where("tenantId", "==", tenant_id)
            .where("status", "==", status)
        )
        return [doc.to_dict() or {} for doc in query.stream()]
    except Exception as exc:
        logger.error("Failed to query groups: %s", str(exc))
        raise FirestoreUnavailableError(str(exc)) from exc


def validate_user_exists(user_id: str) -> bool:
    """Quick check if user exists (used in input validation)."""

    try:
        return get_db().collection("profiles").document(user_id).get().exists
    except Exception as exc:
        logger.error("Failed to validate user exists: %s", str(exc))
        raise FirestoreUnavailableError(str(exc)) from exc


def get_help_articles(tenant_id: str, limit: int = 20) -> list[dict]:
    """Query FAQ/help articles for the Help agent (optional).

    Expects collection "help_articles" or "faq" with fields: id (or doc id),
    question, answer, tenantId (optional). Returns list of {id, question, answer}.
    """

    try:
        for coll_name in ("help_articles", "faq"):
            docs = list(get_db().collection(coll_name).limit(limit * 2).stream())
            if not docs:
                continue
            out = []
            for doc in docs:
                d = doc.to_dict() or {}
                if tenant_id and d.get("tenantId") and d.get("tenantId") != tenant_id:
                    continue
                out.append({
                    "id": str(d.get("id") or doc.id),
                    "question": d.get("question", ""),
                    "answer": d.get("answer", ""),
                })
                if len(out) >= limit:
                    break
            return out
        return []
    except Exception as exc:
        logger.warning("Failed to fetch help articles: %s", str(exc))
        return []
