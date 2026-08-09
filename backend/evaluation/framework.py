"""
DMFE Phase 10 — Experimental Evaluation Framework
==================================================
Read-only evaluation harness for the Phase 9 DMFE pipeline
(backend/app/dmfe).  It exercises the *existing* engine through its
documented programmatic entry points and NEVER modifies engine code.

Key design decisions
--------------------
- Every workload runs against a fresh SQLite schema (drop_all + create_all)
  so experiments are independent and the developer DB (dmfe_dev.db) is
  never touched.
- Requests are generated with the platform's own generator
  (app.services.mock_adapters.generate_simulation_requests) so the mix
  of ride / food / parcel requests matches the production simulator.
- Google Maps is disabled for the experiments (GOOGLE_MAPS_API_KEY="")
  so the deterministic haversine distance matrix is used — no external
  network dependency, fully reproducible runs.
- Stage timings (batch formation / route optimisation / driver selection /
  assignment) are captured by *timing wrappers* around the existing
  methods; the wrapped methods themselves are unmodified.
- Baseline system: every request served individually, no batching, no
  DMFE, no route optimisation.  Distance = haversine(pickup, drop) x
  road_factor; fuel = km / fleet-mean mileage of the preferred vehicle
  type; CO2 = fuel x 2.3 kg/L (the same factor the DMFE optimizer uses).
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Experiment configuration (must be set BEFORE importing app modules)
# ─────────────────────────────────────────────────────────────────────────────

EXPERIMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
EVAL_DB_PATH = os.path.join(EXPERIMENTS_DIR, "eval.db")

os.environ["DATABASE_URL"] = f"sqlite:///{EVAL_DB_PATH}"
os.environ["GOOGLE_MAPS_API_KEY"] = ""  # force deterministic haversine fallback

WORKLOADS = [50, 100, 250, 500]
REQUEST_MIX = {"ride": 0.40, "food": 0.40, "parcel": 0.20}   # same as default simulator mix
FLEET_SIZE = 60
MAX_WAVES = 25
CO2_FACTOR = 2.3                # kg CO2 per litre of fuel (matches optimizer.py)
ROAD_FACTOR = 1.25              # haversine -> road distance multiplier
AVG_SPEED_KMH = 25.0            # baseline travel speed (same as VRP fallback)

FLEET_SPEC: List[Tuple[str, int, float, int]] = [
    # (vehicle_type, capacity, mileage_kmpl, count)
    ("Bike",  1, 40.0, 10),
    ("Bike",  2, 40.0, 14),   # food delivery bikes
    ("Auto",  3, 25.0, 10),
    ("Car",   4, 15.5, 16),
    ("Van",   8, 13.0, 6),
    ("Van",  12, 13.0, 2),
    ("Truck", 15, 8.0, 2),
]

# vehicle_type -> provider category for fleet seeding
VTYPE_TO_PROVIDER: Dict[str, str] = {
    "Bike": "Ride", "Auto": "Ride", "Car": "Ride",
    "Van": "Parcel", "Truck": "Parcel",
}

# Config keys the engine reads (seeded so all runs are reproducible)
ADMFE_MODE = os.environ.get("ADMFE_MODE", "adaptive")  # "adaptive" | "static"

SYSTEM_CONFIG: Dict[str, str] = {
    "pickup_weight": "0.30",
    "route_weight": "0.25",
    "time_weight": "0.20",
    "capacity_weight": "0.15",
    "priority_weight": "0.10",
    "destination_weight": "0.20",
    "route_overlap_weight": "0.20",
    "min_compatibility_score": "70",
    "max_pickup_radius_km": "5",
    "max_allowed_delay_min": "20",
    "max_vehicle_capacity": "6",
    "max_weight_kg": "100",
    "vrp_time_weight": "0.3",
    "vrp_fuel_weight": "1.0",
    "vrp_priority_bonus_m": "2000",
    "service_time_min": "2",
    "avg_speed_kmh": "25",
    "road_factor": "1.25",
    "fuel_price_per_l": "100",
    "google_chunk_size": "10",
    "driver_proximity_weight": "0.50",
    "driver_type_weight": "0.30",
    "driver_workload_weight": "0.20",
    "driver_eta_limit_min": "30",
    "driver_max_search_km": "25",
    "driver_avg_speed_kmh": "25",
    # A-DMFE (adaptive framework) — mode toggles the full adaptive stack
    "admfe.mode": ADMFE_MODE,
    "admfe.base_bqs_threshold": "0.55",
    "admfe.learning_enabled": "true",
    "admfe.learning_max_bias": "0.15",
    "traffic_multiplier": "1.0",
}


# ─────────────────────────────────────────────────────────────────────────────
# app imports (must happen after env configuration)
# ─────────────────────────────────────────────────────────────────────────────

from sqlalchemy.orm import Session  # noqa: E402

from app.db.database import Base, engine, SessionLocal  # noqa: E402
from app.db.models import (  # noqa: E402
    Provider, Vehicle, Driver, SimulationRequest, Trip,
    DriverAssignment, DriverAssignmentHistory, SystemConfig,
)
from app.dmfe.models import DMFEBatch  # noqa: E402
from app.dmfe.pipeline import PipelineRunner  # noqa: E402
from app.dmfe.batch_generator import BatchGenerator  # noqa: E402
from app.dmfe.compatibility import CompatibilityCalculator  # noqa: E402
from app.dmfe import batch_generator as _bg_mod  # noqa: E402
from app.dmfe import driver_selection as _ds_mod  # noqa: E402
from app.dmfe import optimizer as _opt_mod  # noqa: E402
from app.dmfe import pipeline as _pl_mod  # noqa: E402
from app.dmfe.adaptive.learning import LearningEngine  # noqa: E402
from app.engine.distance import haversine  # noqa: E402
from app.core.json_utils import json_loads  # noqa: E402
from app.services.mock_adapters import generate_simulation_requests, COIMBATORE_AREAS  # noqa: E402
from app.api.routes.providers import SEED_PROVIDERS  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# SQL query counter — counts every cursor execution on the eval engine
# ─────────────────────────────────────────────────────────────────────────────

class QueryCounter:
    """Counts SQL statements executed on the engine via sqlalchemy events."""

    def __init__(self) -> None:
        self.count = 0
        self._installed = False

    def _on_cursor(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1

    def install(self) -> None:
        from sqlalchemy import event as sa_event
        sa_event.listen(engine, "before_cursor_execute", self._on_cursor)
        self._installed = True

    def uninstall(self) -> None:
        from sqlalchemy import event as sa_event
        if self._installed:
            sa_event.remove(engine, "before_cursor_execute", self._on_cursor)
            self._installed = False

    def __enter__(self) -> "QueryCounter":
        self.install()
        return self

    def __exit__(self, *exc) -> None:
        self.uninstall()


def stage_share(part_s: float, total_s: float) -> float:
    """Percentage of `part_s` inside `total_s` (0.0 if total <= 0)."""
    return round(part_s / total_s * 100.0, 1) if total_s > 0 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Timing probe — wraps engine methods WITHOUT changing their behaviour
# ─────────────────────────────────────────────────────────────────────────────

class Probe:
    """Records wall-clock durations of every call to a wrapped method."""

    def __init__(self) -> None:
        self.times: List[float] = []

    def wrap(self, cls: type, method_name: str) -> None:
        original = getattr(cls, method_name)

        def wrapped(*args, **kwargs):
            t0 = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                self.times.append(time.perf_counter() - t0)

        setattr(cls, method_name, wrapped)

    def wrap_module(self, module, name: str) -> None:
        original = getattr(module, name)

        def wrapped(*args, **kwargs):
            t0 = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                self.times.append(time.perf_counter() - t0)

        setattr(module, name, wrapped)

    @property
    def total_s(self) -> float:
        return sum(self.times)

    def avg_ms(self) -> float:
        return (self.total_s * 1000.0 / len(self.times)) if self.times else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Experiment database lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class ExperimentDB:
    """Fresh-schema SQLite database for one workload."""

    def __init__(self) -> None:
        os.makedirs(EXPERIMENTS_DIR, exist_ok=True)
        os.makedirs(RESULTS_DIR, exist_ok=True)

    def reset_schema(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def seed_system_config(self, db: Session) -> None:
        self.seed_system_config_with(db, SYSTEM_CONFIG)

    def seed_system_config_with(self, db: Session, config: Dict[str, str]) -> None:
        for key, value in config.items():
            db.add(SystemConfig(category="ai_rules", key=key,
                                value=value, data_type="float"))
        db.commit()

    def seed_fleet(self, db: Session, rng: random.Random) -> None:
        providers = self._seed_providers(db)
        area_pts = list(COIMBATORE_AREAS.values())

        fleet: List[Tuple[str, int, float]] = []
        spec_index = 0
        while len(fleet) < FLEET_SIZE:
            vtype, cap, mileage, count = FLEET_SPEC[spec_index % len(FLEET_SPEC)]
            spec_index += 1
            fleet.extend([(vtype, cap, mileage)] * count)
        fleet = fleet[:FLEET_SIZE]

        for i, (vtype, cap, mileage) in enumerate(fleet):
            lat = area_pts[i % len(area_pts)][0] + rng.uniform(-0.008, 0.008)
            lng = area_pts[i % len(area_pts)][1] + rng.uniform(-0.008, 0.008)
            provider = providers[VTYPE_TO_PROVIDER[vtype]]
            vehicle = Vehicle(
                provider_id=provider.id,
                name=f"Fleet {vtype} {i + 1:02d}",
                vehicle_type=vtype,
                registration_number=f"EVL-{i + 1:04d}",
                capacity=cap,
                fuel_type="Petrol",
                mileage_kmpl=mileage,
                cost_per_km=10.0,
                status="Available",
                current_lat=lat,
                current_lng=lng,
                is_active=True,
            )
            db.add(vehicle)
            db.flush()
            driver = Driver(
                provider_id=provider.id,
                name=f"Driver {i + 1:02d}",
                phone=f"+91 90000 {i:04d}",
                status="Available",
                current_lat=lat,
                current_lng=lng,
                assigned_vehicle_id=vehicle.id,
            )
            db.add(driver)
            vehicle.current_driver_id = driver.id
        db.commit()

    def _seed_providers(self, db: Session) -> Dict[str, Provider]:
        providers: Dict[str, Provider] = {}
        for seed in SEED_PROVIDERS:
            p = Provider(
                name=seed["name"],
                provider_type=seed["provider_type"],
                category=seed["category"],
                operating_area="Coimbatore",
                api_status="Simulated",
                simulation_mode=True,
                description=seed.get("description", ""),
                pricing_model=seed.get("pricing_model", "{}"),
                service_constraints=seed.get("service_constraints", "{}"),
            )
            db.add(p)
            db.flush()
            providers[p.provider_type] = p
        db.commit()
        return providers


# ─────────────────────────────────────────────────────────────────────────────
# Workload runner
# ─────────────────────────────────────────────────────────────────────────────

class WorkloadRunner:
    def __init__(self, workload: int, seed: int) -> None:
        self.workload = workload
        self.seed = seed
        self.requests: List[SimulationRequest] = []
        self.batch_probe = Probe()
        self.dispatch_probe = Probe()
        self.optimize_probe = Probe()
        self.select_probe = Probe()
        self.decision_probe = Probe()
        self.persist_probe = Probe()
        self.learn_probe = Probe()
        self.wave_trip_ids: List[int] = []
        self.wave_sql_queries: int = 0
        # deterministic execution model RNG (independent of dispatch RNG)
        self._exec_rng = random.Random(seed + 9000)

    @staticmethod
    def exec_scatter(execution: str = "scatter") -> Dict[str, Any]:
        """
        Execution model parameters for simulated trip outcomes.

        ``scatter``    — default: actuals wobble around the predictions.
        ``delay_x1.4`` — controlled feed-forward scenario (Step 5):
                         actual delay is EXACTLY 1.4× the predicted delay,
                         other signals scatter-free.
        """
        if execution == "delay_x1.4":
            return {
                "delay_scatter": (1.0, 1.0),
                "delay_bias": 1.4,
                "utilization_scatter": (1.0, 1.0),
                "fuel_scatter": (1.0, 1.0),
            }
        return {
            "delay_scatter": (0.85, 1.45),
            "delay_bias": 1.0,
            "utilization_scatter": (0.9, 1.1),
            "fuel_scatter": (0.9, 1.35),
        }

    def simulate_execution(self, db: Session, trip: Any) -> Any:
        """
        Simulated EXECUTION of a dispatched trip: writes actual outcomes
        into the Trip outcome columns from the dispatch-time predictions
        (still present on the trip row) using the deterministic model.

        This is the simulator's honest role — predictions come from the
        real dispatch path; actuals are the execution model's response.
        Uses an instance RNG so runs are reproducible and the dispatch
        path's own randomness is untouched.
        """
        scatter = self.exec_scatter(getattr(self, "execution", "scatter"))
        p_delay = float(trip.max_delay_min or 0.0)
        p_util = float(trip.utilization_pct or 0.0)
        p_fuel = float(trip.fuel_l or 0.0)
        lo, hi = scatter["delay_scatter"]
        trip.max_delay_min = round(
            max(0.0, p_delay * scatter["delay_bias"] * self._exec_rng.uniform(lo, hi)), 2
        )
        lo, hi = scatter["utilization_scatter"]
        trip.utilization_pct = round(
            min(100.0, max(5.0, p_util * self._exec_rng.uniform(lo, hi))), 1
        )
        lo, hi = scatter["fuel_scatter"]
        trip.fuel_l = round(max(0.0, p_fuel * self._exec_rng.uniform(lo, hi)), 3)
        return trip

    def complete_trips_real(self, db: Session) -> int:
        """
        REAL trip completion: simulated execution outcomes, then the app's
        own lifecycle (complete_trip → learning hook).  Never bypasses the
        trip lifecycle the way complete_all_active did.
        """
        from app.dmfe.driver_selection import complete_trip

        trips = db.query(Trip).filter(Trip.status.in_(["Planned", "Active"])).all()
        for t in trips:
            self.simulate_execution(db, t)
            complete_trip(db, t.id, commit=False)
        db.commit()
        return len(trips)

    def install_probes(self) -> None:
        self.batch_probe.wrap(_bg_mod.BatchGenerator, "create_feasible_batches")
        self.optimize_probe.wrap(_opt_mod.RouteOptimizer, "optimize_trip")
        self.select_probe.wrap(_ds_mod.DriverSelector, "select")
        # pipeline decision gate (high-priority delay re-check)
        self.decision_probe.wrap_module(_pl_mod, "_high_priority_violation")
        from sqlalchemy.orm import Session as _Session
        self.persist_probe.wrap(_Session, "commit")
        from app.dmfe.adaptive.learning import learning_engine
        self.learn_probe.wrap(type(learning_engine), "record_trip_outcome")
        # the pipeline holds a direct import reference -> patch it there too
        self.dispatch_probe.wrap_module(_pl_mod, "dispatch_trip")

    def timing_snapshot(self) -> Dict[str, Any]:
        """Stage timing totals for the current probe window."""
        return {
            "pipeline_total_s": 0.0,  # set by the caller from the wall clock
            "batch_formation_total_s": round(self.batch_probe.total_s, 3),
            "batch_formation_calls": len(self.batch_probe.times),
            "decision_total_s": round(self.decision_probe.total_s, 3),
            "decision_calls": len(self.decision_probe.times),
            "persistence_total_s": round(self.persist_probe.total_s, 3),
            "persistence_calls": len(self.persist_probe.times),
            "learning_total_s": round(self.learn_probe.total_s, 3),
            "learning_calls": len(self.learn_probe.times),
            "dispatch_total_s": round(self.dispatch_probe.total_s, 3),
            "dispatch_calls": len(self.dispatch_probe.times),
        }

    def generate_requests(self, db: Session) -> List[SimulationRequest]:
        random.seed(self.seed)
        self.requests = generate_simulation_requests(
            count=self.workload, db=db, request_types=dict(REQUEST_MIX),
        )
        return self.requests

    def run_pipeline(self, db: Session) -> Dict[str, Any]:
        runner = PipelineRunner()
        with QueryCounter() as qc:
            t0 = time.perf_counter()
            result = runner.run(db, limit=self.workload)
            wall_s = time.perf_counter() - t0
        return {
            "result": result,
            "wall_s": wall_s,
            "trip_ids": [d["trip_id"] for d in result.dispatches],
            "sql_queries": qc.count,
        }

    def run_waves(self, db: Session) -> Dict[str, Any]:
        """
        Full-day simulation with the REAL trip lifecycle (Phase 4.1).

        Trips from the previous pass are completed through simulated
        execution + the app's own complete_trip — never by direct status
        flips.  Static mode therefore stays isolated (learning disabled),
        adaptive mode genuinely accumulates outcomes.
        """
        self.complete_trips_real(db)  # close the single-pass trips for real
        waves = 0
        sql_total = 0
        for _ in range(MAX_WAVES):
            pending = (
                db.query(SimulationRequest)
                .filter(SimulationRequest.status == "Pending")
                .count()
            )
            if pending == 0:
                break
            out = self.run_pipeline(db)
            self.wave_trip_ids.extend(out["trip_ids"])
            waves += 1
            sql_total += out.get("sql_queries", 0)
            if not out["trip_ids"]:
                break
            self.complete_trips_real(db)
        self.wave_sql_queries = sql_total
        return {"waves": waves}

    def _wave_metrics(
        self,
        db: Session,
        requests: List[SimulationRequest],
        trip_ids: List[int],
        waves: int,
    ) -> Dict[str, Any]:
        """Aggregate the full multi-wave run (shared with run_workload)."""
        wave_trips = (
            db.query(Trip).filter(Trip.id.in_(trip_ids)).all()
            if trip_ids else []
        )
        wave_dist = sum(t.total_distance_km or 0 for t in wave_trips)
        wave_fuel = sum(t.fuel_l or 0 for t in wave_trips)
        wave_completed = sum(
            1 for r in requests if r.status in ("Assigned", "Completed")
        )
        return {
            "waves": waves,
            "trips_total": len(trip_ids),
            "total_distance_km": round(wave_dist, 2),
            "total_fuel_l": round(wave_fuel, 2),
            "total_co2_kg": round(wave_fuel * CO2_FACTOR, 2),
            "requests_completed": wave_completed,
            "requests_failed": len(requests) - wave_completed,
            "completion_rate_pct": round(wave_completed / len(requests) * 100.0, 1),
        }

    def collect_metrics(
        self, db: Session, trip_ids: List[int],
        status_map: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        trips = (
            db.query(Trip).filter(Trip.id.in_(trip_ids)).all()
            if trip_ids else []
        )
        shared = [t for t in trips if t.is_shared]
        individual = [t for t in trips if not t.is_shared]

        def avg(vals: List[float]) -> float:
            return round(sum(vals) / len(vals), 2) if vals else 0.0

        total_dist = sum(t.total_distance_km or 0 for t in trips)
        total_dur = sum(t.total_duration_min or 0 for t in trips)
        total_fuel = sum(t.fuel_l or 0 for t in trips)
        fuel_saved = sum(t.fuel_saved_l or 0 for t in trips)
        co2_saved = sum(t.co2_saved_kg or 0 for t in trips)

        if status_map is None:
            status_map = {r.id: r.status for r in self.requests}
        completed = sum(1 for s in status_map.values() if s == "Assigned")
        batching_rate = round(
            (len(shared) / len(trips) * 100.0), 1
        ) if trips else 0.0
        avg_delay_min = avg([t.max_delay_min or 0 for t in trips])

        return {
            "trips": len(trips),
            "shared_trips": len(shared),
            "individual_trips": len(individual),
            "batching_rate_pct": batching_rate,
            "total_distance_km": round(total_dist, 2),
            "avg_distance_km": avg([t.total_distance_km or 0 for t in trips]),
            "avg_shared_distance_km": avg([t.total_distance_km or 0 for t in shared]),
            "avg_individual_distance_km": avg(
                [t.total_distance_km or 0 for t in individual]),
            "total_travel_time_min": round(total_dur, 1),
            "avg_travel_time_min": avg([t.total_duration_min or 0 for t in trips]),
            "total_fuel_l": round(total_fuel, 2),
            "avg_fuel_l": avg([t.fuel_l or 0 for t in trips]),
            "fuel_saved_l": round(fuel_saved, 2),
            "co2_emitted_kg": round(total_fuel * CO2_FACTOR, 2),
            "co2_saved_kg": round(co2_saved, 2),
            "co2_reduction_vs_internal_baseline_pct": round(
                (co2_saved / (co2_saved + total_fuel * CO2_FACTOR) * 100.0), 1
            ) if co2_saved > 0 else 0.0,
            "avg_utilization_pct": avg([t.utilization_pct or 0 for t in trips]),
            "avg_waiting_min": avg([t.max_delay_min or 0 for t in trips]),
            "avg_delay_min": avg_delay_min,
            "avg_shared_waiting_min": avg([t.max_delay_min or 0 for t in shared]),
            "avg_optimization_score": avg([t.optimization_score or 0 for t in trips]),
            "distance_saved_km": round(sum(t.distance_saved_km or 0 for t in trips), 2),
            "matrix_google": sum(1 for t in trips if t.matrix_source == "google_maps"),
            "matrix_haversine": sum(1 for t in trips
                                    if t.matrix_source == "haversine_fallback"),
            "requests_completed": completed,
            "requests_failed": len(self.requests) - completed,
        }

    def driver_metrics(self, db: Session, trip_ids: List[int]) -> Dict[str, Any]:
        trips = db.query(Trip).filter(Trip.id.in_(trip_ids)).all() if trip_ids else []
        used = {t.driver_id for t in trips if t.driver_id}
        total_drivers = db.query(Driver).count()
        trips_per_driver: Dict[int, int] = {}
        for t in trips:
            if t.driver_id:
                trips_per_driver[t.driver_id] = trips_per_driver.get(t.driver_id, 0) + 1
        per = list(trips_per_driver.values())
        return {
            "fleet_size": total_drivers,
            "drivers_used": len(used),
            "driver_pool_utilization_pct": round(
                len(used) / max(total_drivers, 1) * 100.0, 1),
            "avg_trips_per_used_driver": round(
                sum(per) / len(per), 2) if per else 0.0,
            "max_trips_on_driver": max(per) if per else 0,
        }

    def batch_metrics(self, db: Session) -> Dict[str, Any]:
        compatible = (
            db.query(DMFEBatch)
            .filter(DMFEBatch.decision == "Compatible")
            .all()
        )
        scores = [b.compatibility_score for b in compatible]
        sizes = [
            len(json_loads(b.request_ids_json, []) or []) for b in compatible
        ]
        if scores:
            mean = sum(scores) / len(scores)
            var = sum((s - mean) ** 2 for s in scores) / len(scores)
        else:
            mean, var = 0.0, 0.0
        return {
            "shared_batches_created": len(scores),
            "avg_compatibility_score": round(mean, 2),
            "std_compatibility_score": round(var ** 0.5, 2),
            "min_compatibility_score": round(min(scores), 2) if scores else 0.0,
            "max_compatibility_score": round(max(scores), 2) if scores else 0.0,
            "avg_requests_per_batch": round(
                sum(sizes) / len(sizes), 2) if sizes else 0.0,
            "max_requests_per_batch": max(sizes) if sizes else 0,
        }

    def pair_score_distribution(
        self, db: Session, max_pairs: int = 60000
    ) -> Dict[str, Any]:
        calc = CompatibilityCalculator()
        r = self.requests
        scores: List[float] = []
        n = len(r)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = r[i], r[j]
                if haversine(a.pickup_lat, a.pickup_lng,
                              b.pickup_lat, b.pickup_lng) > 5.0:
                    continue
                try:
                    res = calc.compute([a, b], db)
                    scores.append(res.compatibility_score)
                except Exception:
                    continue
                if len(scores) >= max_pairs:
                    break
            if len(scores) >= max_pairs:
                break
        if scores:
            mean = sum(scores) / len(scores)
            var = sum((s - mean) ** 2 for s in scores) / len(scores)
            bins = [0] * 5
            for s in scores:
                bins[min(int(s // 20), 4)] += 1
        else:
            mean, var = 0.0, 0.0
            bins = [0] * 5
        return {
            "pairs_evaluated": len(scores),
            "mean": round(mean, 2),
            "std": round(var ** 0.5, 2),
            "min": round(min(scores), 2) if scores else 0.0,
            "max": round(max(scores), 2) if scores else 0.0,
            "histogram_0_20": bins[0],
            "histogram_20_40": bins[1],
            "histogram_40_60": bins[2],
            "histogram_60_80": bins[3],
            "histogram_80_100": bins[4],
        }

    def compute_baseline(self, db: Session) -> Dict[str, Any]:
        type_stats = self._fleet_type_stats(db)
        total_km = 0.0
        total_fuel = 0.0
        utils: List[float] = []
        direct_times_min: List[float] = []

        t0 = time.perf_counter()
        for r in self.requests:
            km = haversine(r.pickup_lat, r.pickup_lng,
                           r.drop_lat, r.drop_lng) * ROAD_FACTOR
            mileage, capacity = type_stats.get(
                (r.vehicle_type or "").strip().lower(), (20.0, 3.0))
            total_km += km
            total_fuel += km / max(mileage, 1.0)
            utils.append((r.demand or 1) / max(capacity, 1) * 100.0)
            direct_times_min.append(km / AVG_SPEED_KMH * 60.0)
        processing_s = time.perf_counter() - t0

        return {
            "total_distance_km": round(total_km, 2),
            "total_fuel_l": round(total_fuel, 2),
            "total_co2_kg": round(total_fuel * CO2_FACTOR, 2),
            "avg_utilization_pct": round(
                sum(utils) / len(utils), 2) if utils else 0.0,
            "avg_travel_time_min": round(
                sum(direct_times_min) / len(direct_times_min), 2
            ) if direct_times_min else 0.0,
            "avg_waiting_min": 0.0,
            "processing_total_s": round(processing_s, 4),
            "avg_processing_ms": round(processing_s * 1000.0
                                       / max(len(self.requests), 1), 4),
            "requests_completed": len(self.requests),
            "requests_failed": 0,
            "trips": len(self.requests),
            "shared_trips": 0,
            "individual_trips": len(self.requests),
        }

    @staticmethod
    def _fleet_type_stats(db: Session) -> Dict[str, Tuple[float, float]]:
        stats: Dict[str, List[Tuple[float, float]]] = {}
        for v in db.query(Vehicle).all():
            key = (v.vehicle_type or "").strip().lower()
            stats.setdefault(key, []).append((v.mileage_kmpl or 15.0, v.capacity or 1))
        out: Dict[str, Tuple[float, float]] = {}
        for key, vals in stats.items():
            mileage = sum(x[0] for x in vals) / len(vals)
            capacity = sum(x[1] for x in vals) / len(vals)
            out[key] = (mileage, capacity)
        return out


# ─────────────────────────────────────────────────────────────────────────────
# Top-level experiment orchestration
# ─────────────────────────────────────────────────────────────────────────────

def run_workload(
    workload: int, mode: Optional[str] = None, seed: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run one complete evaluation workload.

    `mode` overrides the A-DMFE operating mode ("adaptive" | "static")
    per call; when omitted the module-level ADMFE_MODE env value is used.
    `seed` picks a deterministic repeat; defaults to 1000 + workload.
    """
    exp = ExperimentDB()
    db = SessionLocal()
    try:
        exp.reset_schema()
        effective_seed = seed if seed is not None else 1000 + workload
        rng = random.Random(effective_seed)
        effective_config = dict(SYSTEM_CONFIG)
        if mode is not None:
            effective_config["admfe.mode"] = mode
        exp.seed_system_config_with(db, effective_config)
        exp.seed_fleet(db, rng)

        runner = WorkloadRunner(workload, seed=effective_seed)
        runner.install_probes()
        requests = runner.generate_requests(db)
        dist = {"ride": 0, "food": 0, "parcel": 0}
        for r in requests:
            dist[r.request_type] = dist.get(r.request_type, 0) + 1

        # single-pass dispatch (the pipeline's designed behaviour)
        out = runner.run_pipeline(db)
        status_map = {r.id: r.status for r in requests}
        pipeline_s = out["wall_s"]
        timing_single = {
            "pipeline_total_s": round(pipeline_s, 3),
            "avg_processing_ms_per_request": round(
                out["wall_s"] * 1000.0 / max(workload, 1), 2),
            "sql_queries": out.get("sql_queries", 0),
            "batch_formation_total_s": round(runner.batch_probe.total_s, 3),
            "batch_formation_avg_ms": round(runner.batch_probe.avg_ms(), 2),
            "batch_formation_calls": len(runner.batch_probe.times),
            "route_optimization_total_s": round(runner.optimize_probe.total_s, 3),
            "route_optimization_avg_ms": round(runner.optimize_probe.avg_ms(), 2),
            "route_optimization_calls": len(runner.optimize_probe.times),
            "driver_selection_total_s": round(runner.select_probe.total_s, 3),
            "driver_selection_avg_ms": round(runner.select_probe.avg_ms(), 2),
            "driver_selection_calls": len(runner.select_probe.times),
            "decision_total_s": round(runner.decision_probe.total_s, 3),
            "decision_calls": len(runner.decision_probe.times),
            "persistence_total_s": round(runner.persist_probe.total_s, 3),
            "persistence_calls": len(runner.persist_probe.times),
            "learning_total_s": round(runner.learn_probe.total_s, 3),
            "learning_calls": len(runner.learn_probe.times),
            "dispatch_total_s": round(runner.dispatch_probe.total_s, 3),
            "dispatch_calls": len(runner.dispatch_probe.times),
            "stage_share_pct": {
                "batch_formation": stage_share(runner.batch_probe.total_s, pipeline_s),
                "route_optimization": stage_share(runner.optimize_probe.total_s, pipeline_s),
                "driver_selection": stage_share(runner.select_probe.total_s, pipeline_s),
                "decision": stage_share(runner.decision_probe.total_s, pipeline_s),
                "persistence": stage_share(runner.persist_probe.total_s, pipeline_s),
                "learning": stage_share(runner.learn_probe.total_s, pipeline_s),
                "dispatch": stage_share(runner.dispatch_probe.total_s, pipeline_s),
            },
        }

        metrics = runner.collect_metrics(db, out["trip_ids"], status_map)
        driver_m = runner.driver_metrics(db, out["trip_ids"])
        batch_m = runner.batch_metrics(db)
        pair_m = runner.pair_score_distribution(db)
        baseline = runner.compute_baseline(db)

        # simulated full-day operation: complete trips, re-dispatch until done
        wave_out = runner.run_waves(db)
        all_trip_ids = out["trip_ids"] + runner.wave_trip_ids
        wave_trips = (
            db.query(Trip).filter(Trip.id.in_(all_trip_ids)).all()
            if all_trip_ids else []
        )
        wave_dist = sum(t.total_distance_km or 0 for t in wave_trips)
        wave_fuel = sum(t.fuel_l or 0 for t in wave_trips)
        wave_completed = sum(
            1 for r in requests if r.status in ("Assigned", "Completed")
        )
        waves_metrics = {
            "waves": wave_out["waves"],
            "trips_total": len(runner.wave_trip_ids),
            "total_distance_km": round(wave_dist, 2),
            "total_fuel_l": round(wave_fuel, 2),
            "total_co2_kg": round(wave_fuel * CO2_FACTOR, 2),
            "requests_completed": wave_completed,
            "requests_failed": len(requests) - wave_completed,
            "completion_rate_pct": round(wave_completed / len(requests) * 100.0, 1),
            "sql_queries_total": runner.wave_sql_queries,
        }

        return {
            "workload": workload,
            "seed": runner.seed,
            "request_mix": dist,
            "fleet_size": FLEET_SIZE,
            "config": dict(effective_config),
            "single_pass": {
                "requests_processed": out["result"].requests_processed,
                "shared_trips": out["result"].shared_trips,
                "individual_trips": out["result"].individual_trips,
                "assignments_created": out["result"].assignments_created,
                "unassigned_count": len(out["result"].unassigned),
                "unassigned_reasons": [
                    u["reason"] for u in out["result"].unassigned][:5],
                "trips": metrics,
                "drivers": driver_m,
                "batches": batch_m,
            },
            "compatibility_distribution": pair_m,
            "baseline": baseline,
            "waves": waves_metrics,
            "timing": timing_single,
        }
    finally:
        db.close()


