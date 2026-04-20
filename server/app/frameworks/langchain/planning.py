from __future__ import annotations

import json

from app.frameworks.langchain.runtime import get_llm
from app.planning.planner import PLANNER_SYSTEM


def plan_with_langchain(question: str) -> str:
    llm = get_llm()
    response = llm.invoke(
        [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": question},
        ]
    )
    content = response.content
    return content if isinstance(content, str) else json.dumps(content)
