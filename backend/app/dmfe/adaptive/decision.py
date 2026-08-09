"""
A-DMFE Module 6 — Adaptive Decision Engine
==========================================
Replaces the single hard threshold ``CS >= 70`` with an adaptive decision
pipeline:

    Context → Adaptive Weights → Compatibility Matrix → Batch Score → Decision

The effective compatibility threshold θ_eff and the Batch Quality Score
threshold θ_bqs are derived from the ContextProfile:

    θ_eff = clamp(θ_base + 2·traffic − 4·demand_pressure + 3·driver_scarcity,
                  θ_min, θ_max)

    θ_bqs = clamp(0.55 + 0.04·traffic − 0.06·demand_pressure
                       + 0.05·driver_scarcity − 0.03·priority_pressure,
                  0.40, 0.75)

Decision confidence combines the score margin over θ_eff, the agreement
across the five factors, and the delay headroom:

    confidence = 100 · clamp(0.55·margin + 0.25·agreement + 0.20·delay_ok, 0, 1)

In ``admfe.mode = "static"`` every function degenerates to the exact Phase 9
behaviour (fixed threshold, no confidence).
"""

from __future__ import annotations

from typing import Any, Dict

from app.dmfe.adaptive._util import _clamp, _ctx_dict
from app.dmfe.scoring import FACTOR_KEYS

# Adaptive decision bounds
THRESHOLD_MIN = 55.0
THRESHOLD_MAX = 85.0
BQS_MIN = 0.40
BQS_MAX = 0.75
BQS_BASE = 0.55


def effective_threshold(base_threshold: float, context) -> float:
    """
    Compatibility threshold adjusted by the operating context.
    Static mode / no context → base threshold unchanged.
    """
    if context is None:
        return base_threshold
    ctx = _ctx_dict(context)
    return round(_clamp(
        base_threshold
        + 2.0 * float(ctx.get("traffic_index", 0.0))
        - 4.0 * float(ctx.get("demand_pressure", 0.0))
        + 3.0 * float(ctx.get("driver_scarcity", 0.0)),
        THRESHOLD_MIN, THRESHOLD_MAX,
    ), 1)


def bqs_threshold(context) -> float:
    """Batch Quality Score threshold derived from the context profile."""
    if context is None:
        return BQS_BASE
    ctx = _ctx_dict(context)
    return round(_clamp(
        BQS_BASE
        + 0.04 * float(ctx.get("traffic_index", 0.0))
        - 0.06 * float(ctx.get("demand_pressure", 0.0))
        + 0.05 * float(ctx.get("driver_scarcity", 0.0))
        - 0.03 * float(ctx.get("priority_pressure", 0.0)),
        BQS_MIN, BQS_MAX,
    ), 3)


def batch_quality_score(
    compatibility_score: float,
    factor_scores: Dict[str, float],
    extensions: Dict[str, float],
    factor_details: Dict[str, Any],
    rules: Dict[str, float],
    n_requests: int = 2,
) -> float:
    """
    Multi-criteria Batch Quality Score in [0, 1].

        BQS = 0.40·CS' + 0.15·Δutil + 0.20·savings + 0.15·delay_ok
              + 0.05·environmental + 0.05·historical_success

    where CS' = CS/100, Δutil = utilisation gain over solo trips,
    savings = route overlap proxy, delay_ok = 1 − delay/max_delay.
    """
    cs_norm = _clamp(compatibility_score / 100.0, 0.0, 1.0)

    util = float(extensions.get("vehicle_utilization", 0.0))

    # Savings proxy: route similarity factor (overlap + direction averaged)
    savings = _clamp(float(factor_scores.get("route", 0.0)), 0.0, 1.0)

    delay_min = float(factor_details.get("expected_delay_min", 0.0))
    max_delay = max(float(rules.get("max_allowed_delay_min", 20.0)), 1.0)
    delay_ok = _clamp(1.0 - delay_min / max_delay, 0.0, 1.0)

    env = _clamp(float(extensions.get("environmental", 0.5)), 0.0, 1.0)
    hist = _clamp(float(extensions.get("historical_success", 0.5)), 0.0, 1.0)

    bqs = (
        0.40 * cs_norm
        + 0.15 * util
        + 0.20 * savings
        + 0.15 * delay_ok
        + 0.05 * env
        + 0.05 * hist
    )
    return round(_clamp(bqs, 0.0, 1.0), 4)


def compute_confidence(
    compatibility_score: float,
    threshold: float,
    factor_scores: Dict[str, float],
    delay_min: float,
    rules: Dict[str, float],
) -> float:
    """
    Decision confidence in [0, 100]: margin over the effective threshold,
    agreement across the five factors, and delay headroom.
    """
    margin = _clamp(
        (compatibility_score - threshold) / max(100.0 - threshold, 1.0), 0.0, 1.0
    )
    values = [float(factor_scores.get(k, 0.0)) for k in FACTOR_KEYS]
    spread = (max(values) - min(values)) if values else 0.0
    agreement = _clamp(1.0 - spread, 0.0, 1.0)
    max_delay = max(float(rules.get("max_allowed_delay_min", 20.0)), 1.0)
    delay_ok = _clamp(1.0 - max(0.0, delay_min) / max_delay, 0.0, 1.0)
    conf = 100.0 * _clamp(
        0.55 * margin + 0.25 * agreement + 0.20 * delay_ok, 0.0, 1.0
    )
    return round(conf, 1)
