from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppStateSnapshot:
    """Placeholder for future UI/system-state retrieval.

    The current app does not yet persist frontend filter state on the backend,
    but the retrieval tree reserves this boundary so planning can eventually
    combine sensor data, documents, and active UI state.
    """

    filters: dict[str, Any]
    selection: dict[str, Any]

