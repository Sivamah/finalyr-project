"""
DMFE Score Engine
=================
Pure mathematical scoring functions for the Dynamic Multi-Service Feasibility
Engine.  Every function returns a float in [0.0, 1.0] where 1.0 is the most
compatible outcome.

No routing, no external APIs, no OR-Tools.  All computations are based on
haversine distances, vector angles, and timestamp arithmetic.
"""

import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.engine.distance import haversine


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pickup Distance Score
# ─────────────────────────────────────────────────────────────────────────────

def pickup_distance_score(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
    max_radius_km: float = 5.0,
) -> Tuple[float, float]:
    """
    Score based on haversine distance between two pickup locations.

    Closer pickups → higher score.
    Returns (score, distance_km).
    """
    dist_km = haversine(lat1, lng1, lat2, lng2)
    if dist_km >= max_radius_km:
        score = 0.0
    else:
        # Linear decay: 0 km → 1.0,  max_radius_km → 0.0
        score = max(0.0, 1.0 - (dist_km / max_radius_km))
    return round(score, 4), round(dist_km * 1000, 1)  # (score, distance_m)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Destination Similarity Score
# ─────────────────────────────────────────────────────────────────────────────

def destination_similarity_score(
    pickup1_lat: float, pickup1_lng: float, drop1_lat: float, drop1_lng: float,
    pickup2_lat: float, pickup2_lng: float, drop2_lat: float, drop2_lng: float,
) -> float:
    """
    Cosine similarity between the two trip direction vectors.

    Trips heading in the same direction score close to 1.0;
    opposite directions score close to 0.0.
    """
    v1 = (drop1_lat - pickup1_lat, drop1_lng - pickup1_lng)
    v2 = (drop2_lat - pickup2_lat, drop2_lng - pickup2_lng)

    dot = v1[0] * v2[0] + v1[1] * v2[1]
    mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
    mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

    if mag1 < 1e-9 or mag2 < 1e-9:
        return 0.5  # undefined direction → neutral

    cosine = dot / (mag1 * mag2)
    # cosine ∈ [-1, 1] → map to [0, 1]
    return round((cosine + 1.0) / 2.0, 4)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Route Overlap Score
# ─────────────────────────────────────────────────────────────────────────────

def route_overlap_score(
    pickup1_lat: float, pickup1_lng: float, drop1_lat: float, drop1_lng: float,
    pickup2_lat: float, pickup2_lng: float, drop2_lat: float, drop2_lng: float,
) -> Tuple[float, str]:
    """
    Estimates what fraction of the combined trip is shared route.

    Strategy (no routing engine), average of three complementary proxies:
      - shared-pickup proxy: 1 - pickup_gap / avg_trip_length
          Identical/nearby pickups share the entire pickup leg — the
          detour to the second pickup is the pickup gap itself.
      - shared-drop proxy:   1 - drop_gap / avg_trip_length
          Nearby drops share the final delivery leg.
      - midpoint proxy:      1 - mid_gap / avg_trip_length
          Close mid-points indicate the bulk of both trips is the same
          corridor (the historical heuristic).

    Averaging the pickup/drop endpoint proxies with the midpoint proxy
    fixes the degenerate case where two trips share an exact pickup but
    head in different directions: the midpoint gap alone would report
    ~zero overlap even though the pickup leg is 100% shared.

    Returns (score, label) where label ∈ {"High", "Medium", "Low"}.
    """
    mid1_lat = (pickup1_lat + drop1_lat) / 2
    mid1_lng = (pickup1_lng + drop1_lng) / 2
    mid2_lat = (pickup2_lat + drop2_lat) / 2
    mid2_lng = (pickup2_lng + drop2_lng) / 2

    mid_dist_km = haversine(mid1_lat, mid1_lng, mid2_lat, mid2_lng)
    pickup_gap_km = haversine(pickup1_lat, pickup1_lng, pickup2_lat, pickup2_lng)
    drop_gap_km = haversine(drop1_lat, drop1_lng, drop2_lat, drop2_lng)
    trip1_len = haversine(pickup1_lat, pickup1_lng, drop1_lat, drop1_lng)
    trip2_len = haversine(pickup2_lat, pickup2_lng, drop2_lat, drop2_lng)
    avg_len = (trip1_len + trip2_len) / 2.0 if (trip1_len + trip2_len) > 0 else 1.0

    # Each proxy: smaller gap relative to trip length → more overlap
    mid_score = max(0.0, 1.0 - mid_dist_km / max(avg_len, 0.1))
    pickup_score = max(0.0, 1.0 - pickup_gap_km / max(avg_len, 0.1))
    drop_score = max(0.0, 1.0 - drop_gap_km / max(avg_len, 0.1))
    score = (mid_score + pickup_score + drop_score) / 3.0

    if score >= 0.7:
        label = "High"
    elif score >= 0.4:
        label = "Medium"
    else:
        label = "Low"

    return round(score, 4), label


