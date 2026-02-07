"""
Chat API tools – call CampusConnect backend REST endpoints.

These tools do NOT access Firestore directly. They call the backend API
with the user's auth token. The backend enforces permissions.

Usage: Pass auth_token (JWT) from the graph input when the backend invokes
the graph on behalf of an authenticated user.
"""

from __future__ import annotations

import httpx
from typing import Optional

from src.config import config
from src.utils.logging_config import logger


def _headers(auth_token: Optional[str] = None) -> dict:
    h = {"Content-Type": "application/json"}
    if auth_token:
        h["Authorization"] = f"Bearer {auth_token}"
    return h


def _error_from_response(r: httpx.Response, data: dict) -> str:
    """Surface clear auth errors for 401/403."""
    if r.status_code == 401:
        return "Unauthorized: invalid or expired user token"
    if r.status_code == 403:
        return "Forbidden: access denied"
    return data.get("error", f"HTTP {r.status_code}")


def list_user_conversations(
    auth_token: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    List conversations for the authenticated user (community + private).

    Args:
        auth_token: JWT for the user (required for auth)
        limit: Max conversations to return
        offset: Pagination offset

    Returns:
        dict: { success, conversations, total, ... } or { success: False, error }
    """
    url = f"{config.BACKEND_API_URL.rstrip('/')}/api/chat/conversations"
    params = {"limit": limit, "offset": offset}
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(
                url,
                params=params,
                headers=_headers(auth_token),
            )
            data = r.json() if r.content else {}
            if not r.is_success:
                return {
                    "success": False,
                    "error": _error_from_response(r, data),
                }
            return {"success": True, **data}
    except Exception as e:
        logger.error("list_user_conversations failed: %s", e)
        return {"success": False, "error": str(e)}


def get_conversation_messages(
    conversation_id: str,
    auth_token: Optional[str] = None,
    limit: int = 50,
    before: Optional[str] = None,
) -> dict:
    """
    Fetch paginated message history for a conversation.

    Args:
        conversation_id: Conversation ID
        auth_token: JWT for the user
        limit: Max messages
        before: Message ID for cursor-based pagination

    Returns:
        dict: { success, messages } or { success: False, error }
    """
    url = f"{config.BACKEND_API_URL.rstrip('/')}/api/chat/conversations/{conversation_id}/messages"
    params = {"limit": limit}
    if before:
        params["before"] = before
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(
                url,
                params=params,
                headers=_headers(auth_token),
            )
            data = r.json() if r.content else {}
            if not r.is_success:
                return {
                    "success": False,
                    "error": _error_from_response(r, data),
                }
            return {"success": True, **data}
    except Exception as e:
        logger.error("get_conversation_messages failed: %s", e)
        return {"success": False, "error": str(e)}


def send_conversation_message(
    conversation_id: str,
    content: str,
    auth_token: Optional[str] = None,
) -> dict:
    """
    Send a new message to a conversation as the authenticated user.

    Args:
        conversation_id: Conversation ID
        content: Message text
        auth_token: JWT for the user

    Returns:
        dict: { success, message } or { success: False, error }
    """
    url = f"{config.BACKEND_API_URL.rstrip('/')}/api/chat/conversations/{conversation_id}/messages"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                url,
                json={"content": content},
                headers=_headers(auth_token),
            )
            data = r.json() if r.content else {}
            if not r.is_success:
                return {
                    "success": False,
                    "error": _error_from_response(r, data),
                }
            return {"success": True, **data}
    except Exception as e:
        logger.error("send_conversation_message failed: %s", e)
        return {"success": False, "error": str(e)}


def get_conversation_by_id(
    conversation_id: str,
    auth_token: Optional[str] = None,
) -> dict:
    """
    Get conversation metadata.

    Args:
        conversation_id: Conversation ID
        auth_token: JWT for the user

    Returns:
        dict: { success, conversation } or { success: False, error }
    """
    url = f"{config.BACKEND_API_URL.rstrip('/')}/api/chat/conversations/{conversation_id}"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=_headers(auth_token))
            data = r.json() if r.content else {}
            if not r.is_success:
                return {
                    "success": False,
                    "error": _error_from_response(r, data),
                }
            return {"success": True, **data}
    except Exception as e:
        logger.error("get_conversation_by_id failed: %s", e)
        return {"success": False, "error": str(e)}
