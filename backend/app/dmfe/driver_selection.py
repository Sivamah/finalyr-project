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
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import (
    Driver,
    DriverAssignment,
    DriverAssignmentHistory,
    SimulationRequest,
    SystemConfig,
    Trip,
    Vehicle,
)
from app.dmfe.models import DMFEBatch
from app.dmfe.optimizer import OptimizedRoute, _load_vrp_rules, route_optimizer
from app.engine.distance import haversine

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Selection rules (configurable via SystemConfig, never overwritten)
# ─────────────────────────────────────────────────────────────────────────────

SELECTOR_RULE_DEFAULTS: Dict[str, float] = {
    "driver_proximity_weight": 0.50,   # w_prox — how close the driver is
    "driver_type_weight": 0.30,        # w_type — vehicle-type match
    "driver_workload_weight": 0.20,    # w_work — workload fairness
    "driver_eta_limit_min": 30.0,      # ETA ceiling for a full proximity score
    "driver_max_search_km": 25.0,      # search radius around the trip anchor
    "driver_avg_speed_kmh": 25.0,      # ETA fallback speed
}

SELECTOR_RULE_KEYS: Tuple[str, ...] = tuple(SELECTOR_RULE_DEFAULTS.keys())


def _load_selector_rules(db: Optional[Session]) -> Dict[str, float]:
    """Load driver-selection weights from SystemConfig; fall back to defaults."""
    rules = dict(SELECTOR_RULE_DEFAULTS)
    if db is None:
        return rules
    for key in SELECTOR_RULE_KEYS:
        row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if row:
            try:
                rules[key] = float(row.value)
            except (ValueError, TypeError):
                pass
    return rules


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
    workload_score: float       # 0..1 — availability fairness
    eta_min: float              # estimated arrival at the trip anchor
    total_score: float          # weighted combination

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
            "eta_min": round(self.eta_min, 1),
            "total_score": round(self.total_score, 3),
        }


# ─────────────────────────────────────────────────────────────────────────────
# DriverSelector
# ─────────────────────────────────────────────────────────────────────────────

