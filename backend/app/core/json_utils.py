"""
Shared JSON helpers — single tolerant decoder for DB-encoded JSON columns.
"""

import json
from typing import Any, Optional


def json_loads(value: Optional[str], default: Any = None) -> Any:
    """Decode a JSON string; return ``default`` for empty/None/malformed input."""
    if not value:
        return default
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return default