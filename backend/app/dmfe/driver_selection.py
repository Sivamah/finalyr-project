"""
DMFE Driver Selection & Assignment Engine — Phase 9 Core Engine
================================================================
Selects the best available driver for a trip (Shared or Individual)
and persists the Trip + DriverAssignment records that close the DMFE
pipeline:

    Incoming Requests → Compatibility → Batching → Decision
    → Route Optimizer → Driver Selection → Trip Assignment

Selection factors (configurable weights via SystemConfig):

  - Driver availability          (status == "Available", hard filter)
  - Current workload             (no other active trip/assignment, hard)
  - Current location proximity   (proximity_score from ETA to trip anchor)
  - Estimated arrival time ETA   (haversine / avg speed, reported in min)
  - Vehicle capacity             (demand & weight fit, hard filter)
  - Vehicle type                 (type match with request preference)

The engine integrates with:

  - decision_engine.py  — receives feasible CandidateGroups
  - optimizer.py        — receives the selected (driver, vehicle) pair so
                          the OR-Tools route starts from the driver depot
  - compatibility.py    — selection happens after compatibility evaluation

AssignmentEngine updates the database atomically (single commit):

  - creates Trip + DriverAssignment + DriverAssignmentHistory rows
  - marks driver/vehicle Busy, requests Assigned, batch Dispatched
  - prevents a driver from being assigned two active trips
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.json_utils import json_loads
from app.db.models import (
    Driver,
    DriverAssignment,
    DriverAssignmentHistory,
    SimulationRequest,
    Trip,
    Vehicle,
)
from app.dmfe.compatibility import (
    _cached,
    read_float_rules,
    resolve_mode,
)
from app.dmfe.models import DMFEBatch
from app.dmfe.optimizer import OptimizedRoute, _cached_vrp_rules, route_optimizer
from app.engine.distance import haversine

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Selection rules (configurable via SystemConfig, never overwritten)
# ─────────────────────────────────────────────────────────────────────────────

SELECTOR_RULE_DEFAULTS: Dict[str, float] = {
    "driver_proximity_weight": 0.50,   # w_prox — how close the driver is
    "driver_type_weight": 0.30,        # w_type — vehicle-type match
    "driver_workload_weight": 0.20,    # w_work — workload fairness
    "driver_fairness_weight": 0.10,    # w_fair — rotation among under-used drivers
    "driver_history_weight": 0.15,     # w_hist — historical completion rate
    "driver_eta_limit_min": 30.0,      # ETA ceiling for a full proximity score
    "driver_max_search_km": 25.0,      # search radius around the trip anchor
    "driver_avg_speed_kmh": 25.0,      # ETA fallback speed
    "driver_workload_cap": 6.0,        # recent (24 h) assignments = full workload
    "driver_fairness_cap": 30.0,       # lifetime assignments = full rotation need
    "driver_learning_weight": 0.10,    # adaptive-mode learning influence on w_prox
}


def _load_selector_rules(db: Optional[Session]) -> Dict[str, float]:
    """Load driver-selection weights from SystemConfig; fall back to defaults."""
    return read_float_rules(db, SELECTOR_RULE_DEFAULTS)


def _cached_selector_rules(db: Optional[Session]) -> Dict[str, float]:
    """TTL-cached _load_selector_rules (shared SystemConfig cache)."""
    return _cached(db, "selector_rules", _load_selector_rules)


# ─────────────────────────────────────────────────────────────────────────────
# Candidate model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DriverCandidate:
    """A scored (driver, vehicle) pairing for one trip."""
    driver: Driver
    vehicle: Vehicle
    proximity_score: float      # 0..1 — derived from ETA
    type_score: float           # 0..1 — vehicle type match
    workload_score: float       # 0..1 — recent workload pressure
    fairness_score: float       # 0..1 — lifetime-assignment rotation
    history_score: float        # 0..1 — historical completion rate
    eta_min: float              # estimated arrival at the trip anchor
    total_score: float          # weighted combination
    eta_component_km: float = 0.0     # driver → vehicle distance (km)
    anchor_component_km: float = 0.0  # vehicle → anchor distance (km)
    completion_rate: float = 1.0
    recent_assignments: int = 0
    lifetime_assignments: int = 0
    weights_used: Dict[str, float] = None
    learning_proximity_bump: float = 0.0  # adaptive-only weight boost (0 in static)

    def to_dict(self) -> Dict:
        return {
            "driver_id": self.driver.id,
            "driver_name": self.driver.name,
            "driver_phone": self.driver.phone,
            "driver_status": self.driver.status,
            "vehicle_id": self.vehicle.id,
            "vehicle_name": self.vehicle.name,
            "vehicle_type": self.vehicle.vehicle_type,
            "vehicle_capacity": self.vehicle.capacity,
            "proximity_score": round(self.proximity_score, 3),
            "type_score": round(self.type_score, 3),
            "workload_score": round(self.workload_score, 3),
            "fairness_score": round(self.fairness_score, 3),
            "history_score": round(self.history_score, 3),
            "eta_min": round(self.eta_min, 1),
            "total_score": round(self.total_score, 3),
            "eta_components_km": [
                round(self.eta_component_km, 2),
                round(self.anchor_component_km, 2),
            ],
            "completion_rate": round(self.completion_rate, 3),
            "recent_assignments": self.recent_assignments,
            "lifetime_assignments": self.lifetime_assignments,
            "weights_used": {
                k: round(v, 4) for k, v in (self.weights_used or {}).items()
            },
            "learning_proximity_bump": round(self.learning_proximity_bump, 4),
        }


# ─────────────────────────────────────────────────────────────────────────────
# DriverPool — one grouped-query snapshot shared by every selection probe
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DriverPool:
    """
    Immutable snapshot of every signal the selector needs, fetched with a
    constant number of grouped queries (no N+1):

      - available drivers
      - available active vehicles
      - active trip/assignment counts per driver
      - assignments in the last 24 h per driver (recent workload)
      - lifetime assignment & completion counts per driver (fairness/history)
      - average utilisation of the driver's completed trips

    The pool is built ONCE per analysis run and shared by all candidate
    probes; the dispatch path rebuilds it per select() because driver state
    changes between dispatches.
    """
    drivers: List[Driver]
    vehicles: List[Vehicle]
    total_driver_count: int
    total_vehicle_count: int
    active_counts: Dict[int, int]
    recent_counts: Dict[int, int]
    lifetime_counts: Dict[int, int]
    completed_counts: Dict[int, int]
    avg_utilization: Dict[int, float]

    def fitting_vehicles(self, demand: int) -> List[Vehicle]:
        return [v for v in self.vehicles if (v.capacity or 1) >= demand]


def _corridor_key(requests: List[SimulationRequest]) -> str:
    """Sorted request-type mix, e.g. 'food|ride' (mirrors learning engine)."""
    types = sorted({(r.request_type or "ride").lower() for r in requests})
    return "|".join(types) if types else "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# DriverSelector
# ─────────────────────────────────────────────────────────────────────────────

class DriverSelector:
    """
    Picks the best available (driver, vehicle) pair for a trip.

    Hard filters (no candidate → no dispatch):
      1. Driver status == "Available"
      2. Driver has no other active Trip / assignment
      3. Driver within driver_max_search_km of the trip anchor
      4. An available active vehicle fits demand & weight (capacity gate)
      5. Weight limit (max_weight_kg)

    Soft scoring (normalised 0..1 metrics, weights from SystemConfig):
      total = w_prox·proximity + w_type·type + w_work·workload
              + w_fair·fairness + w_hist·history

      - proximity   ETA-based (honest ETA = driver→vehicle + vehicle→anchor)
      - type        vehicle-type match with the request preference
      - workload    recent (24 h) assignments + historical utilisation
      - fairness    lifetime assignment count (rotation among under-used)
      - history     historical completion rate

    Adaptive mode only: the learned delay bias (outcomes.delay_bias_min ×
    corridor multiplier) raises the proximity weight by up to 0.2 so ETA
    matters more exactly when learning says predictions run low.  Static
    mode never reads the learning state (zero influence).
    """

    def select(
        self,
        db: Session,
        requests: List[SimulationRequest],
        rules: Optional[Dict[str, float]] = None,
        pool: Optional[DriverPool] = None,
    ) -> Optional[DriverCandidate]:
        if not requests:
            return None

        rules = rules or _cached_selector_rules(db)
        vrp = _cached_vrp_rules(db)
        total_demand = sum(r.demand or 1 for r in requests)
        total_weight = sum(r.weight_kg or 0.0 for r in requests)
        if total_weight > vrp.get("max_weight_kg", 100.0):
            logger.info("DriverSelector: combined weight %.1f kg exceeds limit",
                        total_weight)
            return None

        if pool is None:
            pool = self.build_pool(db)
        if not pool.drivers:
            logger.info("DriverSelector: no Available drivers")
            return None

        anchor_lat, anchor_lng = self._trip_anchor(requests)
        max_km = rules.get("driver_max_search_km", 25.0)
        eta_limit = rules.get("driver_eta_limit_min", 30.0)
        speed = rules.get("driver_avg_speed_kmh", 25.0)
        w_prox = rules.get("driver_proximity_weight", 0.5)
        w_type = rules.get("driver_type_weight", 0.3)
        w_work = rules.get("driver_workload_weight", 0.2)
        w_fair = rules.get("driver_fairness_weight", 0.1)
        w_hist = rules.get("driver_history_weight", 0.15)
        work_cap = max(rules.get("driver_workload_cap", 6.0), 1.0)
        fair_cap = max(rules.get("driver_fairness_cap", 30.0), 1.0)

        # A-DMFE learning influence — adaptive mode ONLY (zero in static)
        bump = 0.0
        if resolve_mode(db) == "adaptive":
            bump = self._learned_proximity_bump(db, requests, rules)
        w_prox_eff = w_prox + bump
        weights_used = {
            "proximity": w_prox_eff, "type": w_type, "workload": w_work,
            "fairness": w_fair, "history": w_hist,
        }

        # Vehicle → anchor distances computed once, shared by every driver
        v2a: Dict[int, float] = {
            v.id: haversine(anchor_lat, anchor_lng,
                            v.current_lat or 11.0168, v.current_lng or 76.9558)
            for v in pool.vehicles
        }
        fitting = pool.fitting_vehicles(total_demand)

        best: Optional[DriverCandidate] = None
        for driver in pool.drivers:
            if pool.active_counts.get(driver.id, 0) > 0:
                continue  # never double-book a driver

            eta_km = haversine(
                anchor_lat, anchor_lng,
                driver.current_lat or 11.0168, driver.current_lng or 76.9558,
            )
            if eta_km > max_km:
                continue

            vehicle, veh_km, anchor_km = self._pick_vehicle(
                driver, fitting, v2a, anchor_lat, anchor_lng,
            )
            if vehicle is None:
                continue

            eta_min = ((veh_km + anchor_km) / max(speed, 1.0)) * 60.0
            proximity = max(0.0, 1.0 - eta_min / max(eta_limit, 1.0))
            type_score = self._type_match_score(vehicle, requests)
            workload_score = self._workload_score(driver, pool, work_cap)
            fairness_score = self._fairness_score(driver, pool, fair_cap)
            history_score = self._history_score(driver, pool)
            total = (w_prox_eff * proximity + w_type * type_score
                     + w_work * workload_score + w_fair * fairness_score
                     + w_hist * history_score)

            candidate = DriverCandidate(
                driver=driver, vehicle=vehicle,
                proximity_score=proximity, type_score=type_score,
                workload_score=workload_score, fairness_score=fairness_score,
                history_score=history_score, eta_min=eta_min,
                total_score=total,
                eta_component_km=veh_km, anchor_component_km=anchor_km,
                completion_rate=history_score,
                recent_assignments=pool.recent_counts.get(driver.id, 0),
                lifetime_assignments=pool.lifetime_counts.get(driver.id, 0),
                weights_used=weights_used,
                learning_proximity_bump=bump,
            )
            if best is None or self._better(candidate, best):
                best = candidate

        if best is not None:
            logger.info(
                "DriverSelector: best candidate driver #%d (%s) + vehicle #%d "
                "(%s) score=%.3f eta=%.1f min",
                best.driver.id, best.driver.name, best.vehicle.id,
                best.vehicle.name, best.total_score, best.eta_min,
            )
        else:
            logger.info("DriverSelector: no feasible driver/vehicle for %d requests",
                        len(requests))
        return best

    # ── pool construction (grouped queries — no N+1) ────────────────────────

    def build_pool(self, db: Session) -> DriverPool:
        drivers = (
            db.query(Driver)
            .filter(Driver.status == "Available")
            .order_by(Driver.id.asc())
            .all()
        )
        vehicles = (
            db.query(Vehicle)
            .filter(
                Vehicle.status == "Available",
                Vehicle.is_active.is_(True),
            )
            .all()
        )
        return DriverPool(
            drivers=drivers,
            vehicles=vehicles,
            total_driver_count=(
                db.query(Driver).count()
            ),
            total_vehicle_count=(
                db.query(Vehicle).count()
            ),
            active_counts=self._active_trip_counts(db),
            recent_counts=self._recent_assignment_counts(db, hours=24),
            lifetime_counts=self._lifetime_assignment_counts(db),
            completed_counts=self._completed_assignment_counts(db),
            avg_utilization=self._avg_driver_utilization(db),
        )

    def _recent_assignment_counts(self, db: Session, hours: float) -> Dict[int, int]:
        """Assignments started in the last `hours` per driver (1 grouped query)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        counts: Dict[int, int] = {}
        rows = (
            db.query(DriverAssignmentHistory.driver_id)
            .filter(
                DriverAssignmentHistory.driver_id.isnot(None),
                DriverAssignmentHistory.assignment_time >= cutoff,
            )
            .all()
        )
        for (driver_id,) in rows:
            counts[driver_id] = counts.get(driver_id, 0) + 1
        return counts

    def _lifetime_assignment_counts(self, db: Session) -> Dict[int, int]:
        """All-time assignment count per driver (1 grouped query)."""
        counts: Dict[int, int] = {}
        rows = (
            db.query(DriverAssignmentHistory.driver_id)
            .filter(DriverAssignmentHistory.driver_id.isnot(None))
            .all()
        )
        for (driver_id,) in rows:
            counts[driver_id] = counts.get(driver_id, 0) + 1
        return counts

    def _completed_assignment_counts(self, db: Session) -> Dict[int, int]:
        """All-time Completed assignments per driver (1 grouped query)."""
        counts: Dict[int, int] = {}
        rows = (
            db.query(DriverAssignmentHistory.driver_id)
            .filter(
                DriverAssignmentHistory.driver_id.isnot(None),
                DriverAssignmentHistory.status == "Completed",
            )
            .all()
        )
        for (driver_id,) in rows:
            counts[driver_id] = counts.get(driver_id, 0) + 1
        return counts

    def _avg_driver_utilization(self, db: Session) -> Dict[int, float]:
        """Average utilisation (%) of each driver's completed trips."""
        avg: Dict[int, float] = {}
        rows = (
            db.query(Trip.driver_id, Trip.utilization_pct)
            .filter(
                Trip.driver_id.isnot(None),
                Trip.status == "Completed",
            )
            .all()
        )
        per: Dict[int, List[float]] = {}
        for driver_id, util in rows:
            per.setdefault(driver_id, []).append(util or 0.0)
        for driver_id, utils in per.items():
            avg[driver_id] = sum(utils) / len(utils)
        return avg

    # ── scoring helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _trip_anchor(requests: List[SimulationRequest]) -> Tuple[float, float]:
        """Centroid of the pickups — where the driver must arrive first."""
        n = len(requests)
        lat = sum(r.pickup_lat for r in requests) / n
        lng = sum(r.pickup_lng for r in requests) / n
        return lat, lng

    def _active_trip_counts(self, db: Session) -> Dict[int, int]:
        """Active trip/assignment count per driver, in 2 grouped queries."""
        counts: Dict[int, int] = {}
        trip_rows = (
            db.query(Trip.driver_id)
            .filter(
                Trip.driver_id.isnot(None),
                Trip.status.in_(["Planned", "Active"]),
            )
            .all()
        )
        for (driver_id,) in trip_rows:
            counts[driver_id] = counts.get(driver_id, 0) + 1
        legacy_rows = (
            db.query(DriverAssignmentHistory.driver_id)
            .filter(
                DriverAssignmentHistory.driver_id.isnot(None),
                DriverAssignmentHistory.status == "Active",
            )
            .all()
        )
        for (driver_id,) in legacy_rows:
            counts[driver_id] = counts.get(driver_id, 0) + 1
        return counts

    @staticmethod
    def _learned_proximity_bump(
        db: Session, requests: List[SimulationRequest],
        rules: Dict[str, float],
    ) -> float:
        """
        Adaptive-mode learning influence on the proximity weight (0 in static).

        When the learning state reports that actual delays run above the
        predictions (delay_bias_min > 0), ETA matters more: the proximity
        weight is raised by

            bump = min(delay_bias / 30, 1) · corridor_multiplier · w_learn

        bounded to [0, 0.2].  The corridor multiplier comes from the refitted
        residual model for this request-type mix.  Static mode never calls
        this (the caller gates it on resolve_mode).
        """
        try:
            from app.dmfe.adaptive.learning import LearningEngine

            state = _cached(
                db, "selector_learning_state",
                lambda s: LearningEngine.load_state(s),
            )
            if not LearningEngine.learning_enabled(db):
                return 0.0
            delay_bias = float(state.get("outcomes", {}).get("delay_bias_min", 0.0))
            if delay_bias <= 0.0:
                return 0.0
            corridor = _corridor_key(requests)
            mult = float(state.get("corridor_multipliers", {}).get(corridor, 1.0))
            mult = max(0.5, min(mult, 2.0))
            w_learn = rules.get("driver_learning_weight", 0.10)
            bump = min(delay_bias / 30.0, 1.0) * mult * w_learn
            return min(bump, 0.2)
        except Exception as exc:
            logger.warning("DriverSelector: learning influence skipped: %s", exc)
            return 0.0

    @staticmethod
    def _workload_score(
        driver: Driver, pool: DriverPool, cap: float,
    ) -> float:
        """
        Current workload pressure (0..1): high when the driver has been
        worked recently or has carried high-utilisation trips.
        """
        recent = pool.recent_counts.get(driver.id, 0)
        recent_ok = max(0.0, 1.0 - min(recent / cap, 1.0))
        util = pool.avg_utilization.get(driver.id)
        util_ok = 1.0 if util is None else max(0.0, 1.0 - min(util / 100.0, 1.0))
        return 0.5 * recent_ok + 0.5 * util_ok

    @staticmethod
    def _fairness_score(driver: Driver, pool: DriverPool, cap: float) -> float:
        """
        Rotation score (0..1): drivers with fewer lifetime assignments score
        higher so repeated pick-by-proximity does not starve the others.
        Bounded by its weight (default 0.10), so it can never override a
        material ETA difference (≈ 6 min at the default ETA limit).
        """
        total = pool.lifetime_counts.get(driver.id, 0)
        return max(0.0, 1.0 - min(total / cap, 1.0))

    @staticmethod
    def _history_score(driver: Driver, pool: DriverPool) -> float:
        """Historical completion rate (0..1); no history → neutral 1.0."""
        total = pool.lifetime_counts.get(driver.id, 0)
        if total <= 0:
            return 1.0
        completed = pool.completed_counts.get(driver.id, 0)
        return completed / float(total)

    @staticmethod
    def _pick_vehicle(
        driver: Driver,
        fitting: List[Vehicle],
        v2a: Dict[int, float],
        anchor_lat: float,
        anchor_lng: float,
    ) -> Tuple[Optional[Vehicle], float, float]:
        """
        Choose the vehicle for one driver.

        Preferred: the driver's assigned vehicle (if it fits demand).
        Fallback: the fitting vehicle minimising the honest ETA path
        driver→vehicle + vehicle→anchor (O(D·V) simple float math, no
        repeated distance-matrix work).

        Returns (vehicle, driver→vehicle km, vehicle→anchor km).
        """
        if not fitting:
            return None, 0.0, 0.0

        if driver.assigned_vehicle_id is not None:
            preferred = next(
                (v for v in fitting if v.id == driver.assigned_vehicle_id),
                None,
            )
            if preferred is not None:
                return preferred, 0.0, v2a.get(preferred.id, 0.0)

        dl, dg = driver.current_lat or 11.0168, driver.current_lng or 76.9558
        best_v, best_cost = None, None
        for v in fitting:
            cost = haversine(dl, dg, v.current_lat or 11.0168, v.current_lng or 76.9558)
            cost += v2a.get(v.id, 0.0)
            if best_v is None or cost < best_cost:
                best_v, best_cost = v, cost
        if best_v is None:
            return None, 0.0, 0.0
        return best_v, best_cost - v2a.get(best_v.id, 0.0), v2a.get(best_v.id, 0.0)

    @staticmethod
    def _type_match_score(vehicle: Vehicle, requests: List[SimulationRequest]) -> float:
        """1.0 when the vehicle type matches a request preference, else 0.4."""
        preferred = {
            (r.vehicle_type or "").strip().lower()
            for r in requests
            if r.vehicle_type and (r.vehicle_type or "").strip().lower()
               not in ("any", "all", "any type")
        }
        if not preferred:
            return 1.0  # no explicit preference → any vehicle is acceptable
        vtype = (vehicle.vehicle_type or "").strip().lower()
        return 1.0 if vtype in preferred else 0.4

    @staticmethod
    def _better(a: DriverCandidate, b: DriverCandidate) -> bool:
        """Higher score wins; tie-break on lower ETA, then lower driver id."""
        if abs(a.total_score - b.total_score) > 1e-9:
            return a.total_score > b.total_score
        if abs(a.eta_min - b.eta_min) > 1e-9:
            return a.eta_min < b.eta_min
        return a.driver.id < b.driver.id


