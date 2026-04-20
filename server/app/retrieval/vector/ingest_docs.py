from __future__ import annotations

import importlib
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from llama_index.core import Document, SimpleDirectoryReader

from app.retrieval.corpus.urls import urls

BASE_DIR = Path(__file__).resolve().parents[1]
PDF_DIR = BASE_DIR / "corpus" / "pdfs"


def load_web_docs() -> list[Document]:
    try:
        web_reader_module = importlib.import_module("llama_index.readers.web")
        SimpleWebPageReader = getattr(web_reader_module, "SimpleWebPageReader")
        return SimpleWebPageReader().load_data(urls)
    except Exception:
        documents: list[Document] = []
        for url in urls:
            try:
                response = requests.get(url, timeout=20)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                documents.append(
                    Document(text=text, metadata={"url": url, "source": url})
                )
            except Exception as exc:
                print(f"[ingest_docs] Failed to load {url}: {exc}")
        return documents


def load_pdf_docs() -> list[Document]:
    return SimpleDirectoryReader(
        input_dir=str(PDF_DIR),
        recursive=True,
    ).load_data()


def normalize_metadata(doc: Document) -> Document:
    text = doc.get_content()
    meta = dict(doc.metadata or {})

    source = meta.get("file_name") or meta.get("url", "unknown")

    if "ASHRAE" in source or "ASHRAE" in text:
        meta["category"] = "standard"
        meta["organization"] = "ASHRAE"
    elif "WMO" in text or "WMO" in source:
        meta["category"] = "guideline"
        meta["organization"] = "WMO"
    else:
        meta["category"] = "paper"

    meta["source"] = source
    return Document(text=text, metadata=meta)


def build_raw_docs() -> list[Document]:
    pdf_docs = load_pdf_docs()
    web_docs = load_web_docs()
    return [normalize_metadata(d) for d in pdf_docs + web_docs]


def clean_text(s: str) -> str:
    if not s:
        return s
    s = s.replace("\x00", "")
    s = s.replace("\ufeff", "")
    s = s.replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()
