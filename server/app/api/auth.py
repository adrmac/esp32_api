from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException, Query


def _env(name: str) -> str:
    return os.getenv(name, "")


def _require_secret_token(provided: str, env_name: str) -> None:
    expected = _env(env_name)
    if not expected or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def require_status_token(
    x_status_token: str = Header(default="", alias="X-Status-Token"),
) -> None:
    _require_secret_token(x_status_token, "STATUS_TOKEN")


def require_ingest_token(
    x_ingest_token: str = Header(default="", alias="X-Ingest-Token"),
) -> None:
    _require_secret_token(x_ingest_token, "INGEST_TOKEN")


def require_rag_token(x_rag_token: str = Header(default="")) -> None:
    _require_secret_token(x_rag_token, "RAG_TOKEN")
