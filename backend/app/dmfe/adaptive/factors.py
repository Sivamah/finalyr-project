"""
A-DMFE Module 3 — Advanced Compatibility Engine (extension factors)
===================================================================
The Phase 9 Compatibility Score (CS) is computed from the five original
factors and is preserved verbatim (backward compatibility).  On top of
that, this module evaluates nine complementary dimensions required by the
A-DMFE specification and exposes them as *extension factors* in [0, 1]:

  1. Pickup proximity        (original factor — reused)
  2. Destination similarity  (original factor — reused)
  3. Route overlap           (original factor — reused)
  4. Expected delay          (detour time estimate)
  5. Vehicle utilisation     (combined demand vs fleet capacity)
  6. Estimated waiting time  (detour + mean driver ETA)
  7. Driver workload         (fleet headroom → 1 - driver scarcity)
  8. Historical success rate (corridor success from Module 8)
  9. Environmental impact    (route overlap + fleet efficiency proxy)

Extension factors never enter CS; they feed the Batch Quality Score (BQS)
used by the Intelligent Batch Formation module.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.dmfe.adaptive._util import _clamp01
from app.dmfe.score_engine import estimated_delay_score

EXTENSION_KEYS: Tuple[str, ...] = (
    "expected_delay",
    "vehicle_utilization",
    "estimated_waiting",
    "driver_workload",
    "historical_success",
    "environmental",
)

# Default fleet efficiency reference (km/l) for the environmental score
MAX_FLEET_MILEAGE = 40.0


def compute_extension_factors(
    requests,
    context,
    rules: Dict[str, float],
    learning_state: Optional[Dict[str, Any]] = None,
    pair_overlap: Optional[float] = None,
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Compute the extension factors for a group of 2+ requests.

    Returns (scores, details):
      scores  — {extension_key: score_0_to_1}
      details — raw values for explainability (delay_min, util_pct, ...)
    """
    n = len(requests)
    max_delay = rules.get("max_allowed_delay_min", 20.0)
    max_capacity = int(rules.get("max_vehicle_capacity", 6))

    total_demand = sum(r.demand or 1 for r in requests)

    # 4. Expected delay: mean detour to the additional pickups
    delays: List[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            _, delay_min = estimated_delay_score(
                requests[i].pickup_lat, requests[i].pickup_lng,
                requests[j].pickup_lat, requests[j].pickup_lng,
                max_delay_min=max_delay,
                avg_speed_kmh=rules.get("avg_speed_kmh", 25.0),
            )
            delays.append(delay_min)
    delay_min = sum(delays) / len(delays) if delays else 0.0
    delay_score = 1.0 - _clamp01(delay_min / max_delay)

    # 5. Vehicle utilisation: how well the batch fills the vehicle
    cap = max(max_capacity, 1)
    solo_util = max((r.demand or 1) for r in requests) / cap
    batch_util = min(1.0, total_demand / cap)
    util_pct = batch_util * 100.0
    util_gain = max(0.0, batch_util - solo_util)
    utilization_score = _clamp01(util_gain / max(0.5, solo_util + 1e-9))

    # 6. Estimated waiting time: delay + mean driver ETA from context
    eta_min = getattr(context, "avg_driver_eta_min", 5.0) if context else 5.0
    waiting_min = delay_min + eta_min
    waiting_score = 1.0 - _clamp01(waiting_min / (max_delay + eta_min + 1e-9))

    # 7. Driver workload: fleet headroom (1 - scarcity)
    scarcity = getattr(context, "driver_scarcity", 0.0) if context else 0.0
    workload_score = 1.0 - _clamp01(scarcity)

    # 8. Historical success rate of this service corridor (Module 8)
    corridor = _corridor_key(requests)
    hist_score = 0.5
    if learning_state:
        corr = (learning_state.get("corridor") or {}).get(corridor) or {}
        count = int(corr.get("count", 0) or 0)
        if count > 0:
            hist_score = _clamp01(float(corr.get("success", 0.5)))
    elif context is not None and getattr(context, "raw", {}):
        hist_score = 0.5

    # 9. Environmental impact: route overlap (fuel saved by sharing)
    #     + fleet efficiency of the preferred vehicle class
    overlap = pair_overlap if pair_overlap is not None else 0.5
    fleet_metrics = getattr(context, "raw", {}) if context else {}
    fleet_mileage = float(fleet_metrics.get("fleet_mean_mileage_kmpl") or 0.0)
    if fleet_mileage > 0.0:
        efficiency = _clamp01(fleet_mileage / MAX_FLEET_MILEAGE)
    else:
        efficiency = 0.5
    env_score = _clamp01(0.6 * overlap + 0.4 * efficiency)

    scores = {
        "expected_delay": round(delay_score, 4),
        "vehicle_utilization": round(utilization_score, 4),
        "estimated_waiting": round(waiting_score, 4),
        "driver_workload": round(workload_score, 4),
        "historical_success": round(hist_score, 4),
        "environmental": round(env_score, 4),
    }
    details = {
        "expected_delay_min": round(delay_min, 2),
        "capacity_utilization_pct": round(util_pct, 1),
        "estimated_waiting_min": round(waiting_min, 2),
        "driver_availability_ratio": round(
            1.0 - scarcity, 4) if context else 1.0,
        "corridor": corridor,
        "historical_success_rate": round(hist_score, 3),
        "fleet_efficiency_index": efficiency,
        "route_overlap_used": round(overlap, 3),
    }
    return scores, details


def _corridor_key(requests) -> str:
    """Deterministic corridor key: sorted request-type pair (or single type)."""
    types = sorted({(r.request_type or "ride").lower() for r in requests})
    return "|".join(types) if types else "unknown"


def corridor_success(
    learning_state: Optional[Dict[str, Any]], type_a: str, type_b: Optional[str] = None
) -> float:
    """Historical success rate for a request-type corridor (default 0.5)."""
    key = "|".join(sorted({type_a, type_b} if type_b else {type_a}))
    if not learning_state:
        return 0.5
    corr = (learning_state.get("corridor") or {}).get(key) or {}
    count = int(corr.get("count", 0) or 0)
    if count == 0:
        return 0.5
    return _clamp01(float(corr.get("success", 0.5)))