# ─────────────────────────────────────────────────────────────────────────────
# AssignmentEngine
# ─────────────────────────────────────────────────────────────────────────────

class AssignmentEngine:
    """
    Persists the final Trip + DriverAssignment for a dispatched route.

    Runs inside a single transaction: if any step fails, nothing is
    partially written (the caller controls commit/rollback).
    """

    def create_assignment(
        self,
        db: Session,
        driver: Driver,
        vehicle: Vehicle,
        route: OptimizedRoute,
        requests: List[SimulationRequest],
        batch: Optional[DMFEBatch] = None,
        assignment_type: str = "AUTO",
        commit: bool = True,
    ) -> Tuple[Trip, DriverAssignment]:
        """
        Create Trip + DriverAssignment (+ history) and update the state of
        driver, vehicle, requests and batch.  Returns the Trip row.
        """
        if driver.status != "Available":
            raise ValueError(
                f"Driver #{driver.id} ({driver.name}) is not Available"
            )

        total_demand = sum(r.demand or 1 for r in requests)
        if total_demand > (vehicle.capacity or 1):
            raise ValueError(
                f"Vehicle #{vehicle.id} capacity {vehicle.capacity} < "
                f"combined demand {total_demand}"
            )

        trip = Trip(
            trip_code=route.trip_key,
            batch_id=batch.id if batch is not None else None,
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            request_ids_json=json.dumps(route.request_ids),
            is_shared=route.is_shared,
            status="Active",
            stop_order_json=json.dumps([
                {
                    "request_id": s.request_id,
                    "action": s.action,
                    "arrival_min": s.arrival_min,
                }
                for s in route.stop_order
            ]),
            total_distance_km=route.total_distance_km,
            total_duration_min=route.total_duration_min,
            eta_min=route.total_duration_min,
            fuel_l=route.estimated_fuel_l,
            utilization_pct=route.utilization_pct,
            max_delay_min=route.max_delay_min,
            matrix_source=route.matrix_source,
            estimated_cost=route.savings.get("estimated_cost", 0.0),
            distance_saved_km=route.savings.get("distance_saved_km", 0.0),
            fuel_saved_l=route.savings.get("fuel_saved_l", 0.0),
            co2_saved_kg=route.savings.get("co2_saved_kg", 0.0),
            optimization_score=route.savings.get("optimization_score", 0.0),
        )
        db.add(trip)
        db.flush()

        assignment = DriverAssignment(
            trip_id=trip.id,
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            driver_name=driver.name,
            vehicle_name=vehicle.name,
            assignment_type=assignment_type,
            status="Active",
        )
        db.add(assignment)
        db.add(DriverAssignmentHistory(
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            driver_name=driver.name,
            vehicle_name=vehicle.name,
            status="Active",
        ))

        # State transitions
        driver.status = "Busy"
        vehicle.status = "Busy"
        for r in requests:
            r.status = "Assigned"
        if batch is not None:
            batch.status = "Dispatched"

        if commit:
            db.commit()
            
        logger.info(
            "AssignmentEngine: trip %s (driver #%d, vehicle #%d, %d requests)",
            trip.trip_code, driver.id, vehicle.id, len(requests),
        )
        return trip, assignment

    @staticmethod
    def _has_active_trip(db: Session, driver_id: int) -> bool:
        return (
            db.query(Trip)
            .filter(
                Trip.driver_id == driver_id,
                Trip.status.in_(["Planned", "Active"]),
            )
            .count() > 0
        )


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch orchestration (selection → optimisation → assignment)
# ─────────────────────────────────────────────────────────────────────────────

