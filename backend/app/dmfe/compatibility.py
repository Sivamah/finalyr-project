"""
DMFE Compatibility Calculator — Phase 9 Core Engine
====================================================
Loads configurable weights from SystemConfig, computes the five Phase 9
scoring factors via app.dmfe.scoring, and assembles a structured
CompatibilityResult with the weighted aggregate score

    CS = w1*Pickup + w2*Route + w3*Time + w4*Capacity + w5*Priority

plus natural-language explainability output.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.db.models import SimulationRequest, SystemConfig
from app.dmfe.scoring import (
    pickup_proximity_score,
    route_similarity_score,
    time_compatibility_score,
    vehicle_capacity_score,
    priority_score,
    weighted_compatibility_score,
    DEFAULT_WEIGHTS,
    FACTOR_KEYS,
)
from app.dmfe.score_engine import estimated_delay_score

logger = logging.getLogger(__name__)

# Config key names in SystemConfig table (Phase 9 — 5 configurable weights)
# DEFAULT_WEIGHTS is imported from app.dmfe.scoring (single source of truth)
WEIGHT_KEY_MAP = {
    "pickup":   "pickup_weight",
    "route":    "route_weight",
    "time":     "time_weight",
    "capacity": "capacity_weight",
    "priority": "priority_weight",
}


@dataclass
class CompatibilityResult:
    """Full output of one compatibility evaluation between 2–3 requests."""

    request_ids: List[int]
    compatibility_score: float          # 0–100 (percentage)
    factor_scores: Dict[str, float]     # individual factor scores 0–1
    factor_details: Dict[str, Any]      # raw metric values per factor
    reasons: List[str]                  # human-readable explanation bullets
    estimated_delay_min: float          # additional delay from batching
    weights_used: Dict[str, float]


def _load_weights(db: Session) -> Dict[str, float]:
    """
    Read weight values from SystemConfig.  Falls back to defaults if not found.
    Normalises weights so they always sum to exactly 1.0.
    """
    weights: Dict[str, float] = {}
    for factor, key in WEIGHT_KEY_MAP.items():
        row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if row:
            try:
                weights[factor] = float(row.value)
            except (ValueError, TypeError):
                weights[factor] = DEFAULT_WEIGHTS[factor]
        else:
            weights[factor] = DEFAULT_WEIGHTS[factor]

    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    else:
        weights = dict(DEFAULT_WEIGHTS)

    return weights


def _get_ai_rules(db: Session) -> Dict[str, float]:
    """Load numeric AI rule settings from SystemConfig."""
    rules: Dict[str, float] = {
        "max_pickup_radius_km": 5.0,
        "max_allowed_delay_min": 20.0,
        "max_vehicle_capacity": 6,
        "max_weight_kg": 100.0,
    }
    key_map = {
        "max_pickup_radius_km": "max_pickup_radius_km",
        "max_allowed_delay_min": "max_allowed_delay_min",
        "max_vehicle_capacity": "max_vehicle_capacity",
    }
    for field_name, cfg_key in key_map.items():
        row = db.query(SystemConfig).filter(SystemConfig.key == cfg_key).first()
        if row:
            try:
                rules[field_name] = float(row.value)
            except (ValueError, TypeError):
                pass
    return rules


class CompatibilityCalculator:
    """
    Evaluates compatibility between a group of SimulationRequests.

    Usage:
        calc = CompatibilityCalculator()
        result = calc.compute([req1, req2], db)
    """

    def compute(
        self,
        requests: List[SimulationRequest],
        db: Session,
    ) -> CompatibilityResult:
        """
        Compute a full CompatibilityResult for a group of 2–3 requests.
        For groups > 2, pairwise scores are averaged.
        """
        if len(requests) < 2:
            raise ValueError("Need at least 2 requests to evaluate compatibility")

        weights = _load_weights(db)
        rules = _get_ai_rules(db)

        # Evaluate all pairs and average factor scores
        factor_accum: Dict[str, List[float]] = {k: [] for k in FACTOR_KEYS}
        details: Dict[str, Any] = {}
        delay_accum: List[float] = []

        pairs = [(requests[i], requests[j])
                 for i in range(len(requests))
                 for j in range(i + 1, len(requests))]

        for r1, r2 in pairs:
            # 1. Pickup Proximity
            p_score, dist_m = pickup_proximity_score(
                r1.pickup_lat, r1.pickup_lng,
                r2.pickup_lat, r2.pickup_lng,
                max_radius_km=rules["max_pickup_radius_km"],
            )
            factor_accum["pickup"].append(p_score)
            details.setdefault("pickup_distance_m", dist_m)

            # 2. Route Similarity (direction + overlap, combined)
            r_score, r_details = route_similarity_score(
                r1.pickup_lat, r1.pickup_lng, r1.drop_lat, r1.drop_lng,
                r2.pickup_lat, r2.pickup_lng, r2.drop_lat, r2.drop_lng,
            )
            factor_accum["route"].append(r_score)
            details.setdefault("direction_similarity", r_details["direction_similarity"])
            details.setdefault("route_overlap_label", r_details["overlap_label"])

            # 3. Time Compatibility
            t_score, time_diff_min = time_compatibility_score(
                r1.request_timestamp, r2.request_timestamp,
                max_delay_min=rules["max_allowed_delay_min"],
            )
            factor_accum["time"].append(t_score)
            details.setdefault("time_diff_min", time_diff_min)

            # Estimated Delay (used in explanation, not in weighted score)
            _, delay_min = estimated_delay_score(
                r1.pickup_lat, r1.pickup_lng,
                r2.pickup_lat, r2.pickup_lng,
                max_delay_min=rules["max_allowed_delay_min"],
            )
            delay_accum.append(delay_min)

        # 4. Capacity (evaluated once across all requests)
        total_demand = sum(r.demand or 1 for r in requests)
        total_weight = sum(r.weight_kg or 0.0 for r in requests)
        cap_score, util_pct, cap_note = vehicle_capacity_score(
            total_demand, total_weight,
            max_capacity=int(rules["max_vehicle_capacity"]),
            max_weight_kg=rules.get("max_weight_kg", 100.0),
        )
        factor_accum["capacity"] = [cap_score]
        details["capacity_note"] = cap_note
        details["capacity_utilization_pct"] = util_pct
        details["total_demand"] = total_demand
        details["total_weight_kg"] = total_weight

        # Provider note (explanation only — CS uses the 5 required factors)
        provider_ids = [r.provider_id or 0 for r in requests]
        if len(set(provider_ids)) == 1:
            prov_note = "Same provider — optimal"
        else:
            prov_note = "Cross-provider batching supported"
        details["provider_note"] = prov_note

        # 5. Priority (evaluated once across all requests)
        prio_list = [r.priority or "Medium" for r in requests]
        pri_score, pri_label = priority_score(prio_list)
        factor_accum["priority"] = [pri_score]
        details["priority_label"] = pri_label

        # ── Aggregate factor scores ───────────────────────────────────────────
        avg_factors: Dict[str, float] = {
            k: (sum(v) / len(v)) if v else 0.0
            for k, v in factor_accum.items()
        }

        # Weighted compatibility score (0–100): CS = Σ wi·fi
        compatibility_pct = weighted_compatibility_score(weights, avg_factors)

        avg_delay = round(sum(delay_accum) / len(delay_accum), 1) if delay_accum else 0.0
        details["estimated_delay_min"] = avg_delay

        # ── Build natural-language explanations ───────────────────────────────
        reasons = _build_reasons(avg_factors, details, compatibility_pct, rules)

        return CompatibilityResult(
            request_ids=[r.id for r in requests],
            compatibility_score=compatibility_pct,
            factor_scores={k: round(v, 3) for k, v in avg_factors.items()},
            factor_details=details,
            reasons=reasons,
            estimated_delay_min=avg_delay,
            weights_used=weights,
        )


def _build_reasons(
    factor_scores: Dict[str, float],
    details: Dict[str, Any],
    total_score: float,
    rules: Dict[str, float],
) -> List[str]:
    """Generate ✓/✗ explainability bullets from factor scores and detail values."""
    reasons: List[str] = []

    # Pickup distance
    dist_m = details.get("pickup_distance_m", 0)
    if factor_scores.get("pickup", 0) >= 0.6:
        reasons.append(f"✓ Pickup distance is small ({dist_m:.0f} m — within acceptable range)")
    else:
        reasons.append(f"✗ Pickup distance is large ({dist_m:.0f} m — exceeds recommended radius)")

    # Route similarity (direction + overlap, combined)
    if factor_scores.get("route", 0) >= 0.6:
        reasons.append("✓ Trips share a similar route and direction")
    else:
        reasons.append("✗ Trips follow different routes or directions")

    # Route overlap detail
    overlap = details.get("route_overlap_label", "Low")
    sym = "✓" if overlap in ("High", "Medium") else "✗"
    reasons.append(f"{sym} Route overlap is {overlap}")

    # Time window
    time_diff = details.get("time_diff_min", 0)
    max_delay = rules.get("max_allowed_delay_min", 20.0)
    if factor_scores.get("time", 0) >= 0.6:
        reasons.append(f"✓ Request time difference is acceptable ({time_diff:.1f} min)")
    else:
        reasons.append(f"✗ Request time difference is too large ({time_diff:.1f} min > {max_delay:.0f} min limit)")

    # Capacity
    cap_note = details.get("capacity_note", "")
    sym = "✓" if factor_scores.get("capacity", 0) >= 0.3 else "✗"
    reasons.append(f"{sym} Vehicle capacity: {cap_note}")

    # Estimated delay
    delay = details.get("estimated_delay_min", 0)
    if delay <= 5:
        reasons.append(f"✓ Estimated additional delay is minimal ({delay:.1f} min)")
    elif delay <= max_delay:
        reasons.append(f"✓ Estimated additional delay is within limits ({delay:.1f} min)")
    else:
        reasons.append(f"✗ Estimated additional delay is excessive ({delay:.1f} min)")

    # Provider
    prov_note = details.get("provider_note", "")
    sym = "✓" if "Same" in prov_note else "~"
    reasons.append(f"{sym} {prov_note}")

    # Priority
    pri_label = details.get("priority_label", "Medium")
    sym = "✓" if pri_label in ("High", "Medium") else "~"
    reasons.append(f"{sym} Combined request priority is {pri_label}")

    return reasons
