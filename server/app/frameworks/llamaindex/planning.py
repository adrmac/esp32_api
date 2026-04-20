from __future__ import annotations

from llama_index.core.llms import ChatMessage, MessageRole

from app.frameworks.llamaindex.runtime import get_llamaindex_llm
from app.planning.planner import PLANNER_SYSTEM


def plan_with_llamaindex(question: str) -> str:
    llm = get_llamaindex_llm()
    response = llm.chat(
        [
            ChatMessage(role=MessageRole.SYSTEM, content=PLANNER_SYSTEM),
            ChatMessage(role=MessageRole.USER, content=question),
        ]
    )
    return response.message.content or ""
