from __future__ import annotations

from typing import Any

from app.frameworks.llamaindex.runtime import get_llamaindex_query_engine


def answer_with_llamaindex(question: str) -> dict[str, Any]:
    query_engine = get_llamaindex_query_engine()
    response = query_engine.query(question)
    return {
        "question": question,
        "response": str(response),
        "answer": getattr(response, "response", str(response)),
        "metadata": getattr(response, "metadata", None),
    }
