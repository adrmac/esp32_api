from __future__ import annotations

from llama_index.core import Document

from app.retrieval.vector import ingest_docs


def test_build_raw_docs_combines_pdf_and_web_docs(monkeypatch) -> None:
    pdf_doc = Document(
        text="ASHRAE comfort guidance",
        metadata={"file_name": "ASHRAE-55.pdf"},
    )
    web_doc = Document(
        text="WMO weather guidance",
        metadata={"url": "https://example.com/wmo"},
    )

    monkeypatch.setattr(ingest_docs, "load_pdf_docs", lambda: [pdf_doc])
    monkeypatch.setattr(ingest_docs, "load_web_docs", lambda: [web_doc])

    docs = ingest_docs.build_raw_docs()

    assert len(docs) == 2
    assert docs[0].metadata["category"] == "standard"
    assert docs[0].metadata["organization"] == "ASHRAE"
    assert docs[1].metadata["category"] == "guideline"
    assert docs[1].metadata["organization"] == "WMO"


def test_clean_text_normalizes_whitespace_and_nulls() -> None:
    dirty = " \ufeffhello\x00\r\n\r\n\r\nworld\t\t "
    assert ingest_docs.clean_text(dirty) == "hello\n\nworld"


def test_load_web_docs_fallback_uses_requests(monkeypatch) -> None:
    class FakeResponse:
        text = "<html><body><h1>Title</h1><p>Body copy</p></body></html>"

        def raise_for_status(self) -> None:
            return None

    def fake_import_module(name: str):
        raise ImportError(name)

    def fake_get(url: str, timeout: int):
        assert timeout == 20
        return FakeResponse()

    monkeypatch.setattr(ingest_docs.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(ingest_docs.requests, "get", fake_get)
    monkeypatch.setattr(ingest_docs, "urls", ["https://example.com/reference"])

    docs = ingest_docs.load_web_docs()

    assert len(docs) == 1
    assert docs[0].metadata["url"] == "https://example.com/reference"
    assert "Title" in docs[0].text
    assert "Body copy" in docs[0].text
