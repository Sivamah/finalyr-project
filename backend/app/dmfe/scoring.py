"""
DMFE Scoring Module — Phase 9 Core Engine
==========================================
Pure scoring functions providing exactly the five factors required by the
weighted Compatibility Score formula:

    CS = w1*Pickup + w2*Route + w3*Time + w4*Capacity + w5*Priority

Every factor function returns a float in [0.0, 1.0] where 1.0 is the most
compatible outcome.  No database access, no routing engine, no external
APIs — only arithmetic on coordinates, vectors and timestamps.

The low-level math is reused from app.dmfe.score_engine (single source of
truth for Phase 8); this module defines the Phase 9 factor set and the
weighted aggregation helper.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

from app.dmfe.score_engine import (
    pickup_distance_score,
    destination_similarity_score,
    route_overlap_score,
    time_window_score,
    priority_score as _priority_score,
    vehicle_capacity_score as _capacity_score,
    fuel_score,
    co2_score,
    cost_score,
    delay_penalty_score,
)

# ─────────────────────────────────────────────────────────────────────────────
# Configurable default weights (w1..w5) — must sum to 1.0
# Overridden at runtime from the SystemConfig table by compatibility.py.
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS: Dict[str, float] = {
    "pickup":   0.30,   # w1 — Pickup Proximity Score
    "route":    0.25,   # w2 — Route Similarity Score
    "time":     0.20,   # w3 — Time Compatibility Score
    "capacity": 0.15,   # w4 — Vehicle Capacity Score
    "priority": 0.10,   # w5 — Priority Score
}

FACTOR_KEYS: Tuple[str, ...] = tuple(DEFAULT_WEIGHTS.keys())


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pickup Proximity Score
# ─────────────────────────────────────────────────────────────────────────────

def pickup_proximity_score(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
    max_radius_km: float = 5.0,
) -> Tuple[float, float]:
    """
    Score based on the real-world distance between two pickup locations.

    Closer pickups → higher score.  Returns (score, distance_m).
    """
    return pickup_distance_score(lat1, lng1, lat2, lng2, max_radius_km)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Route Similarity Score
# ─────────────────────────────────────────────────────────────────────────────

def route_similarity_score(
    pickup1_lat: float, pickup1_lng: float, drop1_lat: float, drop1_lng: float,
    pickup2_lat: float, pickup2_lng: float, drop2_lat: float, drop2_lng: float,
) -> Tuple[float, Dict[str, float]]:
    """
    Combined "Route Similarity" factor (w2).

    Average of two complementary measures:
      - direction_similarity: cosine similarity of the two trip vectors
        (same direction → 1.0, opposite → 0.0)
      - overlap_score:       fraction of the combined trip that is shared
        (estimated from midpoint gap vs average trip length)

    Returns (score, details) where details contains the raw sub-metrics.
    """
    direction = destination_similarity_score(
        pickup1_lat, pickup1_lng, drop1_lat, drop1_lng,
        pickup2_lat, pickup2_lng, drop2_lat, drop2_lng,
    )
    overlap, label = route_overlap_score(
        pickup1_lat, pickup1_lng, drop1_lat, drop1_lng,
        pickup2_lat, pickup2_lng, drop2_lat, drop2_lng,
    )
    score = (direction + overlap) / 2.0
    return round(score, 4), {
        "direction_similarity": direction,
        "overlap_score": overlap,
        "overlap_label": label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Time Compatibility Score
# ─────────────────────────────────────────────────────────────────────────────

def time_compatibility_score(
    ts1: datetime,
    ts2: datetime,
    max_delay_min: float = 20.0,
) -> Tuple[float, float]:
    """
    Score based on the time difference between two request timestamps.

    Requests within the same time window score 1.0; requests beyond
    max_delay_min score 0.0 (linear decay in between).
    Returns (score, time_diff_minutes).
    """
    return time_window_score(ts1, ts2, max_delay_min)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Vehicle Capacity Score
# ─────────────────────────────────────────────────────────────────────────────

def vehicle_capacity_score(
    total_demand: int,
    total_weight_kg: float,
    max_capacity: int = 6,
    max_weight_kg: float = 100.0,
) -> Tuple[float, float, str]:
    """
    Score based on whether the combined requests fit in a single vehicle.

    Returns (score, utilization_pct, note).
    """
    score, note = _capacity_score(
        total_demand, total_weight_kg,
        max_capacity=max_capacity, max_weight_kg=max_weight_kg,
    )
    demand_ratio = total_demand / max(max_capacity, 1)
    weight_ratio = total_weight_kg / max(max_weight_kg, 1.0)
    utilization = round(max(demand_ratio, weight_ratio) * 100.0, 1)
    return round(score, 4), utilization, note


# ─────────────────────────────────────────────────────────────────────────────
# 5. Priority Score
# ─────────────────────────────────────────────────────────────────────────────
# PRIORITY_VALUES is imported from app.dmfe.score_engine (single source).


def priority_score(priorities: List[str]) -> Tuple[float, str]:
    """
    Weighted average priority across all requests in the candidate group.

    Higher average priority → higher score (the batch is worth doing
    urgently).  Returns (score, dominant_priority_label).
    """
    return _priority_score(priorities)


# ─────────────────────────────────────────────────────────────────────────────
# Weighted Compatibility Score (CS)
# ─────────────────────────────────────────────────────────────────────────────

def weighted_compatibility_score(
    weights: Dict[str, float],
    factor_scores: Dict[str, float],
) -> float:
    """
    CS = w1*Pickup + w2*Route + w3*Time + w4*Capacity + w5*Priority

    Accepts factor scores in [0, 1] and returns the weighted aggregate
    mapped to a 0–100 percentage, rounded to 1 decimal place.

    Weights that sum to less than 1.0 are normalised so the result is
    always a true percentage of the theoretical maximum.
    """
    total_w = sum(weights.get(k, 0.0) for k in FACTOR_KEYS)
    if total_w <= 0:
        return 0.0
    cs = sum(
        weights.get(k, 0.0) * factor_scores.get(k, 0.0)
        for k in FACTOR_KEYS
    )
    return round((cs / total_w) * 100.0, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Unified Decision Score (Phase 5)
# ─────────────────────────────────────────────────────────────────────────────

UNIFIED_WEIGHTS: Dict[str, float] = {
    "compatibility": 0.40,  # Batch Compatibility Score (CS) contribution
    "driver": 0.30,         # Driver Feasibility Score contribution
    "cost": 0.10,
    "fuel": 0.05,
    "co2": 0.05,
    "delay": 0.10,
}

UNIFIED_FACTOR_KEYS: Tuple[str, ...] = tuple(UNIFIED_WEIGHTS.keys())


def unified_decision_score(
    weights: Dict[str, float],
    compatibility_pct: float,
    driver_score: float,
    cost: float,
    fuel_l: float,
    co2_kg: float,
    delay_min: float,
    max_cost: float = 50.0,
    max_fuel: float = 10.0,
    max_co2: float = 25.0,
    max_delay: float = 20.0,
) -> Tuple[float, Dict[str, float]]:
    """
    Computes the final unified feasibility score combining batch, driver,
    and normalized penalties for cost, fuel, co2, and delay.

    Returns (unified_score_pct, factor_scores)
    """
    cs_norm = compatibility_pct / 100.0 if compatibility_pct > 0 else 0.0
    f_cost, _ = cost_score(cost, max_cost)
    f_fuel, _ = fuel_score(fuel_l, max_fuel)
    f_co2, _ = co2_score(co2_kg, max_co2)
    f_delay, _ = delay_penalty_score(delay_min, max_delay)

    factor_scores = {
        "compatibility": round(cs_norm, 4),
        "driver": round(driver_score, 4),
        "cost": f_cost,
        "fuel": f_fuel,
        "co2": f_co2,
        "delay": f_delay,
    }

    total_w = sum(weights.get(k, 0.0) for k in UNIFIED_FACTOR_KEYS)
    if total_w <= 0:
        return 0.0, factor_scores

    score_val = sum(
        weights.get(k, 0.0) * factor_scores.get(k, 0.0)
        for k in UNIFIED_FACTOR_KEYS
    )

    return round((score_val / total_w) * 100.0, 1), factor_scores