# ─────────────────────────────────────────────────────────────────────────────
# 4. Time Window Compatibility Score
# ─────────────────────────────────────────────────────────────────────────────

def time_window_score(
    ts1: datetime,
    ts2: datetime,
    max_delay_min: float = 20.0,
) -> Tuple[float, float]:
    """
    Score based on time difference between two request timestamps.

    Requests within the same time window score 1.0;
    those beyond max_delay_min score 0.0.
    Returns (score, time_diff_minutes).
    """
    if ts1.tzinfo is None:
        ts1 = ts1.replace(tzinfo=timezone.utc)
    if ts2.tzinfo is None:
        ts2 = ts2.replace(tzinfo=timezone.utc)

    diff_min = abs((ts1 - ts2).total_seconds()) / 60.0
    if diff_min >= max_delay_min:
        score = 0.0
    else:
        score = max(0.0, 1.0 - (diff_min / max_delay_min))
    return round(score, 4), round(diff_min, 1)


def request_times_within_window(
    ts1: Optional[datetime],
    ts2: Optional[datetime],
    max_delay_min: float = 20.0,
) -> bool:
    """
    Cheap time-window gate shared by the batch generator and the adaptive
    compatibility matrix.  Unknown timestamps never block batching.
    """
    if ts1 is None or ts2 is None:
        return True
    if ts1.tzinfo is None:
        ts1 = ts1.replace(tzinfo=timezone.utc)
    if ts2.tzinfo is None:
        ts2 = ts2.replace(tzinfo=timezone.utc)
    return abs((ts1 - ts2).total_seconds()) / 60.0 <= max_delay_min


# ─────────────────────────────────────────────────────────────────────────────
# 5. Vehicle Capacity Score
# ─────────────────────────────────────────────────────────────────────────────

def vehicle_capacity_score(
    total_demand: int,
    total_weight_kg: float,
    max_capacity: int = 6,
    max_weight_kg: float = 100.0,
) -> Tuple[float, str]:
    """
    Score based on whether the combined requests fit in a single vehicle.

    Returns (score, capacity_note).
    """
    demand_ratio = total_demand / max(max_capacity, 1)
    weight_ratio = total_weight_kg / max(max_weight_kg, 1.0)
    combined_ratio = max(demand_ratio, weight_ratio)

    if combined_ratio <= 0.5:
        score = 1.0
        note = "Capacity ample (<=50% utilised)"
    elif combined_ratio <= 0.8:
        score = 0.7
        note = "Capacity sufficient (<=80% utilised)"
    elif combined_ratio <= 1.0:
        score = 0.3
        note = "Capacity near limit"
    else:
        score = 0.0
        note = "Capacity exceeded"

    return round(score, 4), note


# ─────────────────────────────────────────────────────────────────────────────
# 6. Priority Score
# ─────────────────────────────────────────────────────────────────────────────

PRIORITY_VALUES = {"Low": 0.2, "Medium": 0.6, "High": 1.0}