class DriverSelector:
    """
    Picks the best available (driver, vehicle) pair for a trip.

    Hard filters (no candidate → no dispatch):
      1. Driver status == "Available"
      2. Driver has no other active Trip / assignment
      3. Vehicle is Available, active, within driver_max_search_km
      4. Vehicle capacity >= combined demand, weight <= max_weight_kg

    Soft scoring (weights from SystemConfig):
      total = w_prox * proximity + w_type * type + w_work * workload
    """

    def select(
        self,
        db: Session,
        requests: List[SimulationRequest],
        rules: Optional[Dict[str, float]] = None,
    ) -> Optional[DriverCandidate]:
        if not requests:
            return None

        rules = rules or _load_selector_rules(db)
        vrp = _load_vrp_rules(db)
        total_demand = sum(r.demand or 1 for r in requests)
        total_weight = sum(r.weight_kg or 0.0 for r in requests)
        if total_weight > vrp.get("max_weight_kg", 100.0):
            logger.info("DriverSelector: combined weight %.1f kg exceeds limit",
                        total_weight)
            return None

        anchor_lat, anchor_lng = self._trip_anchor(requests)
        max_km = rules.get("driver_max_search_km", 25.0)
        eta_limit = rules.get("driver_eta_limit_min", 30.0)
        speed = rules.get("driver_avg_speed_kmh", 25.0)
        w_prox = rules.get("driver_proximity_weight", 0.5)
        w_type = rules.get("driver_type_weight", 0.3)
        w_work = rules.get("driver_workload_weight", 0.2)

        best: Optional[DriverCandidate] = None
        drivers = (
            db.query(Driver)
            .filter(Driver.status == "Available")
            .order_by(Driver.id.asc())
            .all()
        )
        if not drivers:
            logger.info("DriverSelector: no Available drivers")
            return None

        for driver in drivers:
            active = self._active_trip_count(db, driver.id)
            if active > 0:
                continue  # never double-book a driver

            eta_km = haversine(
                anchor_lat, anchor_lng,
                driver.current_lat or 11.0168, driver.current_lng or 76.9558,
            )
            if eta_km > max_km:
                continue

            vehicle = self._fit_vehicle(db, driver, total_demand, anchor_lat, anchor_lng)
            if vehicle is None:
                continue

            eta_min = (eta_km / max(speed, 1.0)) * 60.0
            proximity = max(0.0, 1.0 - eta_min / max(eta_limit, 1.0))
            type_score = self._type_match_score(vehicle, requests)
            workload_score = max(0.0, 1.0 - 0.5 * active)  # active == 0 → 1.0
            total = (w_prox * proximity + w_type * type_score
                     + w_work * workload_score)

            candidate = DriverCandidate(
                driver=driver, vehicle=vehicle,
                proximity_score=proximity, type_score=type_score,
                workload_score=workload_score, eta_min=eta_min,
                total_score=total,
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

    # ── scoring helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _trip_anchor(requests: List[SimulationRequest]) -> Tuple[float, float]:
        """Centroid of the pickups — where the driver must arrive first."""
        n = len(requests)
        lat = sum(r.pickup_lat for r in requests) / n
        lng = sum(r.pickup_lng for r in requests) / n
        return lat, lng

    def _active_trip_count(self, db: Session, driver_id: int) -> int:
        """Count active trips/assignments; used to prevent double-booking."""
        trip_count = (
            db.query(Trip)
            .filter(
                Trip.driver_id == driver_id,
                Trip.status.in_(["Planned", "Active"]),
            )
            .count()
        )
        legacy_count = (
            db.query(DriverAssignmentHistory)
            .filter(
                DriverAssignmentHistory.driver_id == driver_id,
                DriverAssignmentHistory.status == "Active",
            )
            .count()
        )
        return trip_count + legacy_count

    def _fit_vehicle(
        self,
        db: Session,
        driver: Driver,
        total_demand: int,
        anchor_lat: float,
        anchor_lng: float,
    ) -> Optional[Vehicle]:
        """
        Preferred: the driver's assigned vehicle (if Available and fits).
        Fallback: the nearest Available vehicle that fits the demand.
        """
        preferred = None
        if driver.assigned_vehicle_id is not None:
            preferred = db.query(Vehicle).filter(
                Vehicle.id == driver.assigned_vehicle_id,
                Vehicle.status == "Available",
                Vehicle.is_active.is_(True),
                Vehicle.capacity >= total_demand,
            ).first()
        if preferred is not None:
            return preferred

        candidates = (
            db.query(Vehicle)
            .filter(
                Vehicle.status == "Available",
                Vehicle.is_active.is_(True),
                Vehicle.capacity >= total_demand,
            )
            .all()
        )
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda v: haversine(
                anchor_lat, anchor_lng,
                v.current_lat or 11.0168, v.current_lng or 76.9558,
            ),
        )

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
    ) -> Trip:
        """
        Create Trip + DriverAssignment (+ history) and update the state of
        driver, vehicle, requests and batch.  Returns the Trip row.
        """
        if driver.status != "Available":
            raise ValueError(
                f"Driver #{driver.id} ({driver.name}) is not Available"
            )
        if self._has_active_trip(db, driver.id):
            raise ValueError(
                f"Driver #{driver.id} ({driver.name}) already has an active trip"
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

        db.add(DriverAssignment(
            trip_id=trip.id,
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            driver_name=driver.name,
            vehicle_name=vehicle.name,
            assignment_type=assignment_type,
            status="Active",
        ))
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
            db.refresh(trip)
        logger.info(
            "AssignmentEngine: trip %s (driver #%d, vehicle #%d, %d requests)",
            trip.trip_code, driver.id, vehicle.id, len(requests),
        )
        return trip

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
    candidate = selector.select(db, requests)
    if candidate is None:
        raise ValueError(
            f"No available driver/vehicle for trip with {len(requests)} "
            "request(s)"
        )

    driver = candidate.driver
    vehicle = vehicle_id and db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
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
    trip = AssignmentEngine().create_assignment(
        db, driver, vehicle, route, requests, batch=batch
    )
    db.refresh(trip)
    assignment = (
        db.query(DriverAssignment)
        .filter(DriverAssignment.trip_id == trip.id)
        .first()
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


# Module-level singletons
driver_selector = DriverSelector()
assignment_engine = AssignmentEngine()