def run_learning_workload(
    workload: int,
    learning: bool = True,
    mode: str = "adaptive",
    max_days: int = 5,
    execution: str = "scatter",
) -> Dict[str, Any]:
    """
    Closed-loop workload for the learning A/B (Phase 4/4.1).

    Simulates consecutive operating days with the REAL trip lifecycle:
    dispatch → trip creation → simulated execution (actuals written into
    the trip) → complete_trip (learning hook).  No status flips.  Stale
    Pending requests roll off as Failed at end of day.  Both arms run the
    same fixed number of days with the same per-day seeds, so any
    difference is attributable to the learning loop.

    ``execution`` selects the execution model: "scatter" (default) or
    "delay_x1.4" (Step 5 feed-forward scenario).
    """
    from app.dmfe.adaptive.learning import LearningEngine, REFIT_INTERVAL

    exp = ExperimentDB()
    db = SessionLocal()
    try:
        exp.reset_schema()
        rng = random.Random(1000 + workload)
        effective_config = dict(SYSTEM_CONFIG)
        effective_config["admfe.mode"] = mode
        effective_config["admfe.learning_enabled"] = (
            "true" if learning else "false"
        )
        exp.seed_system_config_with(db, effective_config)
        exp.seed_fleet(db, rng)

        runner = WorkloadRunner(workload, seed=1000 + workload)
        runner.execution = execution
        runner.install_probes()

        dist = {"ride": 0, "food": 0, "parcel": 0}
        all_requests: List[SimulationRequest] = []
        all_trip_ids: List[int] = []
        per_day: List[Dict[str, Any]] = []
        timing_single: Dict[str, Any] = {}
        day1_metrics: Dict[str, Any] = {}

        for day in range(1, max_days + 1):
            runner.seed = 1000 + workload + day  # per-day variation (deterministic)
            requests = runner.generate_requests(db)
            for r in requests:
                dist[r.request_type] = dist.get(r.request_type, 0) + 1
            all_requests.extend(requests)

            out = runner.run_pipeline(db)
            day_trip_ids = list(out["trip_ids"])
            if day == 1:
                status_map = {r.id: r.status for r in requests}
                pipeline_s = out["wall_s"]
                timing_single = {
                    "pipeline_total_s": round(pipeline_s, 3),
                    "avg_processing_ms_per_request": round(
                        out["wall_s"] * 1000.0 / max(workload, 1), 2),
                    "sql_queries": out.get("sql_queries", 0),
                    "batch_formation_total_s": round(
                        runner.batch_probe.total_s, 3),
                    "batch_formation_avg_ms": round(runner.batch_probe.avg_ms(), 2),
                    "batch_formation_calls": len(runner.batch_probe.times),
                    "route_optimization_total_s": round(
                        runner.optimize_probe.total_s, 3),
                    "route_optimization_avg_ms": round(runner.optimize_probe.avg_ms(), 2),
                    "route_optimization_calls": len(runner.optimize_probe.times),
                    "driver_selection_total_s": round(runner.select_probe.total_s, 3),
                    "driver_selection_avg_ms": round(runner.select_probe.avg_ms(), 2),
                    "driver_selection_calls": len(runner.select_probe.times),
                    "decision_total_s": round(runner.decision_probe.total_s, 3),
                    "decision_calls": len(runner.decision_probe.times),
                    "persistence_total_s": round(runner.persist_probe.total_s, 3),
                    "persistence_calls": len(runner.persist_probe.times),
                    "learning_total_s": round(runner.learn_probe.total_s, 3),
                    "learning_calls": len(runner.learn_probe.times),
                    "dispatch_total_s": round(runner.dispatch_probe.total_s, 3),
                    "dispatch_calls": len(runner.dispatch_probe.times),
                    "stage_share_pct": {
                        "batch_formation": stage_share(runner.batch_probe.total_s, pipeline_s),
                        "route_optimization": stage_share(runner.optimize_probe.total_s, pipeline_s),
                        "driver_selection": stage_share(runner.select_probe.total_s, pipeline_s),
                        "decision": stage_share(runner.decision_probe.total_s, pipeline_s),
                        "persistence": stage_share(runner.persist_probe.total_s, pipeline_s),
                        "learning": stage_share(runner.learn_probe.total_s, pipeline_s),
                        "dispatch": stage_share(runner.dispatch_probe.total_s, pipeline_s),
                    },
                }
                day1_metrics = {
                    "trips": runner.collect_metrics(db, out["trip_ids"], status_map),
                    "drivers": runner.driver_metrics(db, out["trip_ids"]),
                    "batches": runner.batch_metrics(db),
                    "requests_processed": out["result"].requests_processed,
                    "shared_trips": out["result"].shared_trips,
                    "individual_trips": out["result"].individual_trips,
                    "assignments_created": out["result"].assignments_created,
                    "unassigned_count": len(out["result"].unassigned),
                }

            # close the loop: simulated execution + REAL completion (learning
            # hook fires), then re-dispatch until the queue drains
            waves = 0
            for _ in range(MAX_WAVES):
                runner.complete_trips_real(db)
                pending = (
                    db.query(SimulationRequest)
                    .filter(SimulationRequest.status == "Pending")
                    .count()
                )
                if pending == 0:
                    break
                wave_out = runner.run_pipeline(db)
                day_trip_ids.extend(wave_out["trip_ids"])
                waves += 1
                if not wave_out["trip_ids"]:
                    break

            # day-end rolloff: stale Pending requests fail
            db.query(SimulationRequest).filter(
                SimulationRequest.status == "Pending"
            ).update({"status": "Failed"}, synchronize_session=False)
            db.commit()

            # per-day mean prediction error for the completed trips —
            # both the route-level prediction the learning engine ingests
            # and the compat-level estimate the corridor multiplier scales
            day_trips = (
                db.query(Trip).filter(Trip.id.in_(day_trip_ids)).all()
                if day_trip_ids else []
            )
            delay_errors = []
            compat_errors = []
            for t in day_trips:
                pred = LearningEngine._estimated_delay(db, t)
                delay_errors.append(float(t.max_delay_min or 0.0) - pred)
                batch = LearningEngine._batch_row(db, t)
                cpred = float(batch.estimated_delay_min or 0.0) if batch else 0.0
                compat_errors.append(abs(float(t.max_delay_min or 0.0) - cpred))
            mean_delay_error = (
                round(sum(delay_errors) / len(delay_errors), 2)
                if delay_errors else 0.0
            )
            mean_compat_error = (
                round(sum(compat_errors) / len(compat_errors), 2)
                if compat_errors else 0.0
            )

            all_trip_ids.extend(day_trip_ids)
            day_info: Dict[str, Any] = {
                "day": day,
                "trips": len(day_trip_ids),
                "waves": waves,
                "mean_delay_error_min": mean_delay_error,
                "mean_compat_delay_error_min": mean_compat_error,
            }
            if learning:
                state = LearningEngine.load_state(db)
                day_info["outcomes"] = state["outcomes"]["count"]
                day_info["refit_count"] = state.get("last_refit_count", 0)
                day_info["corridor_delay_multipliers"] = dict(
                    LearningEngine.corridor_multipliers(db)
                )
                day_info["corridor_utilization_bias"] = dict(
                    LearningEngine.corridor_utilization_bias(db)
                )
            per_day.append(day_info)

        # aggregate metrics over the whole multi-day run
        trips = (
            db.query(Trip).filter(Trip.id.in_(all_trip_ids)).all()
            if all_trip_ids else []
        )
        wave_dist = sum(t.total_distance_km or 0 for t in trips)
        wave_fuel = sum(t.fuel_l or 0 for t in trips)
        wave_completed = sum(
            1 for r in all_requests if r.status in ("Assigned", "Completed")
        )
        refit_day = next(
            (d["day"] for d in per_day if learning and d["refit_count"] >= REFIT_INTERVAL),
            None,
        )
        waves_metrics = {
            "days": len(per_day),
            "refit_fired_day": refit_day,
            "trips_total": len(all_trip_ids),
            "total_distance_km": round(wave_dist, 2),
            "total_fuel_l": round(wave_fuel, 2),
            "total_co2_kg": round(wave_fuel * CO2_FACTOR, 2),
            "requests_completed": wave_completed,
            "requests_failed": len(all_requests) - wave_completed,
            "completion_rate_pct": round(
                wave_completed / len(all_requests) * 100.0, 1
            ),
            "sql_queries_total": runner.wave_sql_queries,
            "learning_total_s": round(runner.learn_probe.total_s, 3),
            "learning_calls": len(runner.learn_probe.times),
            "per_day": per_day,
        }

        learning_m = None
        if learning:
            learning_m = {
                "state_summary": LearningEngine.summary(db),
                "drivers_tracked": len(LearningEngine.driver_outcome_summary(db)),
            }

        return {
            "workload": workload,
            "seed": runner.seed,
            "request_mix": dist,
            "fleet_size": FLEET_SIZE,
            "config": dict(effective_config),
            "single_pass": day1_metrics,
            "waves": waves_metrics,
            "timing": timing_single,
            "learning": learning_m,
        }
    finally:
        db.close()


def run_all_workloads(workloads: Optional[List[int]] = None) -> Dict[int, Dict[str, Any]]:
    workloads = list(workloads or WORKLOADS)
    results_file = os.path.join(RESULTS_DIR, "experiments.json")
    results: Dict[int, Dict[str, Any]] = {}
    if os.path.exists(results_file):
        try:
            with open(results_file) as fh:
                results = {int(k): v for k, v in json.load(fh).items()}
        except Exception:
            results = {}

    os.makedirs(RESULTS_DIR, exist_ok=True)
    for n in workloads:
        if n in results:
            print(f"[eval] workload={n} already done — skipping", flush=True)
            continue
        print(f"[eval] workload={n} ...", flush=True)
        results[n] = run_workload(n)
        print(f"[eval] workload={n} done", flush=True)
        with open(results_file, "w") as fh:
            json.dump({str(k): v for k, v in results.items()}, fh, indent=2)
    return results


if __name__ == "__main__":
    run_all_workloads()