def priority_score(priorities: List[str]) -> Tuple[float, str]:
    """
    Weighted average priority across all requests in the candidate group.

    Higher average priority → higher score (the batch is worth doing urgently).
    Returns (score, dominant_priority_label).
    """
    if not priorities:
        return 0.5, "Unknown"

    values = [PRIORITY_VALUES.get(p, 0.5) for p in priorities]
    avg = sum(values) / len(values)

    if avg >= 0.8:
        label = "High"
    elif avg >= 0.5:
        label = "Medium"
    else:
        label = "Low"

    return round(avg, 4), label


# ─────────────────────────────────────────────────────────────────────────────
# 7. Estimated Delay Score
# ─────────────────────────────────────────────────────────────────────────────

def estimated_delay_score(
    pickup1_lat: float, pickup1_lng: float,
    pickup2_lat: float, pickup2_lng: float,
    max_delay_min: float = 20.0,
    avg_speed_kmh: float = 30.0,
) -> Tuple[float, float]:
    """
    Estimates the additional delay caused by detouring to the second pickup.

    delay_min = (pickup_distance_km / avg_speed_kmh) × 60
    Returns (score, delay_minutes).
    """
    detour_km = haversine(pickup1_lat, pickup1_lng, pickup2_lat, pickup2_lng)
    delay_min = (detour_km / avg_speed_kmh) * 60.0

    if delay_min >= max_delay_min:
        score = 0.0
    else:
        score = max(0.0, 1.0 - (delay_min / max_delay_min))

    return round(score, 4), round(delay_min, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Fuel & CO2 Scores (Continuous Penalties)
# ─────────────────────────────────────────────────────────────────────────────

def fuel_score(
    estimated_fuel_l: float,
    max_acceptable_fuel_l: float = 10.0,
) -> Tuple[float, float]:
    """
    Score based on estimated fuel consumption.

    0 fuel → 1.0; max_acceptable_fuel_l or more → 0.0
    Returns (score, fuel_l).
    """
    if estimated_fuel_l <= 0:
        return 1.0, 0.0
    if estimated_fuel_l >= max_acceptable_fuel_l:
        return 0.0, estimated_fuel_l
    score = 1.0 - (estimated_fuel_l / max_acceptable_fuel_l)
    return round(score, 4), round(estimated_fuel_l, 2)


def co2_score(
    estimated_co2_kg: float,
    max_acceptable_co2_kg: float = 25.0,
) -> Tuple[float, float]:
    """
    Score based on estimated CO2 emissions.

    0 CO2 → 1.0; max_acceptable_co2_kg or more → 0.0
    Returns (score, co2_kg).
    """
    if estimated_co2_kg <= 0:
        return 1.0, 0.0
    if estimated_co2_kg >= max_acceptable_co2_kg:
        return 0.0, estimated_co2_kg
    score = 1.0 - (estimated_co2_kg / max_acceptable_co2_kg)
    return round(score, 4), round(estimated_co2_kg, 2)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Cost Score
# ─────────────────────────────────────────────────────────────────────────────

def cost_score(
    estimated_cost: float,
    max_acceptable_cost: float = 50.0,
) -> Tuple[float, float]:
    """
    Score based on estimated operating cost.

    0 cost → 1.0; max_acceptable_cost or more → 0.0
    Returns (score, cost).
    """
    if estimated_cost <= 0:
        return 1.0, 0.0
    if estimated_cost >= max_acceptable_cost:
        return 0.0, estimated_cost
    score = 1.0 - (estimated_cost / max_acceptable_cost)
    return round(score, 4), round(estimated_cost, 2)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Direct Delay Penalty Score
# ─────────────────────────────────────────────────────────────────────────────

def delay_penalty_score(
    delay_min: float,
    max_delay_min: float = 20.0,
) -> Tuple[float, float]:
    """
    Score based on a directly provided delay in minutes.

    0 delay → 1.0; max_delay_min or more → 0.0
    Returns (score, delay_min).
    """
    if delay_min <= 0:
        return 1.0, 0.0
    if delay_min >= max_delay_min:
        return 0.0, delay_min
    score = 1.0 - (delay_min / max_delay_min)
    return round(score, 4), round(delay_min, 1)
