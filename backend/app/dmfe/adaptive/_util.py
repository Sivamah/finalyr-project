"""
A-DMFE shared helpers
=====================
Tiny, dependency-free utilities used by the adaptive modules (clamping,
normalisation and context-dict coercion).  Single source of truth — the
modules that previously re-defined `_clamp` / `_clamp01` / `_ctx_dict` now
import them from here.
"""

from __future__ import annotations

from typing import Dict


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _clamp01(x: float) -> float:
    return _clamp(x, 0.0, 1.0)


def _ctx_dict(context) -> Dict[str, float]:
    """Normalise any context-like object to a plain dict."""
    if hasattr(context, "to_dict"):
        return context.to_dict()
    if hasattr(context, "__dict__"):
        return vars(context)
    if isinstance(context, dict):
        return context
    return {}