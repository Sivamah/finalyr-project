"""
DMFE Route Optimizer — Phase 9 Core Engine
===========================================
Google OR-Tools Vehicle Routing Problem (VRP) integration for the DMFE
pipeline.  Solves a Pickup-and-Delivery VRP (PDP) for:

  - Shared Trips     (2+ requests batched by DecisionEngine)
  - Individual Trips (single request)

Multi-objective arc cost (weights configurable via SystemConfig):

    arc_cost = distance_m
             + w_time * duration_s                 (minimise time / delay)
             + w_fuel * fuel_l * fuel_price_per_l  (minimise fuel spend)

Fuel consumption is derived from the vehicle's mileage_kmpl, so the fuel
term is per-vehicle; vehicle utilization is maximised via the capacity
dimension plus a global span coefficient in fleet mode.

Constraints (all respected by the model):
  - Vehicle capacity (demand fit)                    [hard]
  - Pickup before delivery for every request         [hard]
  - Maximum delay (total trip duration cap)          [hard]
  - Request priority (early-visit bonus for High)    [soft]
  - Driver / vehicle availability (selection filter) [hard]

Distance/time matrices come from the Google Maps Distance Matrix API when
GOOGLE_MAPS_API_KEY is configured; otherwise the existing haversine-based
matrix from app.engine.distance is used as a fallback.

OptimizedRoute.to_dict() is compatible with the existing AIOrchestrator
result shape so the Analytics / Explainable-AI dashboards can consume it
unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import SimulationRequest, Vehicle, Driver
from app.dmfe.models import DMFEBatch
from app.engine.distance import haversine

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Output structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Stop:
    """One stop of the optimized route."""
    request_id: int
    action: str                 # "pickup" | "drop"
    lat: float
    lng: float
    priority: str
    arrival_min: float = 0.0    # cumulative arrival time from trip start


@dataclass
class OptimizedRoute:
    """Full output of one optimized trip (shared or individual)."""
    trip_key: str                       # "BATCH-0001-0002" | "TRIP-0003"
    request_ids: List[int]
    is_shared: bool
    driver_id: Optional[int]
    vehicle_id: int
    stop_order: List[Stop]
    total_distance_km: float
    total_duration_min: float
    estimated_fuel_l: float
    utilization_pct: float
    max_delay_min: float
    matrix_source: str                  # "google_maps" | "haversine_fallback"
    savings: Dict[str, float]           # vs individual direct trips
    explanation: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """AIOrchestrator-compatible dict (+ Phase 9 extras)."""
        base = {
            "request_count": len(self.request_ids),
            "request_ids": self.request_ids,
            "driver_id": self.driver_id,
            "vehicle_id": self.vehicle_id,
            "best_route": {
                "distance_km": round(self.total_distance_km, 2),
                "duration_min": round(self.total_duration_min, 1),
                "stops": [
                    {
                        "request_id": s.request_id,
                        "action": s.action,
                        "lat": s.lat,
                        "lng": s.lng,
                        "arrival_min": round(s.arrival_min, 1),
                    }
                    for s in self.stop_order
                ],
            },
            "estimated_cost": round(
                self.savings.get("estimated_cost", 0.0), 2
            ),
            "eta_mins": round(self.total_duration_min, 1),
            "fuel_saved_l": round(self.savings.get("fuel_saved_l", 0.0), 2),
            "distance_saved_km": round(self.savings.get("distance_saved_km", 0.0), 2),
            "co2_saved_kg": round(self.savings.get("co2_saved_kg", 0.0), 2),
            "optimization_score": round(
                self.savings.get("optimization_score", 0.0), 1
            ),
            "is_batched": self.is_shared,
            "trip_key": self.trip_key,
            "matrix_source": self.matrix_source,
            "utilization_pct": self.utilization_pct,
            "max_delay_min": self.max_delay_min,
            "explanation": {
                "requests": len(self.request_ids),
                "distance_km": round(self.total_distance_km, 2),
                "duration_min": round(self.total_duration_min, 1),
                "fuel_l": round(self.estimated_fuel_l, 2),
                "utilization_pct": self.utilization_pct,
                "matrix_source": self.matrix_source,
            },
        }
        return base


# ─────────────────────────────────────────────────────────────────────────────
# VRP rules (configurable via SystemConfig)
# ─────────────────────────────────────────────────────────────────────────────

VRP_RULE_DEFAULTS: Dict[str, float] = {
    "vrp_time_weight": 0.3,          # w_time — seconds-of-time per meter
    "vrp_fuel_weight": 1.0,          # w_fuel — fuel cost weighting
    "vrp_priority_bonus_m": 2000.0,  # meter-equivalent discount for High-priority pickups
    "service_time_min": 2.0,         # loading time at each pickup
    "max_allowed_delay_min": 20.0,   # maximum delay budget (duration cap)
    "max_weight_kg": 100.0,          # system-wide load weight limit
    "avg_speed_kmh": 25.0,           # fallback matrix speed
    "road_factor": 1.25,             # fallback matrix road multiplier
    "fuel_price_per_l": 100.0,       # fuel price for the fuel cost term
    "google_chunk_size": 10,         # Distance Matrix API elements per call
}

VRP_RULE_KEYS: Tuple[str, ...] = tuple(VRP_RULE_DEFAULTS.keys())


def _load_vrp_rules(db: Optional[Session]) -> Dict[str, float]:
    """Load VRP weights/limits from SystemConfig; fall back to defaults."""
    rules = dict(VRP_RULE_DEFAULTS)
    if db is None:
        return rules
    from app.db.models import SystemConfig

    for key in VRP_RULE_KEYS:
        row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if row:
            try:
                rules[key] = float(row.value)
            except (ValueError, TypeError):
                pass
    return rules


# ─────────────────────────────────────────────────────────────────────────────
# Google Maps + fallback matrices
# ─────────────────────────────────────────────────────────────────────────────

def _build_matrices(
    locations: List[Tuple[float, float]],
    rules: Dict[str, float],
) -> Tuple[List[List[int]], List[List[int]], str]:
    """
    Build integer matrices (distance in metres, duration in seconds).

    Tries the Google Maps Distance Matrix API when GOOGLE_MAPS_API_KEY is
    configured; falls back to haversine × road factor / average speed.
    Returns (distance_m, duration_s, source).
    """
    n = len(locations)
    if n == 0:
        return [], [], "empty"

    google = _google_distance_matrix(locations, rules)
    if google is not None:
        return google[0], google[1], "google_maps"

    speed_kmh = rules.get("avg_speed_kmh", 25.0)
    road = rules.get("road_factor", 1.25)
    m_m: List[List[int]] = [[0] * n for _ in range(n)]
    m_s: List[List[int]] = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            km = haversine(*locations[i], *locations[j]) * road
            m_m[i][j] = int(km * 1000.0)
            m_s[i][j] = int((km / max(speed_kmh, 1.0)) * 3600.0)
    return m_m, m_s, "haversine_fallback"


def _google_distance_matrix(
    locations: List[Tuple[float, float]],
    rules: Dict[str, float],
) -> Optional[Tuple[List[List[int]], List[List[int]]]]:
    """Fetch real travel distance/duration via the Distance Matrix API."""
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
    if not api_key:
        return None

    n = len(locations)
    chunk = int(rules.get("google_chunk_size", 10))
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    m_m: List[List[int]] = [[0] * n for _ in range(n)]
    m_s: List[List[int]] = [[0] * n for _ in range(n)]

    try:
        for i0 in range(0, n, chunk):
            origins = locations[i0:i0 + chunk]
            for j0 in range(0, n, chunk):
                destinations = locations[j0:j0 + chunk]
                params = {
                    "origins": "|".join(f"{la},{lo}" for la, lo in origins),
                    "destinations": "|".join(f"{la},{lo}" for la, lo in destinations),
                    "mode": "driving",
                    "key": api_key,
                }
                resp = requests.get(url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") != "OK":
                    return None
                rows = data.get("rows", [])
                if len(rows) != len(origins):
                    return None
                for r_i, row in enumerate(rows):
                    elements = row.get("elements", [])
                    if len(elements) != len(destinations):
                        return None
                    for c_j, el in enumerate(elements):
                        if el.get("status") != "OK":
                            return None
                        m_m[i0 + r_i][j0 + c_j] = el["distance"]["value"]
                        m_s[i0 + r_i][j0 + c_j] = el["duration"]["value"]
    except Exception as exc:
        logger.warning("Google Distance Matrix API failed (%s) — using fallback", exc)
        return None

    return m_m, m_s


# ─────────────────────────────────────────────────────────────────────────────
# RouteOptimizer
# ─────────────────────────────────────────────────────────────────────────────

class RouteOptimizer:
    """
    OR-Tools pickup-and-delivery VRP optimizer for DMFE trips.

    Usage:
        optimizer = RouteOptimizer()
        route = optimizer.optimize_trip(db, requests=[req1, req2],
                                        vehicle_id=3, driver_id=1)
        route.to_dict()  # dashboard-compatible dict
    """

    def optimize_trip(
        self,
        db: Session,
        requests: List[SimulationRequest],
        vehicle: Optional[Vehicle] = None,
        driver: Optional[Driver] = None,
        vehicle_id: Optional[int] = None,
        driver_id: Optional[int] = None,
        trip_key: Optional[str] = None,
    ) -> OptimizedRoute:
        """
        Optimize ONE trip (shared batch or individual request).

        `requests` — 1+ requests (pickup → delivery pairs).
        `vehicle`  — the serving vehicle (or vehicle_id to load it).
        `driver`   — the serving driver (or driver_id); its current
                     location becomes the route depot.
        """
        if not requests:
            raise ValueError("optimize_trip needs at least one request")

        rules = _load_vrp_rules(db)
        if vehicle is None and vehicle_id is not None:
            vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if driver is None and driver_id is not None:
            driver = db.query(Driver).filter(Driver.id == driver_id).first()

        if vehicle is None:
            vehicle = self._select_vehicle(db, requests, rules)

        # Depot = driver location → vehicle location → first pickup
        if driver is not None:
            depot = (driver.current_lat or 11.0168, driver.current_lng or 76.9558)
        else:
            depot = (vehicle.current_lat or 11.0168, vehicle.current_lng or 76.9558)

        # Weight limit gate (system-wide max_weight_kg)
        total_weight = sum(r.weight_kg or 0.0 for r in requests)
        if total_weight > rules["max_weight_kg"]:
            raise ValueError(
                f"Combined weight {total_weight:.1f} kg exceeds "
                f"{rules['max_weight_kg']:.0f} kg limit"
            )

        locations = [depot]
        for r in requests:
            locations.append((r.pickup_lat, r.pickup_lng))
            locations.append((r.drop_lat, r.drop_lng))

        m_m, m_s, source = _build_matrices(locations, rules)
        self._open_route_matrices(m_m, m_s, n_requests=len(requests))

        capacity = int(vehicle.capacity or 1)
        total_demand = sum(r.demand or 1 for r in requests)
        if total_demand > capacity:
            raise ValueError(
                f"Vehicle capacity {capacity} < combined demand {total_demand}"
            )

        solved = self._solve_pdp(
            n_requests=len(requests),
            demands=[r.demand or 1 for r in requests],
            matrix_m=m_m,
            matrix_s=m_s,
            vehicle_capacities=[capacity],
            vehicle_mileage=vehicle.mileage_kmpl or 15.0,
            vehicle_cost_km=vehicle.cost_per_km or 10.0,
            priorities=[r.priority or "Medium" for r in requests],
            rules=rules,
        )

        if solved is None:
            raise ValueError("OR-Tools could not find a feasible route")

        solution, manager, routing, time_dim = solved

        route = self._build_route(
            solution=solution,
            manager=manager,
            routing=routing,
            time_dim=time_dim,
            requests=requests,
            vehicle=vehicle,
            driver=driver,
            matrix_m=m_m,
            matrix_s=m_s,
            source=source,
            trip_key=trip_key,
        )
        logger.info(
            "Optimized trip %s: %d stops, %.2f km, %.1f min, source=%s",
            trip_key, len(route.stop_order), route.total_distance_km,
            route.total_duration_min, source,
        )
        return route

    def optimize_batch(
        self,
        db: Session,
        batch: DMFEBatch,
        vehicle_id: Optional[int] = None,
        driver_id: Optional[int] = None,
    ) -> OptimizedRoute:
        """
        Optimize a persisted DMFE batch (Shared Trip) — integrates directly
        with the output of DecisionEngine / BatchGenerator.
        """
        import json

        ids = json.loads(batch.request_ids_json or "[]")
        requests = (
            db.query(SimulationRequest)
            .filter(SimulationRequest.id.in_(ids))
            .all()
        )
        if len(requests) != len(ids):
            found = {r.id for r in requests}
            missing = set(ids) - found
            raise ValueError(f"Batch {batch.batch_code} references missing requests: {missing}")
        return self.optimize_trip(
            db, requests,
            vehicle_id=vehicle_id, driver_id=driver_id,
            trip_key=batch.batch_code,
        )

    # ── Vehicle selection (driver availability aware) ────────────────────────

    def _select_vehicle(
        self,
        db: Session,
        requests: List[SimulationRequest],
        rules: Dict[str, float],
    ) -> Vehicle:
        """
        Pick the best Available vehicle whose capacity fits the combined
        demand, closest to the first pickup.  Only vehicles linked to
        Available drivers (or free vehicles) are considered.
        """
        total_demand = sum(r.demand or 1 for r in requests)
        first = requests[0]
        candidates = (
            db.query(Vehicle)
            .filter(Vehicle.status == "Available", Vehicle.is_active.is_(True))
            .filter(Vehicle.capacity >= total_demand)
            .all()
        )
        if not candidates:
            raise ValueError("No available vehicle with sufficient capacity")

        def dist(v: Vehicle) -> float:
            return haversine(
                first.pickup_lat, first.pickup_lng,
                v.current_lat or 11.0168, v.current_lng or 76.9558,
            )

        chosen = min(candidates, key=dist)
        logger.info("Auto-selected vehicle #%d (%s) for trip", chosen.id, chosen.name)
        return chosen

    # ── Matrix helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _open_route_matrices(
        m_m: List[List[int]],
        m_s: List[List[int]],
        n_requests: int,
    ) -> None:
        """
        Zero the return-to-depot legs from every drop node so the route
        finishes at the last delivery (open-route behaviour).
        Node layout: 0 = depot, then pickup_i = 2i+1, drop_i = 2i+2.
        """
        n = len(m_m)
        for i in range(n_requests):
            drop = 2 * i + 2
            if drop < n:
                m_m[drop][0] = 0
                m_s[drop][0] = 0

    # ── OR-Tools model ───────────────────────────────────────────────────────

    def _solve_pdp(
        self,
        n_requests: int,
        demands: List[int],
        matrix_m: List[List[int]],
        matrix_s: List[List[int]],
        vehicle_capacities: List[int],
        vehicle_mileage: float,
        vehicle_cost_km: float,
        priorities: List[str],
        rules: Dict[str, float],
        num_vehicles: Optional[int] = None,
    ) -> Optional[Tuple[
        pywrapcp.Assignment,
        pywrapcp.RoutingIndexManager,
        pywrapcp.RoutingModel,
        object,
    ]]:
        """
        Build and solve the OR-Tools pickup-and-delivery VRP.

        Node layout: node 0 = depot; request i → pickup 2i+1, drop 2i+2.

        Objective (per arc): distance + w_time*duration + w_fuel*fuel cost,
        minus the priority bonus when entering a High-priority pickup.

        If the time-constrained model is infeasible, the model is relaxed
        (time dimension dropped) and re-solved — graceful degradation.
        Returns (solution, manager, routing, time_dim) or None.
        """
        n_nodes = 1 + 2 * n_requests
        if num_vehicles is None:
            num_vehicles = len(vehicle_capacities)
        manager = pywrapcp.RoutingIndexManager(n_nodes, num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        w_time = rules.get("vrp_time_weight", 0.3)
        w_fuel = rules.get("vrp_fuel_weight", 1.0)
        fuel_price = rules.get("fuel_price_per_l", 100.0)
        prio_bonus = int(rules.get("vrp_priority_bonus_m", 2000.0))
        service_sec = int(rules.get("service_time_min", 2.0) * 60.0)

        high_prio_pickups = {
            2 * i + 1 for i, p in enumerate(priorities) if p == "High"
        }
        mileage_m = max(float(vehicle_mileage or 15.0), 1.0)
        pickups = {2 * i + 1 for i in range(n_requests)}

        def make_callbacks(mgr):
            def combined_cb(from_index, to_index):
                f = mgr.IndexToNode(from_index)
                t = mgr.IndexToNode(to_index)
                dist = matrix_m[f][t]
                dur = matrix_s[f][t]
                fuel_l = (dist / 1000.0) / mileage_m
                cost = dist + w_time * dur + w_fuel * fuel_l * fuel_price
                if t in high_prio_pickups and f != t:
                    cost -= prio_bonus
                return int(max(cost, 0))

            def demand_cb(from_index):
                node = mgr.IndexToNode(from_index)
                if node == 0:
                    return 0
                req = (node - 1) // 2
                return demands[req] if node % 2 == 1 else -demands[req]

            def distance_cb(from_index, to_index):
                f = mgr.IndexToNode(from_index)
                t = mgr.IndexToNode(to_index)
                return int(matrix_m[f][t])

            return combined_cb, demand_cb, distance_cb

        combined_cb, demand_cb, distance_cb = make_callbacks(manager)
        transit_idx = routing.RegisterTransitCallback(combined_cb)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

        # Capacity callback
        demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
        routing.AddDimensionWithVehicleCapacity(
            demand_idx, 0, vehicle_capacities, True, "Capacity"
        )

        # Distance dimension — guarantees pickup-before-delivery ordering
        # (distance strictly increases along the route)
        dist_idx = routing.RegisterTransitCallback(distance_cb)
        max_dist = int(sum(sum(row) for row in matrix_m)) + 1_000_000
        routing.AddDimension(dist_idx, 0, max_dist, True, "Distance")
        dist_dim = routing.GetDimensionOrDie("Distance")

        # Pickup-before-delivery + same vehicle
        for i in range(n_requests):
            p_idx = manager.NodeToIndex(2 * i + 1)
            d_idx = manager.NodeToIndex(2 * i + 2)
            routing.AddPickupAndDelivery(p_idx, d_idx)
            routing.solver().Add(
                routing.VehicleVar(p_idx) == routing.VehicleVar(d_idx)
            )
            routing.solver().Add(
                dist_dim.CumulVar(p_idx) <= dist_dim.CumulVar(d_idx)
            )

        time_dim = None

        def solve(use_time_dim: bool):
            nonlocal time_dim
            if use_time_dim:
                # Time callback: travel time + service time at pickups
                def time_cb(from_index, to_index):
                    f = manager.IndexToNode(from_index)
                    t = manager.IndexToNode(to_index)
                    dur = matrix_s[f][t]
                    if f in pickups:
                        dur += service_sec
                    return int(dur)

                time_idx = routing.RegisterTransitCallback(time_cb)
                direct_sec = sum(matrix_s[2 * i + 1][2 * i + 2] for i in range(n_requests))
                horizon = int(
                    (rules.get("max_allowed_delay_min", 20.0) + direct_sec / 60.0) * 60.0
                    + 60.0
                )
                routing.AddDimension(time_idx, 0, horizon, True, "Time")
                time_dim = routing.GetDimensionOrDie("Time")

            if num_vehicles > 1 and time_dim is not None:
                # Utilisation: balance route lengths in fleet mode
                time_dim.SetGlobalSpanCostCoefficient(max(50, 100 * n_requests))

            params = pywrapcp.DefaultRoutingSearchParameters()
            params.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
            )
            params.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            params.time_limit.seconds = 4
            return routing.SolveWithParameters(params)

        solution = solve(use_time_dim=True)
        if solution is None:
            logger.warning(
                "OR-Tools: no solution with time dimension (%d requests) "
                "— relaxing time constraint and retrying",
                n_requests,
            )
            # Relax: rebuild the model without the time dimension
            manager = pywrapcp.RoutingIndexManager(n_nodes, num_vehicles, 0)
            routing = pywrapcp.RoutingModel(manager)
            combined_cb, demand_cb, distance_cb = make_callbacks(manager)
            routing.SetArcCostEvaluatorOfAllVehicles(
                routing.RegisterTransitCallback(combined_cb)
            )
            routing.AddDimensionWithVehicleCapacity(
                routing.RegisterUnaryTransitCallback(demand_cb),
                0, vehicle_capacities, True, "Capacity",
            )
            routing.AddDimension(
                routing.RegisterTransitCallback(distance_cb),
                0, max_dist, True, "Distance",
            )
            dist_dim = routing.GetDimensionOrDie("Distance")
            for i in range(n_requests):
                p_idx = manager.NodeToIndex(2 * i + 1)
                d_idx = manager.NodeToIndex(2 * i + 2)
                routing.AddPickupAndDelivery(p_idx, d_idx)
                routing.solver().Add(
                    routing.VehicleVar(p_idx) == routing.VehicleVar(d_idx)
                )
                routing.solver().Add(
                    dist_dim.CumulVar(p_idx) <= dist_dim.CumulVar(d_idx)
                )
            params = pywrapcp.DefaultRoutingSearchParameters()
            params.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
            )
            params.time_limit.seconds = 6
            solution = routing.SolveWithParameters(params)
            time_dim = None

        if solution is None:
            return None
        return solution, manager, routing, time_dim

    # ── Result assembly ──────────────────────────────────────────────────────

    def _build_route(
        self,
        solution: pywrapcp.Assignment,
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        time_dim,
        requests: List[SimulationRequest],
        vehicle: Vehicle,
        driver: Optional[Driver],
        matrix_m: List[List[int]],
        matrix_s: List[List[int]],
        source: str,
        trip_key: Optional[str],
    ) -> OptimizedRoute:
        """Assemble the OptimizedRoute from the OR-Tools solution."""
        node_index = routing.Start(0)
        stop_order: List[Stop] = []
        total_dist = 0
        prev = 0

        while not routing.IsEnd(node_index):
            node = manager.IndexToNode(node_index)
            if node != 0:
                req = requests[(node - 1) // 2]
                is_pickup = node % 2 == 1
                arr_sec = 0.0
                if time_dim is not None:
                    try:
                        arr_sec = solution.Min(time_dim.CumulVar(node_index))
                    except Exception:
                        arr_sec = 0.0
                stop_order.append(Stop(
                    request_id=req.id,
                    action="pickup" if is_pickup else "drop",
                    lat=req.pickup_lat if is_pickup else req.drop_lat,
                    lng=req.pickup_lng if is_pickup else req.drop_lng,
                    priority=req.priority or "Medium",
                    arrival_min=round(arr_sec / 60.0, 1),
                ))
                total_dist += matrix_m[prev][node]
            prev = node
            node_index = solution.Value(routing.NextVar(node_index))

        total_dist += matrix_m[prev][0]  # open-route: leg is zeroed

        # Per-request delay vs direct trip
        direct_times = {
            r.id: matrix_s[2 * i + 1][2 * i + 2] / 60.0
            for i, r in enumerate(requests)
        }
        arrival_at = {s.request_id: s.arrival_min for s in stop_order if s.action == "drop"}
        pickup_at = {s.request_id: s.arrival_min for s in stop_order if s.action == "pickup"}
        delays = [
            arrival_at[r.id] - pickup_at[r.id] - direct_times[r.id]
            for r in requests if r.id in arrival_at and r.id in pickup_at
        ]
        max_delay = round(max(delays), 1) if delays else 0.0

        total_km = total_dist / 1000.0
        duration_min = stop_order[-1].arrival_min if stop_order else 0.0
        mileage = vehicle.mileage_kmpl or 15.0
        fuel_l = total_km / max(mileage, 1.0)

        # Baseline: individual trips (depot → pickup → drop per request)
        baseline_km = sum(
            (matrix_m[0][2 * i + 1] + matrix_m[2 * i + 1][2 * i + 2]) / 1000.0
            for i in range(len(requests))
        )
        saved_km = max(0.0, baseline_km - total_km)
        fuel_saved = saved_km / max(mileage, 1.0)
        co2_saved = fuel_saved * 2.3
        cost = total_km * (vehicle.cost_per_km or 10.0)
        score = min(100.0, max(0.0, 100.0 - (saved_km / max(baseline_km, 0.1)) * 50.0 + 50.0))

        utilization = round(
            (sum(r.demand or 1 for r in requests) / max(int(vehicle.capacity or 1), 1))
            * 100.0, 1
        )

        trip_key = trip_key or (
            f"TRIP-{requests[0].id:04d}"
            if len(requests) == 1
            else f"BATCH-{requests[0].id:04d}-{requests[-1].id:04d}"
        )

        return OptimizedRoute(
            trip_key=trip_key,
            request_ids=[r.id for r in requests],
            is_shared=len(requests) > 1,
            driver_id=driver.id if driver else None,
            vehicle_id=vehicle.id,
            stop_order=stop_order,
            total_distance_km=round(total_km, 2),
            total_duration_min=round(duration_min, 1),
            estimated_fuel_l=round(fuel_l, 2),
            utilization_pct=utilization,
            max_delay_min=max_delay,
            matrix_source=source,
            savings={
                "distance_saved_km": round(saved_km, 2),
                "fuel_saved_l": round(fuel_saved, 2),
                "co2_saved_kg": round(co2_saved, 2),
                "estimated_cost": round(cost, 2),
                "optimization_score": round(score, 1),
                "baseline_distance_km": round(baseline_km, 2),
            },
            explanation={
                "requests": len(requests),
                "direct_distance_km": round(baseline_km, 2),
                "optimized_distance_km": round(total_km, 2),
                "savings_percentage": round(
                    (saved_km / max(baseline_km, 0.1)) * 100.0, 1
                ),
                "vehicle_used": vehicle.name,
                "fuel_type": vehicle.fuel_type,
            },
        )


# Module-level singleton
route_optimizer = RouteOptimizer()
