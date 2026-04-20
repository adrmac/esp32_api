from __future__ import annotations

from fastapi import HTTPException

from app.config.rag import DEFAULT_RAG_QUERY_FRAMEWORK, choose_framework
from app.frameworks.langchain.answering import answer_with_langchain
from app.frameworks.llamaindex.answering import answer_with_llamaindex


SUPPORTED_QUERY_FRAMEWORKS = {"langchain", "llamaindex"}


def answer_question(question: str, framework: str | None = None) -> dict[str, object]:
    selected = choose_framework(framework, default=DEFAULT_RAG_QUERY_FRAMEWORK)

    if selected == "langchain":
        result = answer_with_langchain(question)
    elif selected == "llamaindex":
        result = answer_with_llamaindex(question)
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported query framework '{selected}'. "
                f"Supported frameworks: {sorted(SUPPORTED_QUERY_FRAMEWORKS)}"
            ),
        )

    return {"framework": selected, **result}
