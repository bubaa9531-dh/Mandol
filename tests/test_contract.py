"""Contract-level tests for the AML Add/Search adapter.

These tests only need ``pydantic`` (a Mandol dependency) and do not require the
Mandol runtime, so they run in CI or on a laptop without GPUs:

    pytest tests/test_contract.py -v
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mandol_aml.schemas import (
    AddMessage,
    AddRequest,
    AddResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)


def _sample_add() -> dict:
    return {
        "request_id": "eval:run_abc123:locomo_refined:conv-0:chunk-0",
        "messages": [
            {"role": "user", "timestamp": 1704067200000, "content": "raw memory text"}
        ],
        "user_id": "eval:run_abc123:locomo:conv-0",
        "session_id": "eval:run_abc123:sample:0",
    }


def test_add_request_accepts_valid_payload() -> None:
    req = AddRequest.model_validate(_sample_add())
    assert req.request_id.startswith("eval:")
    assert req.user_id == "eval:run_abc123:locomo:conv-0"
    assert req.messages[0].role == "user"
    assert req.messages[0].timestamp == 1704067200000


def test_add_request_rejects_missing_ids() -> None:
    payload = _sample_add()
    del payload["user_id"]
    with pytest.raises(ValidationError):
        AddRequest.model_validate(payload)


def test_add_request_rejects_blank_message_content() -> None:
    payload = _sample_add()
    payload["messages"] = [{"role": "user", "content": "   "}]
    with pytest.raises(ValidationError):
        AddRequest.model_validate(payload)


def test_add_response_echoes_ids() -> None:
    payload = _sample_add()
    resp = AddResponse(
        success=True,
        request_id=payload["request_id"],
        user_id=payload["user_id"],
        session_id=payload["session_id"],
    )
    assert resp.model_dump() == {
        "success": True,
        "request_id": payload["request_id"],
        "user_id": payload["user_id"],
        "session_id": payload["session_id"],
    }


def test_search_request_valid_and_blank_query_rejected() -> None:
    valid = SearchRequest(
        query="Which answer best matches the memory?",
        options=["A. First", "B. Second"],
        user_id="eval:run_abc123:locomo:conv-0",
        top_k=100,
    )
    assert valid.top_k == 100
    with pytest.raises(ValidationError):
        SearchRequest(query="   ", user_id="u", top_k=5)


def test_search_response_shape_matches_contract() -> None:
    resp = SearchResponse(
        data=[
            SearchHit(
                id="mem_1",
                content="remembered fact text",
                score=0.87,
                created_at="2026-07-01T12:00:00Z",
            )
        ]
    )
    dumped = resp.model_dump()
    assert set(dumped.keys()) == {"data"}
    assert set(dumped["data"][0].keys()) == {"id", "content", "score", "created_at"}


def test_search_response_empty_data_allowed() -> None:
    resp = SearchResponse(data=[])
    assert resp.model_dump() == {"data": []}
