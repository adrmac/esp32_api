from __future__ import annotations

import os
from typing import Optional


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "")

DEVICE_ID = os.getenv("DEVICE_ID", "")
RAW_DATA_TABLE = os.getenv("RAW_DATA_TABLE", "readings")
SNAPSHOT_DATA_TABLE = os.getenv("SNAPSHOT_DATA_TABLE", "snapshots")
RAG_SNAPSHOT_TABLE = os.getenv("RAG_SNAPSHOT_TABLE", "")
RAG_LITERATURE_TABLE = os.getenv("RAG_LITERATURE_TABLE", "")
PGVECTOR_CONNECTION_STRING = os.getenv("PGVECTOR_CONNECTION_STRING", "")

SUPABASE_DB = os.getenv("SUPABASE_DB", "")
SUPABASE_IPV4_HOST = os.getenv("SUPABASE_IPV4_HOST", "")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "")
SUPABASE_DB_PORT = os.getenv("SUPABASE_DB_PORT", "")
SUPABASE_USER_NAME = os.getenv("SUPABASE_USER_NAME", "")

RAG_K = int(os.getenv("RAG_K", "25"))


def require_env(name: str, value: Optional[str]) -> str:
    if not value:
        raise RuntimeError(
            f"Missing required env var: {name}. "
            f"Please set it in your .env file or environment."
        )
    return value