def dispatch_trip(
    db: Session,
    requests: List[SimulationRequest],
    batch: Optional[DMFEBatch] = None,
    trip_key: Optional[str] = None,
    vehicle_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    pool: Optional[DriverPool] = None,
    commit: bool = True,
) -> Dict:
    """
    Full dispatch of ONE trip:

        Driver Selection → Route Optimization → Trip Assignment

    Returns a dict with {trip, assignment, driver, vehicle, requests,
    route_dict}.  Raises ValueError when no driver/vehicle is available
    or the route cannot be optimized (the caller decides how to handle
    the unassigned requests).
    """
    selector = DriverSelector()
    candidate = selector.select(db, requests, pool=pool)
    if candidate is None:
        raise ValueError(
            f"No available driver/vehicle for trip with {len(requests)} "
            "request(s)"
        )

    driver = candidate.driver
    vehicle = (
        db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if vehicle_id is not None else None
    )
    if vehicle_id is not None and vehicle is None:
        raise ValueError(f"Vehicle #{vehicle_id} not found")
    if vehicle is None:
        vehicle = candidate.vehicle
    if driver_id is not None:
        forced = db.query(Driver).filter(Driver.id == driver_id).first()
        if forced is None:
            raise ValueError(f"Driver #{driver_id} not found")
        driver = forced
        if vehicle_id is None:
            raise ValueError(
                "When forcing a driver, a compatible vehicle_id is required"
            )

    route = route_optimizer.optimize_trip(
        db,
        requests,
        vehicle=vehicle,
        driver=driver,
        trip_key=trip_key,
    )
    trip, assignment = AssignmentEngine().create_assignment(
        db, driver, vehicle, route, requests, batch=batch, commit=commit
    )

    return {
        "trip": trip,
        "assignment": assignment,
        "driver": driver,
        "vehicle": vehicle,
        "requests": requests,
        "route_dict": route.to_dict(),
        "candidate": candidate,
    }


