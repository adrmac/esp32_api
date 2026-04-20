from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Snapshot:
    kind: Optional[str]
    device_id: Optional[str]
    window_start: Optional[str]
    window_end: Optional[str]
    source: Optional[str]


@dataclass(frozen=True)
class AnswerContext:
    text: str
    metadata: dict[str, object]


def _metadata_string(
    metadata: dict[str, object],
    key: str,
) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    return str(value)


def list_snapshots_used(contexts: list[AnswerContext]) -> list[Snapshot]:
    snapshots: list[Snapshot] = []
    for context in contexts:
        md = context.metadata
        snapshots.append(
            Snapshot(
                kind=_metadata_string(md, "kind"),
                device_id=_metadata_string(md, "device_id"),
                window_start=_metadata_string(md, "window_start"),
                window_end=_metadata_string(md, "window_end"),
                source=_metadata_string(md, "source"),
            )
        )
    return snapshots


def build_answer_prompt(question: str, contexts: list[AnswerContext]) -> str:
    context_blocks = []
    for index, context in enumerate(contexts, start=1):
        md = context.metadata
        device_id = _metadata_string(md, "device_id")
        window_start = _metadata_string(md, "window_start")
        window_end = _metadata_string(md, "window_end")
        cite = (
            f"[{index}] device={device_id} "
            f"{window_start}→{window_end}"
        )
        context_blocks.append(f"{cite}\n{context.text}".strip())

    context = "\n\n---\n\n".join(context_blocks) if context_blocks else "(no context retrieved)"

    return (
        "You are an assistant analyzing hourly sensor snapshots.\n"
        "Use ONLY the provided context. If the answer is not supported, say so.\n"
        "When you make a claim, cite sources like [1], [2].\n\n"
        f"QUESTION:\n{question}\n\n"
        f"CONTEXT:\n{context}\n\n"
        "ANSWER:\n"
    )
