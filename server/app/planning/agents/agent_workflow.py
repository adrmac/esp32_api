from __future__ import annotations

import asyncio
import os
from typing import Any

from llama_index.core import Settings
from llama_index.core.agent.workflow import AgentStream, ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

from app.execution.answering.rag_query import llamaindex_answer_question
from app.frameworks.llamaindex.runtime import get_llamaindex_query_engine

RAG_K = int(os.getenv("RAG_K", "25"))


def print_sources(resp: Any, max_chars: int = 800) -> None:
    print("\n=== SOURCE NODES USED ===")
    source_nodes = getattr(resp, "source_nodes", []) or []
    for i, nws in enumerate(source_nodes, 0):
        node = nws.node
        src = node.metadata.get("source", "unknown")
        print(f"\n--- #{i} score={nws.score:.4f} source={src} ---")
        print(node.get_content()[:max_chars])
    print("\n=== END SOURCES ===\n")


def build_agent():
    query_engine = get_llamaindex_query_engine()

    def temperature_analyst(question: str) -> str:
        response = query_engine.query(question)
        print_sources(response)
        return str(response)

    tool = FunctionTool.from_defaults(
        fn=temperature_analyst,
        name="temperature_analyst",
        description="""Analyzes temperature readings from the database and compares them to reference standards in the documents.
        Input is a natural language question ONLY. Do not pass JSON arguments.
        """,
    )

    agent = ReActAgent(tools=[tool], llm=Settings.llm, verbose=True)
    context = Context(agent)
    return agent, context


async def start_chat() -> None:
    agent, context = build_agent()
    print("Type 'exit' to quit.\n")

    while True:
        msg = input("You: ").strip()
        if msg.lower() in {"exit", "quit"}:
            break
        handler = agent.run(msg, ctx=context)
        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                print(event.delta, end="", flush=True)

        await handler
        print("\n\n")


def just_answer() -> None:
    question = "What was the average temperature yesterday?"
    result = llamaindex_answer_question(question)
    print("question: ", result["question"])
    print("response: ", result["response"])
    print("metadata: ", result["metadata"])


if __name__ == "__main__":
    asyncio.run(start_chat())