def complete_trip(
    db: Session,
    trip_id: int,
    commit: bool = True,
) -> Trip:
    """
    Complete a dispatched trip and release its resources.

    Atomic lifecycle transition (mirrors AssignmentEngine.create_assignment):

      Trip        → status='Completed', completed_at=now
      Assignment  → status='Completed', completed_at=now
      History     → status='Completed', completion_time=now
      Driver      → status='Available'
      Vehicle     → status='Available'
      Requests    → status='Completed'

    Without this transition a completed trip would permanently hold its
    driver/vehicle Busy, starving Gate E (driver availability) for every
    future batch — the root cause of 100% rejection runs.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise ValueError(f"Trip #{trip_id} not found")
    if trip.status == "Completed":
        return trip

    now = datetime.now(timezone.utc)

    trip.status = "Completed"
    trip.completed_at = now

    assignment = (
        db.query(DriverAssignment)
        .filter(DriverAssignment.trip_id == trip.id)
        .first()
    )
    if assignment is not None:
        assignment.status = "Completed"
        assignment.completed_at = now

    if trip.driver_id is not None and getattr(trip, "_skip_availability", False) is False:
        driver = db.query(Driver).filter(Driver.id == trip.driver_id).first()
        if driver is not None:
            driver.status = "Available"

    if trip.vehicle_id is not None and getattr(trip, "_skip_availability", False) is False:
        vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).first()
        if vehicle is not None:
            vehicle.status = "Available"

    # Link the most recent Active history row for this driver+vehicle
    if trip.driver_id is not None and trip.vehicle_id is not None:
        history = (
            db.query(DriverAssignmentHistory)
            .filter(
                DriverAssignmentHistory.driver_id == trip.driver_id,
                DriverAssignmentHistory.vehicle_id == trip.vehicle_id,
                DriverAssignmentHistory.status == "Active",
            )
            .order_by(DriverAssignmentHistory.assignment_time.desc())
            .first()
        )
        if history is not None:
            history.status = "Completed"
            history.completion_time = now

    request_ids = json_loads(trip.request_ids_json, [])
    if request_ids:
        db.query(SimulationRequest).filter(
            SimulationRequest.id.in_(request_ids)
        ).update({"status": "Completed"}, synchronize_session=False)

    # A-DMFE Module 8 — fold the actual outcome into the learning state
    # (never blocks trip completion; failures are logged and swallowed)
    try:
        from app.dmfe.adaptive.learning import learning_engine

        learning_engine.record_trip_outcome(db, trip, commit=False)
    except Exception:
        logger.warning(
            "A-DMFE outcome ingestion skipped for trip %s (id=%d)",
            trip.trip_code, trip.id,
        )

    if commit:
        db.commit()
        db.refresh(trip)

    logger.info(
        "Trip %s (id=%d) completed — driver #%s and vehicle #%s released",
        trip.trip_code, trip.id, trip.driver_id, trip.vehicle_id,
    )
    return trip


def complete_stale_trips(db: Session, max_age_min: float = 45.0) -> int:
    """
    Release any trip stuck in 'Planned'/'Active' beyond max_age_min.

    Called on startup and before pipeline runs so stuck trips can never
    permanently block driver/vehicle availability.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_min)
    stale = (
        db.query(Trip)
        .filter(
            Trip.status.in_(["Planned", "Active"]),
            Trip.created_at < cutoff,
        )
        .all()
    )
    if not stale:
        return 0

    # Bulk update to avoid N+1 queries in the loop below
    driver_ids = [t.driver_id for t in stale if t.driver_id is not None]
    vehicle_ids = [t.vehicle_id for t in stale if t.vehicle_id is not None]

    if driver_ids:
        db.query(Driver).filter(Driver.id.in_(driver_ids)).update(
            {"status": "Available"}, synchronize_session=False
        )
    if vehicle_ids:
        db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).update(
            {"status": "Available"}, synchronize_session=False
        )

    count = 0
    for trip in stale:
        setattr(trip, "_skip_availability", True)
        complete_trip(db, trip.id, commit=False)
        count += 1
    
    db.commit()
    logger.info("Released %d stale trip(s) older than %.0f min", len(stale), max_age_min)
    return len(stale)
