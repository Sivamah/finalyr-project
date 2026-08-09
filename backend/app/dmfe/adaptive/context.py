"""
A-DMFE Module 1 — Context Awareness Engine
===========================================
Builds a normalised :class:`ContextProfile` from live system state before
every batching run.  The profile couples the otherwise static compatibility
engine to the operating environment:

  - Traffic density        (scenario multiplier + pickup-cluster congestion)
  - Pending requests       (demand pressure)
  - Driver availability    (available / total)
  - Vehicle capacity       (capacity stress: pending demand vs free fleet)
  - Service demand         (Shannon entropy of the pending service mix)
  - Time of day            (rush-hour factor)
  - Request priority       (priority pressure: fraction of High requests)

The profile is fully deterministic for a given database state and drives
the Adaptive Weight Generator (Module 2) and the Adaptive Decision Engine
(Module 6).  No machine learning, no external APIs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import SimulationRequest, SimulationScenario, Driver, Vehicle
from app.dmfe.adaptive._util import _clamp01
from app.dmfe.compatibility import get_config_value

# Config fallback values (also seeded by decision_engine._seed_dmfe_configs)
TRAFFIC_MULTIPLIER_KEY = "traffic_multiplier"
TRAFFIC_MULTIPLIER_DEFAULT = 1.0

# Demand pressure saturation: 300+ pending requests → pressure = 1.0
DEMAND_SATURATION = 300.0
# Congestion proximity threshold (km): pickups closer than this count as a hotspot
CONGESTION_RADIUS_KM = 1.5
# Driver ETA speed for the waiting-time estimate (km/h)
ETA_SPEED_KMH = 25.0


def _safe_hour(dt: Optional[datetime]) -> float:
    if dt is None:
        return float(datetime.now(timezone.utc).hour)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return float(dt.hour)


@dataclass
class ContextProfile:
    """Normalised description of the operating context at decision time."""

    # Core context signals (all in [0, 1])
    traffic_index: float = 0.4          # 0 calm … 1 gridlocked
    demand_pressure: float = 0.0        # 0 idle … 1 saturated queue
    driver_availability: float = 1.0    # 0 none free … 1 all free
    capacity_stress: float = 0.0        # 0 ample … 1 fleet over-committed
    service_entropy: float = 0.5        # 0 mono-service … 1 fully mixed
    rush_factor: float = 0.2            # 0 off-peak … 1 peak hour
    priority_pressure: float = 0.0      # fraction of High-priority requests

    # Learned-correction pressures (Module 8; 0 = no learned effect)
    fuel_pressure: float = 0.0          # 0 baseline … 1 fuel runs above benchmark
    co2_pressure: float = 0.0           # 0 baseline … 1 CO2 above benchmark
    utilization_gap: float = 0.0        # 0 util matches prediction … 1 under-utilised

    # Raw values kept for explainability / dashboards
    raw: Dict[str, Any] = field(default_factory=dict)

    # Derived convenience signals
    driver_scarcity: float = 0.0        # 1 - driver_availability
    avg_driver_eta_min: float = 5.0     # mean ETA of available drivers to demand centroid

    @property
    def is_stressed(self) -> bool:
        """Heavy load heuristic used by the explainer."""
        return (
            self.traffic_index >= 0.6
            or self.demand_pressure >= 0.6
            or self.driver_scarcity >= 0.6
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "traffic_index": round(self.traffic_index, 3),
            "demand_pressure": round(self.demand_pressure, 3),
            "driver_availability": round(self.driver_availability, 3),
            "driver_scarcity": round(self.driver_scarcity, 3),
            "capacity_stress": round(self.capacity_stress, 3),
            "service_entropy": round(self.service_entropy, 3),
            "rush_factor": round(self.rush_factor, 3),
            "priority_pressure": round(self.priority_pressure, 3),
            "fuel_pressure": round(self.fuel_pressure, 3),
            "co2_pressure": round(self.co2_pressure, 3),
            "utilization_gap": round(self.utilization_gap, 3),
            "avg_driver_eta_min": round(self.avg_driver_eta_min, 1),
            "raw": {k: round(v, 4) if isinstance(v, float) else v
                    for k, v in self.raw.items()},
        }


class ContextAwarenessEngine:
    """
    Gathers the live system signals and composes a ContextProfile.

    Usage:
        profile = ContextAwarenessEngine().build(db, pending_requests)
    """

    # ────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ────────────────────────────────────────────────────────────────────────

    def build(
        self,
        db: Session,
        pending: Optional[List[SimulationRequest]] = None,
    ) -> ContextProfile:
        if pending is None:
            pending = (
                db.query(SimulationRequest)
                .filter(SimulationRequest.status == "Pending")
                .all()
            )
        profile = ContextProfile()
        n = len(pending)

        # 1. Traffic density: scenario multiplier + pickup-cluster congestion
        profile.traffic_index = self._traffic_index(db, pending, n)

        # 2. Demand pressure: pending queue saturation
        profile.demand_pressure = _clamp01(n / DEMAND_SATURATION)

        # 3. Driver availability ratio
        profile.driver_availability, avg_eta = self._driver_signals(db, pending, n)
        profile.driver_scarcity = round(1.0 - profile.driver_availability, 4)
        profile.avg_driver_eta_min = round(avg_eta, 1)

        # 4. Vehicle capacity stress
        profile.capacity_stress = self._capacity_stress(db, pending, n)

        # 5. Service demand entropy (normalised Shannon entropy of the mix)
        profile.service_entropy = self._service_entropy(pending, n)

        # 6. Time-of-day rush factor (peaks ~09:00 and ~18:30)
        profile.rush_factor = _rush_factor(_safe_hour(None))

        # 7. Priority pressure
        profile.priority_pressure = self._priority_pressure(pending, n)

        profile.raw = {
            "pending_count": n,
            "traffic_multiplier": self._raw.get("traffic_multiplier", 1.0),
            "congestion_index": self._raw.get("congestion_index", 0.0),
            "mean_nearest_pickup_km": self._raw.get("mean_nearest_pickup_km", 0.0),
            "available_drivers": self._raw.get("available_drivers", 0),
            "total_drivers": self._raw.get("total_drivers", 0),
            "available_vehicles": self._raw.get("available_vehicles", 0),
            "mean_pending_demand": self._raw.get("mean_pending_demand", 0.0),
            "mean_fleet_capacity": self._raw.get("mean_fleet_capacity", 0.0),
            "hour_of_day": self._raw.get("hour_of_day", 0),
            "high_priority_fraction": self._raw.get("high_priority_fraction", 0.0),
        }

        # ── Learned corrections (Module 8) ──────────────────────────────────
        # Injected as derived pressures so the adaptive weight generator can
        # react to learned fuel/CO2/utilization gaps without touching the
        # scoring files.  Deterministic: depends only on the DB state.
        try:
            from app.dmfe.adaptive.learning import LearningEngine

            corridor = _corridor_key(pending)
            learned = LearningEngine.learned_signals(db, corridor)
            profile.fuel_pressure = _clamp01(
                max(0.0, float(learned["fuel_multiplier"]) - 1.0)
            )
            profile.co2_pressure = _clamp01(
                max(0.0, float(learned["co2_multiplier"]) - 1.0)
            )
            profile.utilization_gap = _clamp01(
                max(0.0, 1.0 - float(learned["utilization_factor"]))
            )
            profile.raw["learned_corridor"] = corridor
            profile.raw["learned_delay_multiplier"] = learned["delay_multiplier"]
            profile.raw["learned_fuel_multiplier"] = learned["fuel_multiplier"]
            profile.raw["learned_co2_multiplier"] = learned["co2_multiplier"]
            profile.raw["learned_utilization_factor"] = learned["utilization_factor"]
            profile.raw["learned_delay_residual_mean_min"] = learned[
                "delay_residual_mean"
            ]
            profile.raw["learned_driver_quality"] = learned["driver_quality"]
        except Exception:
            pass  # learning must never break context building
        return profile

    # ────────────────────────────────────────────────────────────────────────
    # Signal estimators (each returns a normalised value in [0, 1])
    # ────────────────────────────────────────────────────────────────────────

    def __init_state(self, db: Session) -> None:
        self._raw: Dict[str, Any] = {}
        self._scenario_traffic: float = TRAFFIC_MULTIPLIER_DEFAULT
        try:
            raw = get_config_value(db, TRAFFIC_MULTIPLIER_KEY)
            if raw is not None:
                try:
                    self._scenario_traffic = float(raw)
                except (ValueError, TypeError):
                    pass
        except Exception:
            pass
        try:
            scenario = (
                db.query(SimulationScenario)
                .order_by(SimulationScenario.id.desc())
                .first()
            )
            if scenario is not None and scenario.traffic_multiplier:
                self._scenario_traffic = max(
                    float(scenario.traffic_multiplier), 0.5
                )
                self._raw["scenario_weather"] = scenario.weather_condition
        except Exception:
            pass
        self._raw["traffic_multiplier"] = round(self._scenario_traffic, 3)

    def _traffic_index(
        self, db: Session, pending: List[SimulationRequest], n: int
    ) -> float:
        self.__init_state(db)
        # Scenario component: multiplier 0.8 → 0, 2.2 → 1
        scenario_traffic = _clamp01((self._scenario_traffic - 0.8) / 1.4)
        # Congestion component: mean nearest-neighbour pickup distance
        congestion = 0.0
        if n >= 2:
            # Symmetric distance scan: every pair is measured once and reused,
            # halving the O(n²) haversine work on large pending queues while
            # producing the exact same nearest-neighbour value as brute force.
            dist: List[List[float]] = [[0.0] * n for _ in range(n)]
            for i in range(n):
                for j in range(i + 1, n):
                    d = _haversine(
                        pending[i].pickup_lat, pending[i].pickup_lng,
                        pending[j].pickup_lat, pending[j].pickup_lng,
                    )
                    dist[i][j] = d
                    dist[j][i] = d
            mean_nn = sum(min(dist[i][j] for j in range(n) if j != i)
                          for i in range(n)) / n
            congestion = _clamp01((CONGESTION_RADIUS_KM - mean_nn) / CONGESTION_RADIUS_KM)
            self._raw["mean_nearest_pickup_km"] = round(mean_nn, 3)
        self._raw["congestion_index"] = round(congestion, 3)
        self._raw["scenario_traffic"] = round(scenario_traffic, 3)
        return round(0.6 * scenario_traffic + 0.4 * congestion, 4)

    def _driver_signals(
        self, db: Session, pending: List[SimulationRequest], n: int
    ) -> tuple:
        total = db.query(Driver).count()
        if total == 0:
            return 1.0, 5.0  # no drivers seeded → availability neutral
        available = db.query(Driver).filter(Driver.status == "Available").all()
        avail_count = len(available)
        ratio = avail_count / total
        # Mean ETA of free drivers to the demand centroid (waiting-time proxy)
        eta_min = 5.0
        if avail_count and n:
            lat = sum(r.pickup_lat for r in pending) / n
            lng = sum(r.pickup_lng for r in pending) / n
            etas = [
                _haversine(lat, lng, d.current_lat or 11.0168, d.current_lng or 76.9558)
                / max(ETA_SPEED_KMH, 1.0) * 60.0
                for d in available
            ]
            eta_min = sum(etas) / len(etas)
        self._raw["available_drivers"] = avail_count
        self._raw["total_drivers"] = total
        return round(ratio, 4), eta_min

    def _capacity_stress(
        self, db: Session, pending: List[SimulationRequest], n: int
    ) -> float:
        mean_demand = (sum(r.demand or 1 for r in pending) / n) if n else 1.0
        vehicles = (
            db.query(Vehicle)
            .filter(Vehicle.status == "Available", Vehicle.is_active.is_(True))
            .all()
        )
        if not vehicles:
            self._raw["mean_fleet_capacity"] = 0.0
            self._raw["mean_pending_demand"] = round(mean_demand, 3)
            self._raw["fleet_mean_mileage_kmpl"] = 0.0
            return 1.0
        mean_cap = sum(v.capacity or 1 for v in vehicles) / len(vehicles)
        mean_mileage = (
            sum(v.mileage_kmpl or 15.0 for v in vehicles) / len(vehicles)
        )
        self._raw["available_vehicles"] = len(vehicles)
        self._raw["mean_fleet_capacity"] = round(mean_cap, 3)
        self._raw["mean_pending_demand"] = round(mean_demand, 3)
        self._raw["fleet_mean_mileage_kmpl"] = round(mean_mileage, 3)
        return round(_clamp01(mean_demand / max(mean_cap, 1.0)), 4)

    @staticmethod
    def _service_entropy(pending: List[SimulationRequest], n: int) -> float:
        if n == 0:
            return 0.5
        counts: Dict[str, int] = {}
        for r in pending:
            t = (r.request_type or "ride").lower()
            counts[t] = counts.get(t, 0) + 1
        probs = [c / n for c in counts.values()]
        entropy = -sum(p * math.log(p) for p in probs if p > 0)
        # Normalise by log3 (three possible service classes)
        return round(_clamp01(entropy / math.log(3)), 4)

    @staticmethod
    def _priority_pressure(pending: List[SimulationRequest], n: int) -> float:
        if n == 0:
            return 0.0
        high = sum(1 for r in pending if (r.priority or "Medium") == "High")
        return round(high / n, 4)


def _rush_factor(hour: float) -> float:
    """Time-of-day peak curve: ~09:00 and ~18:30 peaks, 0.2 baseline."""
    morning = math.exp(-((hour - 9.0) ** 2) / 6.0)
    evening = math.exp(-((hour - 18.5) ** 2) / 6.0)
    return round(_clamp01(0.2 + 0.8 * max(morning, evening)), 4)


def _corridor_key(requests) -> str:
    """Corridor key of the pending mix (same convention as Module 8)."""
    types = sorted({(r.request_type or "ride").lower() for r in requests})
    return "|".join(types) if types else "unknown"


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    from app.engine.distance import haversine

    return haversine(lat1, lng1, lat2, lng2)
