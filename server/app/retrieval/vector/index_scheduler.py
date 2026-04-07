from __future__ import annotations

import time

from app.api.rag_router import rag_index


def index_loop(interval_seconds: int = 3600) -> None:
    print("Starting indexing loop...")
    while True:
        result = rag_index()
        print(result)
        time.sleep(interval_seconds)
