from __future__ import annotations

import os


DEFAULT_RAG_QUERY_FRAMEWORK = os.getenv(
    "DEFAULT_RAG_QUERY_FRAMEWORK", "llamaindex"
).strip().lower()
DEFAULT_RAG_INDEX_FRAMEWORK = os.getenv(
    "DEFAULT_RAG_INDEX_FRAMEWORK", "langchain"
).strip().lower()
DEFAULT_RAG_LITERATURE_FRAMEWORK = os.getenv(
    "DEFAULT_RAG_LITERATURE_FRAMEWORK", "llamaindex"
).strip().lower()


def choose_framework(explicit: str | None, *, default: str) -> str:
    return (explicit or default).strip().lower()

