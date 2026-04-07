from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import psycopg
from langchain_core.documents import Document
from psycopg import sql

from app.frameworks.langchain.runtime import get_llm, get_retriever
from app.frameworks.llamaindex.runtime import get_llamaindex_query_engine
from app.planning.core.query_planner import plan_query, resolve_time_range
from app.providers.ollama.config import DEVICE_ID, SNAPSHOT_DATA_TABLE

DATABASE_URL = os.getenv("SUPABASE_DB_URL_IPV4", "")


@dataclass
class Source:
    kind: Optional[str]
    device_id: Optional[str]
    window_start: Optional[str]
    window_end: Optional[str]
    source: Optional[str]


def _list_snapshots_used(documents: list[Document]) -> list[Source]:
    sources: list[Source] = []
    for document in documents:
        md = document.metadata or {}
        sources.append(
            Source(
                kind=md.get("kind"),
                device_id=md.get("device_id"),
                window_start=md.get("window_start"),
                window_end=md.get("window_end"),
                source=md.get("source"),
            )
        )
    return sources


def _build_prompt(question: str, documents: list[Document]) -> str:
    context_blocks = []
    for index, document in enumerate(documents, start=1):
        md = document.metadata or {}
        cite = (
            f"[{index}] device={md.get('device_id')} "
            f"{md.get('window_start')}→{md.get('window_end')}"
        )
        context_blocks.append(f"{cite}\n{document.page_content}".strip())

    context = "\n\n---\n\n".join(context_blocks) if context_blocks else "(no context retrieved)"

    return (
        "You are an assistant analyzing hourly sensor snapshots.\n"
        "Use ONLY the provided context. If the answer is not supported, say so.\n"
        "When you make a claim, cite sources like [1], [2].\n\n"
        f"QUESTION:\n{question}\n\n"
        f"CONTEXT:\n{context}\n\n"
        "ANSWER:\n"
    )


def fetch_snapshots_between(
    start_utc: datetime,
    end_utc: datetime,
    device_id: str = DEVICE_ID,
    table: str = SNAPSHOT_DATA_TABLE,
) -> list[Document]:
    query = sql.SQL(
        """
      select window_start, window_end, snapshot_text
      from {table}
      where device_id = %s
        and window_start >= %s
        and window_end <= %s
      order by window_start asc;
    """
    ).format(table=sql.Identifier(table))
    docs: list[Document] = []
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (device_id, start_utc, end_utc))
            for window_start, window_end, snapshot_text in cur.fetchall():
                docs.append(
                    Document(
                        page_content=snapshot_text,
                        metadata={
                            "kind": "hourly_snapshot",
                            "device_id": device_id,
                            "window_start": window_start.isoformat(),
                            "window_end": window_end.isoformat(),
                            "source": table,
                        },
                    )
                )
    return docs


AGG_METRICS = {
    "temperature_avg",
    "temperature_min",
    "temperature_max",
    "humidity_avg",
    "coverage_gaps",
    "latest_snapshot",
}


def llamaindex_answer_question(question: str) -> dict[str, Any]:
    query_engine = get_llamaindex_query_engine()
    response = query_engine.query(question)
    return {
        "question": question,
        "response": str(response),
        "answer": getattr(response, "response", str(response)),
        "metadata": getattr(response, "metadata", None),
    }


def langchain_answer_question(question: str) -> dict[str, Any]:
    llm = get_llm()
    plan = plan_query(question)
    metric = plan.get("metric", "none")

    if metric in AGG_METRICS:
        start_utc, end_utc = resolve_time_range(plan)
        documents = fetch_snapshots_between(start_utc, end_utc)

        if not documents:
            return {
                "question": question,
                "answer": f"No snapshots found between {start_utc.isoformat()} and {end_utc.isoformat()}.",
                "sources": [],
                "retrieved": 0,
                "plan": plan,
                "time_range_utc": {
                    "start": start_utc.isoformat(),
                    "end": end_utc.isoformat(),
                },
            }

        if metric == "latest_snapshot":
            md = documents[-1].metadata
            answer = (
                f"Most recent snapshot in range: "
                f"{md.get('window_start')} - {md.get('window_end')}."
            )
            return {
                "question": question,
                "answer": answer,
                "sources": _list_snapshots_used([documents[-1]]),
                "retrieved": len(documents),
                "plan": plan,
                "time_range_utc": {
                    "start": start_utc.isoformat(),
                    "end": end_utc.isoformat(),
                },
            }

        prompt = _build_prompt(question, documents)
        response = llm.invoke(prompt)

        return {
            "question": question,
            "answer": response.content,
            "sources": _list_snapshots_used(documents),
            "retrieved": len(documents),
            "plan": plan,
            "time_range_utc": {
                "start": start_utc.isoformat(),
                "end": end_utc.isoformat(),
            },
        }

    retriever = get_retriever()
    documents = retriever.invoke(question)
    prompt = _build_prompt(question, documents)
    response = llm.invoke(prompt)

    return {
        "question": question,
        "answer": response.content,
        "sources": _list_snapshots_used(documents),
        "retrieved": len(documents),
    }
