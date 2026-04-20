from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.retrieval.vector import service


def test_index_snapshots_dispatches_to_langchain(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "index_snapshots_with_langchain",
        lambda **kwargs: {"snapshots_indexed": 3},
    )

    result = service.index_snapshots(db_url="postgres://example", framework="langchain")

    assert result["framework"] == "langchain"
    assert result["snapshots_indexed"] == 3


def test_index_snapshots_dispatches_to_llamaindex(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "index_snapshots_with_llamaindex",
        lambda **kwargs: {"snapshots_indexed": 2},
    )

    result = service.index_snapshots(db_url="postgres://example", framework="llamaindex")

    assert result["framework"] == "llamaindex"
    assert result["snapshots_indexed"] == 2


def test_ingest_literature_dispatches_to_langchain(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "ingest_literature_with_langchain",
        lambda: {"chunks_indexed": 7},
    )

    result = service.ingest_literature(framework="langchain")

    assert result["framework"] == "langchain"
    assert result["chunks_indexed"] == 7


def test_ingest_literature_dispatches_to_llamaindex(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "ingest_literature_with_llamaindex",
        lambda: {"chunks_indexed": 5},
    )

    result = service.ingest_literature(framework="llamaindex")

    assert result["framework"] == "llamaindex"
    assert result["chunks_indexed"] == 5


def test_index_snapshots_rejects_unknown_framework() -> None:
    with pytest.raises(HTTPException) as exc_info:
        service.index_snapshots(db_url="postgres://example", framework="bogus")

    assert exc_info.value.status_code == 400


def test_ingest_literature_rejects_unknown_framework() -> None:
    with pytest.raises(HTTPException) as exc_info:
        service.ingest_literature(framework="bogus")

    assert exc_info.value.status_code == 400
