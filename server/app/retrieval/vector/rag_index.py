from __future__ import annotations

import os

import psycopg
from langchain_core.documents import Document
from psycopg import sql

from app.frameworks.langchain.runtime import get_vectorstore
from app.providers.ollama.config import SNAPSHOT_DATA_TABLE

test_document = Document(
    page_content="",
    metadata={
        "device_id": "device_id",
        "window_start": "window_start",
        "window_end": "window_end",
    },
)


def _stable_doc_id(document: Document) -> str:
    device_id = document.metadata["device_id"]
    window_start = str(document.metadata["window_start"])
    return f"{device_id}:{window_start}:hourly"


_stable_doc_id(test_document)


def archive_documents_in_database(
    db_url: str,
    documents: list[Document],
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
        for document in documents:
            metadata = document.metadata or {}
            cursor.execute(
                query,
                (
                    metadata["device_id"],
                    metadata["window_start"],
                    metadata["window_end"],
                    document.page_content,
                ),
            )
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    return len(documents)


def index_documents_in_vectorstore(documents: list[Document]) -> int:
    vectorstore = get_vectorstore()
    document_ids = [_stable_doc_id(document) for document in documents]
    vectorstore.add_documents(documents, ids=document_ids)
    return len(documents)
