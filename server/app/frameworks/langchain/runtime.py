from __future__ import annotations

from functools import lru_cache

from langchain_core.vectorstores import VectorStoreRetriever
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_postgres import PGVector

from app.providers.ollama.config import (
    OLLAMA_CHAT_MODEL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_HOST,
    PGVECTOR_CONNECTION_STRING,
    RAG_K,
    RAG_SNAPSHOT_TABLE,
    require_env,
)


@lru_cache(maxsize=1)
def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=OLLAMA_EMBED_MODEL,
        base_url=OLLAMA_HOST,
    )


@lru_cache(maxsize=1)
def get_llm() -> ChatOllama:
    return ChatOllama(
        model=OLLAMA_CHAT_MODEL,
        temperature=0.9,
        base_url=OLLAMA_HOST,
    )


@lru_cache(maxsize=1)
def get_vectorstore() -> PGVector:
    verified = require_env("PGVECTOR_CONNECTION_STRING", PGVECTOR_CONNECTION_STRING)

    return PGVector(
        embeddings=get_embeddings(),
        collection_name=RAG_SNAPSHOT_TABLE,
        connection=verified,
    )


@lru_cache(maxsize=1)
def get_retriever() -> VectorStoreRetriever:
    vs = get_vectorstore()
    return vs.as_retriever(search_kwargs={"k": RAG_K})
