"""
A-DMFE Module 2 — Adaptive Weight Generator
===========================================
Replaces the fixed Phase 9 weight vector with a context-dependent weight
vector that is recomputed once per batching run:

    w_f = base_f · (1 + Δ_f^context) · (1 + Δ_f^learned)        (normalised Σw_f = 1)

where Δ_f^context is a calibrated sensitivity ramp over the ContextProfile
signals and Δ_f^learned is a bounded correction supplied by the Learning
Component (Module 8).

Policy (deterministic and explainable):
  - Heavy traffic            → route weight up      (corridor alignment matters)
  - Many pending requests    → pickup weight up     (quick consolidation)
  - Few available drivers    → capacity weight up   (utilisation of scarce assets)
  - Emergency (High) requests→ priority weight up   (urgency drives batching)
  - Peak hour / high demand  → time weight up       (delay is more expensive)
  - Fuel/CO2 above benchmark → route weight up      (overlap saves fuel)
  - Under-utilised batches   → capacity weight up   (fill the vehicle better)

In ``admfe.mode = "static"`` the generator returns the raw configured
weights unchanged (exact Phase 9 behaviour).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.dmfe.adaptive._util import _ctx_dict
from app.dmfe.compatibility import WEIGHT_KEY_MAP, read_float_value
from app.dmfe.scoring import DEFAULT_WEIGHTS, FACTOR_KEYS

logger = logging.getLogger(__name__)

# Maximum learned perturbation per factor (Module 8 guard)
LEARNED_MAX_BIAS = 0.15

# Context sensitivity coefficients (literature-style calibrated ramps)
CONTEXT_GAINS: Dict[str, Dict[str, float]] = {
    # factor -> {signal: gain}
    "pickup":   {"demand_pressure": 0.45},
    "route":    {"traffic_index": 0.55, "rush_factor": 0.25,
                 "fuel_pressure": 0.15, "co2_pressure": 0.10},
    "time":     {"rush_factor": 0.30, "demand_pressure": 0.30},
    "capacity": {"driver_scarcity": 0.55, "capacity_stress": 0.20,
                 "utilization_gap": 0.15},
    "priority": {"priority_pressure": 0.60},
}


def _normalise(weights: Dict[str, float]) -> Dict[str, float]:
    """
    Normalise so the weights sum to exactly 1.0 (last factor absorbs the
    residual — the invariant Σw = 1 holds to machine precision).
    """
    total = sum(weights.get(k, 0.0) for k in FACTOR_KEYS)
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    keys = list(FACTOR_KEYS)
    out: Dict[str, float] = {}
    acc = 0.0
    for factor in keys[:-1]:
        out[factor] = weights.get(factor, 0.0) / total
        acc += out[factor]
    out[keys[-1]] = 1.0 - acc
    return out


def load_base_weights(db: Session) -> Dict[str, float]:
    """Read the configured (fixed) weights from SystemConfig; normalise."""
    weights: Dict[str, float] = {
        factor: read_float_value(db, key, DEFAULT_WEIGHTS[factor])
        for factor, key in WEIGHT_KEY_MAP.items()
    }
    return _normalise(weights)


class AdaptiveWeightGenerator:
    """
    Context-driven weight synthesis.  ``generate()`` returns a weight dict
    plus an explanation of every perturbation applied.
    """

    def __init__(self, mode: str = "adaptive") -> None:
        self.mode = mode

    def generate(
        self,
        db: Session,
        context: "ContextProfile",           # noqa: F821 — duck-typed
        learned_bias: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        return self.generate_with_reasons(db, context, learned_bias)["weights"]

    def generate_with_reasons(
        self,
        db: Session,
        context,
        learned_bias: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Dict]:
        """
        Returns {"weights": {...}, "reasons": [str], "drivers": {factor: [str]}}.
        In static mode the reasons list is empty and weights equal the
        configured baseline — byte-identical to Phase 9.
        """
        base = load_base_weights(db)
        if self.mode != "adaptive":
            return {
                "weights": base,
                "reasons": [],
                "drivers": {k: [] for k in FACTOR_KEYS},
            }

        ctx = _ctx_dict(context)
        learned = learned_bias or {}
        adjusted: Dict[str, float] = {}
        drivers: Dict[str, List[str]] = {k: [] for k in FACTOR_KEYS}
        reasons: List[str] = []

        for factor in FACTOR_KEYS:
            mult = 1.0
            for signal, gain in CONTEXT_GAINS.get(factor, {}).items():
                value = ctx.get(signal, 0.0)
                contribution = gain * float(value)
                if abs(contribution) > 1e-4:
                    mult *= (1.0 + contribution)
                    drivers[factor].append(
                        f"{signal}={value:.2f} → factor ×{1.0 + contribution:.2f}"
                    )
            bias = max(
                -LEARNED_MAX_BIAS, min(LEARNED_MAX_BIAS, float(learned.get(factor, 0.0)))
            )
            if abs(bias) > 1e-4:
                mult *= (1.0 + bias)
                drivers[factor].append(f"learned bias {bias:+.3f}")
            adjusted[factor] = base[factor] * mult

        weights = _normalise(adjusted)
        for factor in FACTOR_KEYS:
            delta = weights[factor] - base[factor]
            if abs(delta) > 1e-4:
                reasons.append(
                    f"{factor} weight {base[factor]:.2f} → {weights[factor]:.2f} "
                    f"({delta:+.2f})"
                )
        if not reasons:
            reasons.append("No context perturbation applied — weights stay at baseline")
        return {"weights": weights, "reasons": reasons, "drivers": drivers}


# Module-level singleton
adaptive_weight_generator = AdaptiveWeightGenerator()
