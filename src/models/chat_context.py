"""Chat assistant context – user auth and identity for backend API calls.

Populated from /run-graph input when graph == "chat_assistant".
All chat tools must receive auth_token to call backend with Authorization: Bearer <token>.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatContext(BaseModel):
    """Context passed into chat graph nodes and tools.

    Attributes:
        auth_token: User JWT (same as frontend). Required for backend chat API.
        user_id: User UID from backend. Required. Not overridable by tools.
        tenant_id: Optional tenant for multi-tenant isolation.
    """

    auth_token: str = Field(..., min_length=1, description="User JWT for Authorization: Bearer")
    user_id: str = Field(..., min_length=1, description="User UID")
    tenant_id: Optional[str] = Field(default=None, description="Tenant for multi-tenant isolation")
