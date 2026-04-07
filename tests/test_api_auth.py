from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api import auth


def test_require_status_token_rejects_missing_header(monkeypatch) -> None:
    monkeypatch.setenv("STATUS_TOKEN", "status-secret")

    with pytest.raises(HTTPException) as exc_info:
        auth.require_status_token("")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


def test_require_status_token_accepts_valid_header(monkeypatch) -> None:
    monkeypatch.setenv("STATUS_TOKEN", "status-secret")

    assert auth.require_status_token("status-secret") is None


def test_require_ingest_token_rejects_wrong_header(monkeypatch) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "ingest-secret")

    with pytest.raises(HTTPException) as exc_info:
        auth.require_ingest_token("wrong-secret")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


def test_require_ingest_token_accepts_valid_header(monkeypatch) -> None:
    monkeypatch.setenv("INGEST_TOKEN", "ingest-secret")

    assert auth.require_ingest_token("ingest-secret") is None


def test_require_rag_token_rejects_missing_header(monkeypatch) -> None:
    monkeypatch.setenv("RAG_TOKEN", "rag-secret")

    with pytest.raises(HTTPException) as exc_info:
        auth.require_rag_token("")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


def test_require_rag_token_accepts_valid_header(monkeypatch) -> None:
    monkeypatch.setenv("RAG_TOKEN", "rag-secret")

    assert auth.require_rag_token("rag-secret") is None
