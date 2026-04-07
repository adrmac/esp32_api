from __future__ import annotations

import importlib
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from llama_index.core import Document, SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from app.providers.ollama.config import (
    OLLAMA_EMBED_MODEL,
    OLLAMA_HOST,
    RAG_LITERATURE_TABLE,
    SUPABASE_DB,
    SUPABASE_DB_PASSWORD,
    SUPABASE_DB_PORT,
    SUPABASE_IPV4_HOST,
    SUPABASE_USER_NAME,
)
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


load_dotenv()
EMBED_DIM = 768


def ingest():
    embed_model = OllamaEmbedding(
        model_name=OLLAMA_EMBED_MODEL,
        base_url=OLLAMA_HOST,
    )

    raw_docs = build_raw_docs()
    splitter = SentenceSplitter(chunk_size=256, chunk_overlap=50)
    nodes = splitter.get_nodes_from_documents(raw_docs)

    for n in nodes:
        if isinstance(n, TextNode):
            n.text = clean_text(n.text)

    pgvs = PGVectorStore.from_params(
        database=SUPABASE_DB,
        host=SUPABASE_IPV4_HOST,
        password=SUPABASE_DB_PASSWORD,
        port=SUPABASE_DB_PORT,
        user=SUPABASE_USER_NAME,
        table_name=RAG_LITERATURE_TABLE,
        embed_dim=EMBED_DIM,
    )

    storage_context = StorageContext.from_defaults(vector_store=pgvs)

    VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model,
    )


if __name__ == "__main__":
    ingest()
