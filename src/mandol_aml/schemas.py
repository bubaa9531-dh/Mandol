"""Pydantic models for the AML Add/Search contract.

Contract reference (https://agentmemoryleaderboard.ai/api-guide):

* Add request : request_id, messages[{role, content, timestamp?}], user_id,
                session_id
* Add response: HTTP 200 with {"success": true, "request_id", "user_id",
                "session_id"} (all ids echoed byte-for-byte)
* Search req  : query, options?, user_id, top_k
* Search resp : {"data": [{id, content, score?, created_at?}]} ordered by
                relevance, at most top_k items
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class AddMessage(BaseModel):
    """One message inside an Add request."""

    role: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    timestamp: Optional[int] = Field(default=None, description="Unix milliseconds")

    @field_validator("content")
    @classmethod
    def _content_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value

    @field_validator("role")
    @classmethod
    def _role_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("role must not be blank")
        return value


class AddRequest(BaseModel):
    request_id: str = Field(..., min_length=1)
    messages: List[AddMessage] = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


class AddResponse(BaseModel):
    success: bool = True
    request_id: str
    user_id: str
    session_id: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    options: Optional[List[str]] = None
    user_id: str = Field(..., min_length=1)
    top_k: int = Field(..., ge=1, le=10000)

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value


class SearchHit(BaseModel):
    id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    score: Optional[float] = None
    created_at: Optional[str] = None


class SearchResponse(BaseModel):
    data: List[SearchHit] = Field(default_factory=list)
