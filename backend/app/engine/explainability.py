import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import OptimizationResult
from .distance import haversine


WEIGHTS = {
    "route_similarity":   0.30,
    "delay_impact":       0.25,
    "capacity_fit":       0.15,
    "environmental":      0.20,
    "driver_workload":    0.10,
}


def generate_explanation(result: OptimizationResult, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    request_count = len(requests)

    route_sim = _route_similarity(requests)
    delay_min = _estimated_delay(result.distance_saved_km, result.distance_saved_km + 1, requests)
    fuel_pct = (result.fuel_saved_l / max(result.fuel_saved_l + 1, 0.1)) * 100

    s_route = route_sim
    s_delay = _delay_score(delay_min)
    s_capacity = 100.0
    s_env = _env_score(fuel_pct)
    s_workload = _workload_score(request_count)

    feasibility = (
        WEIGHTS["route_similarity"] * s_route
        + WEIGHTS["delay_impact"]   * s_delay
        + WEIGHTS["capacity_fit"]   * s_capacity
        + WEIGHTS["environmental"]  * s_env
        + WEIGHTS["driver_workload"] * s_workload
    )
    feasibility = round(min(100.0, max(0.0, feasibility)), 1)

    return {
        "decision": "Batched" if request_count > 1 else "Single",
        "feasibility_score": feasibility,
        "factors": [
            {"factor": "Route Similarity",   "value": f"{route_sim}%",              "score": s_route},
            {"factor": "Estimated Delay",    "value": f"{delay_min} min",           "score": s_delay},
            {"factor": "Capacity",           "value": "Sufficient",                 "score": s_capacity},
            {"factor": "Fuel Saved",         "value": f"{fuel_pct:.1f}%",           "score": s_env},
            {"factor": "Driver Workload",    "value": f"{request_count} requests",  "score": s_workload},
        ],
        "impact": {
            "fuel_saved_l": result.fuel_saved_l,
            "co2_saved_kg": result.co2_saved_kg,
            "distance_saved_km": result.distance_saved_km,
            "cost_saved": result.estimated_cost,
        },
    }


def _route_similarity(requests: List[Dict[str, Any]]) -> float:
    if len(requests) <= 1:
        return 100.0

    avg_plat = sum(r.get("pickup_lat", 0) for r in requests) / len(requests)
    avg_plng = sum(r.get("pickup_lng", 0) for r in requests) / len(requests) if len(requests) > 0 else 0
    avg_dlat = sum(r.get("drop_lat", 0) for r in requests) / len(requests)
    avg_dlng = sum(r.get("drop_lng", 0) for r in requests) / len(requests)

    total_deviation = 0.0
    for r in requests:
        pickup_dist = haversine(r.get("pickup_lat", 0), r.get("pickup_lng", 0), avg_plat, avg_plng)
        drop_dist = haversine(r.get("drop_lat", 0), r.get("drop_lng", 0), avg_dlat, avg_dlng)
        total_deviation += pickup_dist + drop_dist

    avg_deviation = total_deviation / len(requests)
    score = max(0.0, min(100.0, 100.0 - (avg_deviation / 10.0) * 100.0))
    return round(score, 1)


def _estimated_delay(batch_distance_km: float, direct_distance_km: float, requests: List) -> float:
    extra_km = max(0.0, batch_distance_km - direct_distance_km / max(len(requests), 1))
    return round((extra_km / 30.0) * 60.0, 1)


def _delay_score(delay_min: float) -> float:
    return max(0.0, min(100.0, 100.0 - delay_min * 10.0))


def _env_score(fuel_pct: float) -> float:
    return min(100.0, fuel_pct * 2.0)


def _workload_score(request_count: int) -> float:
    return max(20.0, 100.0 - (request_count - 1) * 10.0)
