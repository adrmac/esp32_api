from __future__ import annotations

from langchain_core.documents import Document

from app.providers.ollama.config import SNAPSHOT_DATA_TABLE
from app.retrieval.vector.indexing import (
    archive_documents_in_database,
    index_documents_in_vectorstore,
)
from app.retrieval.vector.snapshots import SnapshotRecord, build_snapshot_records


def _to_langchain_documents(records: list[SnapshotRecord]) -> list[Document]:
    return [
        Document(
            page_content=record.text,
            metadata=dict(record.metadata),
        )
        for record in records
    ]


def index_snapshots_with_langchain(
    *,
    db_url: str,
    archive: str = SNAPSHOT_DATA_TABLE,
    lookback_hours: int | None = None,
) -> dict[str, object]:
    records = build_snapshot_records(lookback_hours=lookback_hours)
    documents = _to_langchain_documents(records)
    if not documents:
        note = (
            "No data to index in the last hour."
            if lookback_hours
            else "No data to index from all time."
        )
        return {"snapshots_indexed": 0, "note": note}

    index_documents_in_vectorstore(documents)
    archive_documents_in_database(
        db_url=db_url,
        snapshot_rows=[(document.page_content, document.metadata or {}) for document in documents],
        archive=archive,
    )
    return {"snapshots_indexed": len(documents)}
