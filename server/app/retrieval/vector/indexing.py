from __future__ import annotations

import os
from collections.abc import Mapping

import psycopg
from langchain_core.documents import Document
from psycopg import sql

from app.frameworks.langchain.runtime import get_vectorstore
from app.providers.ollama.config import SNAPSHOT_DATA_TABLE

SnapshotMetadata = Mapping[str, object]


def stable_snapshot_id(metadata: SnapshotMetadata) -> str:
    device_id = str(metadata["device_id"])
    window_start = str(metadata["window_start"])
    return f"{device_id}:{window_start}:hourly"


def archive_documents_in_database(
    db_url: str,
    snapshot_rows: list[tuple[str, SnapshotMetadata]],
    archive: str = SNAPSHOT_DATA_TABLE,
) -> int:
    query = sql.SQL(
        """
      insert into {archive} (
        device_id,
        window_start,
        window_end,
        snapshot_text
        )
      values (%s, %s, %s, %s)
      on conflict (device_id, window_start, window_end)
      do update set snapshot_text = excluded.snapshot_text
    """
    ).format(archive=sql.Identifier(archive))

    connection = psycopg.connect(db_url)
    cursor = connection.cursor()

    try:
        for snapshot_text, metadata in snapshot_rows:
            cursor.execute(
                query,
                (
                    metadata["device_id"],
                    metadata["window_start"],
                    metadata["window_end"],
                    snapshot_text,
                ),
            )
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    return len(snapshot_rows)


def index_documents_in_vectorstore(documents: list[Document]) -> int:
    vectorstore = get_vectorstore()
    document_ids = [stable_snapshot_id(document.metadata or {}) for document in documents]
    vectorstore.add_documents(documents, ids=document_ids)
    return len(documents)
