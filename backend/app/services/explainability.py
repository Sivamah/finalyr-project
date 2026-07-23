"""
Phase 8 — Explainable AI (XAI) Service

Generates structured, human-readable explanations for every DMFE batching
decision and persists them as AIDecision records.
"""

import json
import math
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import AIDecision, BatchedTrip, DriverProfile
from app.engine.distance_matrix import haversine


# ─── Configurable Weights ────────────────────────────────────────────
WEIGHTS = {
    "route_similarity":   0.30,
    "delay_impact":       0.25,
    "capacity_fit":       0.15,
    "environmental":      0.20,
    "driver_workload":    0.10,
}


# ─── Helper: Route-Similarity Score ──────────────────────────────────

def _route_similarity(requests: List[Dict[str, Any]]) -> float:
    """
    Measures how 'aligned' the pickup→drop vectors of all requests are.
    Returns 0–100.  For a single request the score is 100 (trivially similar).
    """
    if len(requests) <= 1:
        return 100.0

    # Compute the centroid of all pickups and all drops
    avg_plat = sum(r["pickup_lat"] for r in requests) / len(requests)
    avg_plng = sum(r["pickup_lng"] for r in requests) / len(requests)
    avg_dlat = sum(r["drop_lat"]   for r in requests) / len(requests)
    avg_dlng = sum(r["drop_lng"]   for r in requests) / len(requests)

    # For each request compute deviation from centroid direction
    total_deviation = 0.0
    for r in requests:
        pickup_dist = haversine(r["pickup_lat"], r["pickup_lng"], avg_plat, avg_plng)
        drop_dist   = haversine(r["drop_lat"],   r["drop_lng"],   avg_dlat, avg_dlng)
        total_deviation += pickup_dist + drop_dist

    avg_deviation = total_deviation / len(requests)
    # Normalize: <0.5 km deviation → 100, >10 km → 0
    score = max(0.0, min(100.0, 100.0 - (avg_deviation / 10.0) * 100.0))
    return round(score, 1)


# ─── Helper: Delay estimation ────────────────────────────────────────

def _estimated_delay(batch_distance_km: float, requests: List[Dict[str, Any]]) -> float:
    """
    Estimates the extra delay (minutes) caused by combining requests vs.
    serving each independently.  Avg speed assumed 30 km/h.
    """
    direct_total_km = 0.0
    for r in requests:
        direct_total_km += haversine(
            r["pickup_lat"], r["pickup_lng"],
            r["drop_lat"],   r["drop_lng"]
        )
    extra_km = max(0.0, batch_distance_km - direct_total_km)
    return round((extra_km / 30.0) * 60.0, 1)  # minutes


# ─── Helper: Environmental savings ───────────────────────────────────

def _environmental_savings(batch_distance_km: float, requests: List[Dict[str, Any]]):
    """
    Returns (fuel_saved_pct, co2_reduction_pct) comparing batch route
    distance to the sum of individual direct distances.
    """
    direct_total_km = sum(
        haversine(r["pickup_lat"], r["pickup_lng"], r["drop_lat"], r["drop_lng"])
        for r in requests
    )
    if direct_total_km == 0:
        return 0.0, 0.0

    saved_km = max(0.0, direct_total_km - batch_distance_km)
    pct = (saved_km / direct_total_km) * 100.0
    return round(pct, 1), round(pct, 1)  # fuel% ≈ co2% for simple model


# ─── Helper: Delay impact score ──────────────────────────────────────

def _delay_score(delay_min: float) -> float:
    """0 min → 100, 5 min → 50, 10+ min → 0."""
    return max(0.0, min(100.0, 100.0 - delay_min * 10.0))


# ─── Helper: Environmental score ─────────────────────────────────────

def _env_score(fuel_pct: float) -> float:
    """Higher savings → higher score.  0% → 0,  50%+ → 100."""
    return min(100.0, fuel_pct * 2.0)


# ─── Helper: Driver workload score ───────────────────────────────────

def _workload_score(request_count: int) -> float:
    """1-2 requests → 100,  5 → 60,  10+ → 20."""
    return max(20.0, 100.0 - (request_count - 1) * 10.0)


# ═══════════════════════════════════════════════════════════════════════
# Main API
# ═══════════════════════════════════════════════════════════════════════

def generate_decision(
    db: Session,
    batch: BatchedTrip,
    requests: List[Dict[str, Any]],
    batch_distance_km: float,
    driver_available: bool,
) -> AIDecision:
    """
    Scores a batch, builds a structured explanation, and persists it as
    an AIDecision row.
    """
    request_count   = len(requests)
    decision_type   = "combined" if request_count > 1 else "single"

    # ── Compute factors ──────────────────────────────────────────────
    route_sim        = _route_similarity(requests)
    delay_min        = _estimated_delay(batch_distance_km, requests)
    fuel_pct, co2_pct = _environmental_savings(batch_distance_km, requests)
    cap_sufficient   = True  # already validated by OR-Tools capacity constraint

    # ── Sub-scores ───────────────────────────────────────────────────
    s_route    = route_sim                         # already 0-100
    s_delay    = _delay_score(delay_min)
    s_capacity = 100.0 if cap_sufficient else 0.0
    s_env      = _env_score(fuel_pct)
    s_workload = _workload_score(request_count)

    # ── Weighted final score ─────────────────────────────────────────
    feasibility = (
        WEIGHTS["route_similarity"] * s_route
        + WEIGHTS["delay_impact"]   * s_delay
        + WEIGHTS["capacity_fit"]   * s_capacity
        + WEIGHTS["environmental"]  * s_env
        + WEIGHTS["driver_workload"] * s_workload
    )
    feasibility = round(min(100.0, max(0.0, feasibility)), 1)

    # ── Build explanation ────────────────────────────────────────────
    def _impact(val, threshold_good=70):
        return "positive" if val >= threshold_good else "acceptable" if val >= 40 else "negative"

    explanation = {
        "decision": "Combined Trip" if decision_type == "combined" else "Single Trip",
        "reasons": [
            {"factor": "Route Similarity",   "value": f"{route_sim}%",                "score": s_route,    "impact": _impact(s_route)},
            {"factor": "Driver Available",   "value": "Yes" if driver_available else "No", "score": 100 if driver_available else 0, "impact": "positive" if driver_available else "negative"},
            {"factor": "Capacity",           "value": "Sufficient" if cap_sufficient else "Insufficient", "score": s_capacity, "impact": _impact(s_capacity)},
            {"factor": "Estimated Delay",    "value": f"{delay_min} min",              "score": s_delay,    "impact": _impact(s_delay)},
            {"factor": "Fuel Saved",         "value": f"{fuel_pct}%",                  "score": s_env,      "impact": _impact(s_env, 30)},
            {"factor": "CO₂ Reduction",      "value": f"{co2_pct}%",                   "score": s_env,      "impact": _impact(s_env, 30)},
            {"factor": "Driver Workload",    "value": f"{request_count} requests",     "score": s_workload, "impact": _impact(s_workload)},
        ],
        "final_score": feasibility,
        "weights": WEIGHTS,
    }

    # ── Persist ──────────────────────────────────────────────────────
    record = AIDecision(
        batch_id            = batch.id,
        decision_type       = decision_type,
        feasibility_score   = feasibility,
        route_similarity    = route_sim,
        estimated_delay_min = delay_min,
        fuel_saved_pct      = fuel_pct,
        co2_reduction_pct   = co2_pct,
        driver_available    = driver_available,
        capacity_sufficient = cap_sufficient,
        request_count       = request_count,
        explanation_json    = json.dumps(explanation),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record
