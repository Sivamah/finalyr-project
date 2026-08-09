"""
A-DMFE Module 8 — Learning Component (lightweight, no deep learning)
===================================================================
Closed-loop outcome-driven adaptation.  After every completed trip the
module ingests the ACTUAL outcome recorded on the Trip row:

  - actual delay        (trip.max_delay_min)
  - fuel used           (trip.fuel_l)
  - customer waiting    (trip.max_delay_min + driver ETA at dispatch)
  - driver utilisation  (trip.utilization_pct)
  - batch success       (status Completed + delay vs batch estimate)

Predicted-vs-actual residuals are logged per trip into bounded ring
buffers (separate ``delay`` and ``utilization`` tracks, capped at
RESIDUAL_BUFFER_SIZE) keyed by corridor (sorted request-type mix, e.g.
``food|ride``):

  - delay residual       = trip.max_delay_min − batch.estimated_delay_min
  - utilization residual = trip.utilization_pct − batch.predicted_utilization_pct

Every REFIT_INTERVAL completed trips (and only then) the module refits a
per-corridor correction factor for each signal from its ring buffer
(ratio of sums, clamped to [0.5, 2.0], min CORRIDOR_SAMPLES per
corridor, drift-damped so later refits step halfway toward the target):

  - corridor_multipliers           (delay)      — feeds Compatibility
                                                  scoring + driver ETA
  - corridor_utilization_bias      (utilization) — feeds capacity/weight
                                                  pressure (via context)
  - corridor_fuel_multiplier       (fuel)       — predicted fuel vs fleet
                                                  benchmark, per corridor
  - corridor_co2_multiplier        (CO2)        — emissions ratio per
                                                  corridor (CO2 ∝ fuel)
  - corridor_delay_residual_mean   (delay EMA)  — per-corridor mean
                                                  prediction error

All refits are gated together by the single ``admfe.refit_enabled``
config flag (default on).

From the per-trip residuals the module also derives bounded (±15%)
weight corrections that the Adaptive Weight Generator applies on top of
the context perturbation:

  - realized delay exceeds the prediction → raise time & route weight
    pressure (delay is under-priced)
  - realized utilization runs BELOW the prediction → raise capacity
    weight pressure (predicted utilisation is over-optimistic)
  - realized fuel runs ABOVE the fleet benchmark → raise route weight
    pressure (fuel is under-priced → route overlap matters more)

Per-driver outcome summaries (delay residual, utilisation, fuel,
completion) feed a per-corridor driver-quality map used by the context
layer to adjust the workload signal for that service corridor.

All state is persisted as JSON in the existing SystemConfig table under
key ``admfe.learning_state`` — no schema change, PostgreSQL untouched.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.json_utils import json_loads
from app.db.models import SimulationRequest, SystemConfig, Trip, Vehicle
from app.dmfe.adaptive._util import _clamp, _clamp01
from app.dmfe.compatibility import get_config_value
from app.dmfe.models import DMFEBatch

logger = logging.getLogger(__name__)

STATE_KEY = "admfe.learning_state"
LEARNING_RATE = 0.05          # EMA / update step
MAX_BIAS = 0.15               # learned correction bounds
MAX_BIAS_KEY = "admfe.learning_max_bias"
LEARNING_ENABLED_KEY = "admfe.learning_enabled"

# ── residual refit (delay + utilization + fuel + co2) ───────────────────────
RESIDUAL_BUFFER_SIZE = 200    # max kept residuals per signal — sized ≥ 1 refit window (200)
                              # so no sample needed for a refit is ever evicted
REFIT_INTERVAL = 200          # refit corridor factors every N completed trips
MIN_CORRIDOR_SAMPLES = 10     # per-corridor min samples before a factor is emitted
CORRIDOR_FACTOR_MIN = 0.5     # clamp bounds for refitted correction factors
CORRIDOR_FACTOR_MAX = 2.0
REFIT_ENABLED_KEY = "admfe.refit_enabled"
REFIT_DAMPING = 0.5           # step toward the target ratio per refit (anti-oscillation)
CO2_FACTOR = 2.3              # kg CO2 per litre of fuel (matches optimizer.py)
FLEET_MILEAGE_FALLBACK = 15.0 # km/l used when the fleet benchmark is unknown
DRIVER_SUMMARY_CAP = 500      # max per-driver summaries kept (LRU-ish: oldest dropped)
QUALITY_CAP = 200             # max corridors in the driver-quality map

EMPTY_STATE: Dict[str, Any] = {
    "version": 3,
    "outcomes": {
        "count": 0,
        "shared": 0,
        "individual": 0,
        "completed": 0,
        "failed": 0,
        "avg_delay_min": 0.0,
        "avg_util_pct": 50.0,
        "avg_fuel_l": 0.0,
        "avg_duration_min": 0.0,
        "delay_error": 0.0,          # (actual − estimated)/max_delay
        "delay_bias_min": 0.0,       # EMA of (actual − predicted) delay, minutes
        "util_bias_pp": 0.0,         # EMA of (actual − predicted) utilization, p.p.
        "fuel_ratio": 1.0,           # EMA of (actual fuel / expected fuel)
    },
    "factor_bias": {
        "pickup": 0.0, "route": 0.0,
        "time": 0.0, "capacity": 0.0, "priority": 0.0,
    },
    "corridor": {},                  # "type_a|type_b" → {count, success, avg_delay_min}
    "residuals": {                   # bounded ring buffers, tagged by signal
        "delay": [],
        "utilization": [],
        "fuel": [],
        "co2": [],
    },
    "corridor_multipliers": {},      # "type_a|type_b" → delay correction factor
    "corridor_utilization_bias": {},  # "type_a|type_b" → utilization correction factor
    "corridor_fuel_multiplier": {},  # "type_a|type_b" → fuel correction factor
    "corridor_co2_multiplier": {},   # "type_a|type_b" → CO2 correction factor
    "corridor_delay_residual_mean": {},  # "type_a|type_b" → EMA delay error (min)
    "corridor_driver_quality": {},   # "type_a|type_b" → {driver_id, quality, samples}
    "driver_outcome_summary": {},    # driver_id → {trips, avg_delay_residual_min,
                                     #              avg_util_pct, avg_fuel_l,
                                     #              completion_rate, last_updated}
    "last_refit_count": 0,
    "last_updated": None,
}


def _ema(old: float, new: float, eta: float = LEARNING_RATE) -> float:
    return (1.0 - eta) * old + eta * new


class LearningEngine:
    """Outcome ingestion + weight-correction synthesis (stateless core)."""

    # ── state persistence ───────────────────────────────────────────────────

    @staticmethod
    def load_state(db: Session) -> Dict[str, Any]:
        state = json.loads(json.dumps(EMPTY_STATE))
        try:
            db.flush()  # see pending writes even with autoflush disabled
            row = db.query(SystemConfig).filter(
                SystemConfig.key == STATE_KEY
            ).first()
            if row and row.value:
                stored = json.loads(row.value)
                for k, v in stored.items():
                    if k in state:
                        state[k] = v
        except Exception:
            logger.warning("A-DMFE learning state parse failed — using empty state")
        return state

    @staticmethod
    def save_state(db: Session, state: Dict[str, Any]) -> None:
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        try:
            db.flush()  # expose any pending writes to the upsert below
            row = db.query(SystemConfig).filter(
                SystemConfig.key == STATE_KEY
            ).first()
            payload = json.dumps(state)
            if row:
                row.value = payload
            else:
                db.add(SystemConfig(
                    category="ai_rules", key=STATE_KEY,
                    value=payload, data_type="json",
                ))
        except Exception as exc:
            logger.warning("A-DMFE learning state save failed: %s", exc)

    @staticmethod
    def learning_enabled(db: Session) -> bool:
        try:
            raw = get_config_value(db, LEARNING_ENABLED_KEY)
            if raw is not None:
                return str(raw).strip().lower() not in ("false", "0", "off")
        except Exception:
            pass
        return True

    @staticmethod
    def max_bias(db: Session) -> float:
        try:
            raw = get_config_value(db, MAX_BIAS_KEY)
            if raw is not None:
                return _clamp(float(raw), 0.0, 0.5)
        except Exception:
            pass
        return MAX_BIAS

    # ── outcome ingestion ───────────────────────────────────────────────────

    def record_trip_outcome(
        self, db: Session, trip: Trip, commit: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Fold one completed trip into the learning state (no-op if disabled)."""
        if not self.learning_enabled(db):
            return None
        try:
            if not self._has_actuals(trip):
                # Safety: stale/auto-completed trips carry no realized
                # outcomes — ingesting them would poison the bias EMAs
                # and corridor statistics with zeros.
                return None
            state = self.load_state(db)
            corridor = LearningEngine._trip_corridor(db, trip)
            batch = LearningEngine._batch_row(db, trip)
            self._update_outcomes(state, db, trip, corridor, batch)
            self._update_corridor(state, db, trip, corridor)
            self._update_driver(state, db, trip, corridor, batch)
            self._maybe_refit(state, db)
            self._update_bias(state, trip)
            self.save_state(db, state)
            if commit:
                db.commit()
            return state
        except Exception as exc:
            logger.warning("A-DMFE outcome ingestion failed: %s", exc)
            return None

    @staticmethod
    def _has_actuals(trip: Trip) -> bool:
        """
        A trip is only ingested when it carries realized outcomes.

        The Trip model defaults every outcome column to 0.0, so auto-
        created / never-dispatched rows are indistinguishable from real
        zero-outcome trips by None alone.  Such rows additionally lack a
        batch linkage — skip anything that has no batch AND no non-zero
        actual, otherwise the bias EMAs and corridor stats would be
        poisoned by zero-filled rows.
        """
        has_any = any(
            getattr(trip, field, None) is not None
            for field in ("max_delay_min", "utilization_pct", "fuel_l")
        )
        if not has_any:
            return False
        all_zero = all(
            float(getattr(trip, field, 0.0) or 0.0) == 0.0
            for field in ("max_delay_min", "utilization_pct", "fuel_l")
        )
        if all_zero and trip.batch_id is None:
            return False
        return True

    # ── prediction lookups (recover the EXACT dispatch-time prediction) ──────
    #
    # Phase 4.1: the pipeline snapshots the route-level predictions into the
    # batch factor details under ``details["predicted"]`` when the trip is
    # created (see pipeline._record_dispatch).  The lookups below prefer
    # that snapshot, then fall back to the persisted batch columns, so the
    # prediction used for dispatch is recoverable here even after real
    # execution actuals overwrite the Trip outcome columns.

    @staticmethod
    def _batch_row(db: Session, trip: Trip) -> Optional[DMFEBatch]:
        """The trip's batch row in one query (shared by all lookups)."""
        if trip.batch_id is None:
            return None
        try:
            return (
                db.query(DMFEBatch)
                .filter(DMFEBatch.id == trip.batch_id)
                .first()
            )
        except Exception:
            return None

    @staticmethod
    def _prediction_snapshot(batch: Optional[DMFEBatch]) -> Dict[str, float]:
        """Route-level prediction snapshot written at dispatch time."""
        if batch is None:
            return {}
        try:
            details = json_loads(batch.factor_details_json or "{}", {})
            snap = details.get("predicted") if isinstance(details, dict) else None
            return snap if isinstance(snap, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _estimated_delay(
        db: Session, trip: Trip, batch: Optional[DMFEBatch] = None
    ) -> float:
        """Predicted delay (minutes) used for the trip at dispatch time.

        Preference: route snapshot → batch.estimated_delay_min → 0.0.
        """
        if trip.batch_id is None:
            return 0.0
        try:
            batch = batch if batch is not None else LearningEngine._batch_row(db, trip)
            if batch is None:
                return 0.0
            snap = LearningEngine._prediction_snapshot(batch)
            if float(snap.get("delay_min") or 0.0) > 0.0:
                return float(snap["delay_min"])
            return float(batch.estimated_delay_min or 0.0)
        except Exception:
            return 0.0

    @staticmethod
    def _estimated_utilization(
        db: Session, trip: Trip, batch: Optional[DMFEBatch] = None
    ) -> float:
        """Predicted vehicle utilization (%) used for the trip at dispatch.

        Preference: route snapshot → batch.predicted_utilization_pct → the
        formation-time capacity factor → 0.0.
        """
        if trip.batch_id is None:
            return 0.0
        try:
            batch = batch if batch is not None else LearningEngine._batch_row(db, trip)
            if batch is None:
                return 0.0
            snap = LearningEngine._prediction_snapshot(batch)
            if float(snap.get("utilization_pct") or 0.0) > 0.0:
                return float(snap["utilization_pct"])
            predicted = float(batch.predicted_utilization_pct or 0.0)
            if predicted > 0.0:
                return predicted
            details = json_loads(batch.factor_details_json or "{}", {})
            if isinstance(details, dict):
                cap_util = details.get("capacity_utilization_pct")
                if isinstance(cap_util, (int, float)) and float(cap_util) > 0.0:
                    return float(cap_util)
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _expected_fuel(
        db: Session,
        trip: Trip,
        batch: Optional[DMFEBatch] = None,
    ) -> Optional[float]:
        """Expected fuel (L) for the trip, or None.

        Preference: the dispatch-time route prediction (snapshot on the
        batch) → the fleet-benchmark expectation (trip km ÷ fleet mean
        mileage).  The benchmark falls back to a constant when no vehicles
        are seeded.  Skipped when the trip has no distance and no snapshot.
        """
        if batch is None and trip.batch_id is not None:
            batch = LearningEngine._batch_row(db, trip)
        snap = LearningEngine._prediction_snapshot(batch)
        if float(snap.get("fuel_l") or 0.0) > 0.0:
            return float(snap["fuel_l"])
        km = float(
            getattr(trip, "distance_km", None)
            or getattr(trip, "executed_trip_km", None)
            or getattr(trip, "total_distance_km", None)
            or 0.0
        )
        if km <= 0.0:
            return None
        try:
            rows = (
                db.query(Vehicle)
                .filter(Vehicle.is_active.is_(True))
                .all()
            )
            mileages = [
                float(v.mileage_kmpl or FLEET_MILEAGE_FALLBACK) for v in rows
            ]
            if not mileages:
                mileage = FLEET_MILEAGE_FALLBACK
            else:
                mileage = sum(mileages) / len(mileages)
        except Exception:
            mileage = FLEET_MILEAGE_FALLBACK
        return km / max(mileage, 1.0)

    @staticmethod
    def _trip_corridor(db: Session, trip: Trip) -> str:
        """Corridor key: sorted request-type mix of the trip, e.g. 'food|ride'."""
        ids = json_loads(trip.request_ids_json, [])
        if not ids:
            return "unknown"
        try:
            rows = (
                db.query(SimulationRequest)
                .filter(SimulationRequest.id.in_(ids))
                .all()
            )
        except Exception:
            rows = []
        types = sorted({(r.request_type or "ride").lower() for r in rows})
        return "|".join(types) if types else "unknown"

    @staticmethod
    def _log_residual(
        state: Dict[str, Any], tag: str,
        corridor: str, estimated: float, actual: float,
    ) -> None:
        """Append one predicted-vs-actual sample to the tagged ring buffer."""
        buf = state.setdefault("residuals", {"delay": [], "utilization": []})
        buf.setdefault(tag, []).append({
            "corridor": corridor,
            "estimated": round(float(estimated), 4),
            "actual": round(float(actual), 4),
        })
        del buf[tag][:-RESIDUAL_BUFFER_SIZE]

    @staticmethod
    def _update_outcomes(
        state: Dict[str, Any],
        db: Session,
        trip: Trip,
        corridor: str,
        batch: Optional[DMFEBatch] = None,
    ) -> None:
        o = state["outcomes"]
        o["count"] = int(o.get("count", 0)) + 1
        if trip.is_shared:
            o["shared"] = int(o.get("shared", 0)) + 1
        else:
            o["individual"] = int(o.get("individual", 0)) + 1
        if trip.status == "Completed":
            o["completed"] = int(o.get("completed", 0)) + 1
        else:
            o["failed"] = int(o.get("failed", 0)) + 1

        actual_delay = float(trip.max_delay_min or 0.0)
        util = float(trip.utilization_pct or 0.0)
        fuel = float(trip.fuel_l or 0.0)
        duration = float(trip.total_duration_min or 0.0)

        if o["count"] == 1:
            o["avg_delay_min"] = round(actual_delay, 2)
            o["avg_util_pct"] = round(util, 1)
            o["avg_fuel_l"] = round(fuel, 3)
            o["avg_duration_min"] = round(duration, 2)
        else:
            o["avg_delay_min"] = round(_ema(o.get("avg_delay_min", 0.0), actual_delay), 2)
            o["avg_util_pct"] = round(_ema(o.get("avg_util_pct", 50.0), util), 1)
            o["avg_fuel_l"] = round(_ema(o.get("avg_fuel_l", 0.0), fuel), 3)
            o["avg_duration_min"] = round(_ema(o.get("avg_duration_min", 0.0), duration), 2)

        # Predicted-vs-actual residuals — each signal is logged into its
        # OWN ring buffer so the refit grouping never mixes them.
        estimated_delay = LearningEngine._estimated_delay(db, trip, batch)
        estimated_util = LearningEngine._estimated_utilization(db, trip, batch)
        LearningEngine._log_residual(
            state, "delay", corridor, estimated_delay, actual_delay
        )
        LearningEngine._log_residual(
            state, "utilization", corridor, estimated_util, util
        )

        # Fuel / CO2 residuals against the dispatch-time fuel prediction
        # (or the fleet mileage benchmark); CO2 = fuel × 2.3 both sides so
        # the residual measures the same physical quantity (emissions).
        expected_fuel = LearningEngine._expected_fuel(db, trip, batch)
        if expected_fuel is not None and expected_fuel > 1e-6:
            ratio = fuel / expected_fuel
            if o["count"] == 1:
                o["fuel_ratio"] = round(ratio, 4)
            else:
                o["fuel_ratio"] = round(
                    _ema(float(o.get("fuel_ratio", 1.0)), ratio), 4
                )
            LearningEngine._log_residual(
                state, "fuel", corridor, round(expected_fuel, 4), round(fuel, 4)
            )
            co2_expected = expected_fuel * CO2_FACTOR
            co2_actual = fuel * CO2_FACTOR
            LearningEngine._log_residual(
                state, "co2", corridor, round(co2_expected, 4), round(co2_actual, 4)
            )

        # Bias-driving residual EMAs (first sample seeds directly so a single
        # bad trip is not diluted by the 0.05 EMA warm-up)
        if o["count"] == 1:
            o["delay_bias_min"] = round(actual_delay - estimated_delay, 3)
            o["util_bias_pp"] = round(util - estimated_util, 2)
        else:
            o["delay_bias_min"] = round(_ema(
                o.get("delay_bias_min", 0.0), actual_delay - estimated_delay
            ), 3)
            o["util_bias_pp"] = round(_ema(
                o.get("util_bias_pp", 0.0), util - estimated_util
            ), 2)

        # Delay error vs the batch-time estimate (kept for backward compat)
        max_delay = max(20.0, actual_delay + 1.0)
        error = (actual_delay - estimated_delay) / max_delay
        o["delay_error"] = round(_ema(o.get("delay_error", 0.0), error), 4)

    @staticmethod
    def _update_corridor(
        state: Dict[str, Any], db: Session, trip: Trip, corridor: str
    ) -> None:
        corr = state["corridor"].setdefault(corridor, {
            "count": 0, "success": 0.0, "avg_delay_min": 0.0,
        })
        corr["count"] = int(corr.get("count", 0)) + 1
        success = 1.0 if trip.status == "Completed" else 0.0
        delay = float(trip.max_delay_min or 0.0)
        if corr["count"] == 1:
            corr["success"] = round(success, 4)
            corr["avg_delay_min"] = round(delay, 2)
        else:
            corr["success"] = round(
                _ema(float(corr.get("success", 0.5)), success), 4
            )
            corr["avg_delay_min"] = round(
                _ema(float(corr.get("avg_delay_min", 0.0)), delay), 2
            )

    # ── per-driver learning (Step 6) ────────────────────────────────────────

    @staticmethod
    def _update_driver(
        state: Dict[str, Any],
        db: Session,
        trip: Trip,
        corridor: str,
        batch: Optional[DMFEBatch] = None,
    ) -> None:
        """Per-driver outcome summaries + per-corridor driver quality.

        Every completed trip folds its realized delay residual,
        utilisation and fuel into the driver's rolling summary; each
        corridor keeps the driver with the best rolling quality (quality
        = 0.7 × punctuality + 0.3 × utilisation).  The corridor map is
        consumed by the context layer to tune the workload signal.
        """
        if trip.driver_id is None:
            return
        driver_id = str(trip.driver_id)
        actual_delay = float(trip.max_delay_min or 0.0)
        estimated_delay = LearningEngine._estimated_delay(db, trip, batch)
        delay_res = round(actual_delay - estimated_delay, 3)
        util = float(trip.utilization_pct or 0.0)
        fuel = float(trip.fuel_l or 0.0)

        summaries = state.setdefault("driver_outcome_summary", {})
        s = summaries.setdefault(driver_id, {
            "trips": 0,
            "avg_delay_residual_min": 0.0,
            "avg_util_pct": 0.0,
            "avg_fuel_l": 0.0,
            "completion_rate": 1.0,
            "last_updated": None,
        })
        n = int(s.get("trips", 0))
        if n == 0:
            s["avg_delay_residual_min"] = delay_res
            s["avg_util_pct"] = round(util, 1)
            s["avg_fuel_l"] = round(fuel, 3)
        else:
            s["avg_delay_residual_min"] = round(
                (float(s.get("avg_delay_residual_min", 0.0)) * n + delay_res)
                / (n + 1), 3
            )
            s["avg_util_pct"] = round(
                (float(s.get("avg_util_pct", 0.0)) * n + util) / (n + 1), 1
            )
            s["avg_fuel_l"] = round(
                (float(s.get("avg_fuel_l", 0.0)) * n + fuel) / (n + 1), 3
            )
        s["trips"] = n + 1
        s["completion_rate"] = 1.0  # only Completed trips reach ingestion
        s["last_updated"] = datetime.now(timezone.utc).isoformat()

        # corridor driver quality: rolling quality of the corridor's best
        quality = LearningEngine._driver_quality(delay_res, util)
        qmap = state.setdefault("corridor_driver_quality", {})
        q = qmap.get(corridor)
        if q is None:
            qmap[corridor] = {
                "driver_id": int(trip.driver_id),
                "quality": round(quality, 4),
                "samples": 1,
            }
        elif int(q.get("driver_id", 0) or 0) == int(trip.driver_id):
            qn = int(q.get("samples", 0))
            q["quality"] = round(
                (float(q.get("quality", 0.0)) * qn + quality) / (qn + 1), 4
            )
            q["samples"] = qn + 1
        else:
            q_old = float(q.get("quality", 0.0))
            q["quality"] = round(q_old + LEARNING_RATE * (quality - q_old), 4)
            if float(q["quality"]) <= quality:
                q["driver_id"] = int(trip.driver_id)
            q["samples"] = int(q.get("samples", 0)) + 1

        if len(summaries) > DRIVER_SUMMARY_CAP:
            oldest = min(
                summaries, key=lambda k: summaries[k].get("last_updated") or ""
            )
            summaries.pop(oldest, None)
        if len(qmap) > QUALITY_CAP:
            qmap.pop(next(iter(qmap)))

    @staticmethod
    def _driver_quality(delay_residual: float, util_pct: float) -> float:
        """Driver quality proxy in [0, 1]: 0.7 × punctuality + 0.3 × utilisation."""
        punctuality = _clamp01(1.0 - abs(delay_residual) / 30.0)
        utilisation = _clamp01(util_pct / 100.0)
        return round(0.7 * punctuality + 0.3 * utilisation, 4)

    # ── periodic per-corridor refit (delay + utilization, gated together) ───

    @staticmethod
    def refit_enabled(db: Session) -> bool:
        """
        Single master switch for the periodic corridor refits.
        Gating both delay and utilization refits together keeps the A/B
        surface at one dimension (on/off); the residuals themselves are
        already stored in separate tagged ring buffers, so a later split
        only needs a second config key — nothing in the state schema.
        """
        try:
            raw = get_config_value(db, REFIT_ENABLED_KEY)
            if raw is not None:
                return str(raw).strip().lower() not in ("false", "0", "off")
        except Exception:
            pass
        return True

    @staticmethod
    def _maybe_refit(state: Dict[str, Any], db: Session) -> None:
        """
        Refit the per-corridor correction factors from the residual ring
        buffers.  Fires ONLY on exact multiples of REFIT_INTERVAL and only
        per-corridor when at least MIN_CORRIDOR_SAMPLES samples exist.
        Target factor = Σ(actual) / Σ(predicted), clamped to [0.5, 2.0].
        Existing factors are drift-damped toward the target (step of
        REFIT_DAMPING) so a single bad refit can never swing a corridor.
        The delay refit also records the per-corridor mean prediction
        error (minutes) for explainability.
        """
        if not LearningEngine.refit_enabled(db):
            return
        count = int(state["outcomes"].get("count", 0))
        if count <= 0 or count % REFIT_INTERVAL != 0:
            return
        for tag, target in (
            ("delay", "corridor_multipliers"),
            ("utilization", "corridor_utilization_bias"),
            ("fuel", "corridor_fuel_multiplier"),
            ("co2", "corridor_co2_multiplier"),
        ):
            groups: Dict[str, list] = {}
            for r in state.get("residuals", {}).get(tag, []):
                estimated = float(r.get("estimated", 0.0))
                if estimated <= 1e-6:
                    continue
                g = groups.setdefault(r.get("corridor", "unknown"), [0.0, 0.0, 0])
                g[0] += float(r.get("actual", 0.0))
                g[1] += estimated
                g[2] += 1
            for corridor, (sum_actual, sum_estimated, n) in groups.items():
                if n < MIN_CORRIDOR_SAMPLES:
                    continue
                target_factor = sum_actual / sum_estimated
                prev = float(state[target].get(corridor, 0.0))
                if prev > 0.0:
                    target_factor = (
                        REFIT_DAMPING * target_factor + (1.0 - REFIT_DAMPING) * prev
                    )
                factor = _clamp(
                    target_factor, CORRIDOR_FACTOR_MIN, CORRIDOR_FACTOR_MAX
                )
                state[target][corridor] = round(factor, 4)
        # Per-corridor mean delay prediction error (minutes) — explainability
        means: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for r in state.get("residuals", {}).get("delay", []):
            corr = r.get("corridor", "unknown")
            means[corr] = means.get(corr, 0.0) + (
                float(r.get("actual", 0.0)) - float(r.get("estimated", 0.0))
            )
            counts[corr] = counts.get(corr, 0) + 1
        for corr, total in means.items():
            if counts.get(corr, 0) >= MIN_CORRIDOR_SAMPLES:
                state["corridor_delay_residual_mean"][corr] = round(
                    total / counts[corr], 3
                )
        state["last_refit_count"] = count

    @staticmethod
    def _update_bias(state: Dict[str, Any], trip: Trip) -> None:
        """
        Residual-driven hedge of the weight biases:
          delay EMA > 0.5 min       → time & route up (delay under-priced)
          utilization EMA < −5 p.p. → capacity up (predicted utilisation
                                      over-optimistic — batches under-utilise)
        Decay runs first so a fresh signal clamps against the real bounds.
        """
        o = state["outcomes"]
        bias = state["factor_bias"]
        max_bias = MAX_BIAS

        # Decay: pull biases back toward zero so the system tracks drift
        for factor in bias:
            bias[factor] = round(
                _clamp(float(bias[factor]) * 0.995, -max_bias, max_bias), 4
            )

        delay_bias = float(o.get("delay_bias_min", 0.0))
        if delay_bias > 0.5:
            d = delay_bias / 20.0
            bias["time"] = round(_clamp(
                float(bias.get("time", 0.0)) + LEARNING_RATE * d * 2.0, -max_bias, max_bias
            ), 4)
            bias["route"] = round(_clamp(
                float(bias.get("route", 0.0)) + LEARNING_RATE * d, -max_bias, max_bias
            ), 4)

        util_bias = float(o.get("util_bias_pp", 0.0))
        if util_bias < -5.0:
            d = (-util_bias - 5.0) / 100.0
            bias["capacity"] = round(_clamp(
                float(bias.get("capacity", 0.0)) + LEARNING_RATE * d * 2.0,
                -max_bias, max_bias,
            ), 4)

        fuel_ratio = float(o.get("fuel_ratio", 1.0))
        if fuel_ratio > 1.1:
            d = (fuel_ratio - 1.1) / 0.9
            bias["route"] = round(_clamp(
                float(bias.get("route", 0.0)) + LEARNING_RATE * d * 2.0,
                -max_bias, max_bias,
            ), 4)

    # ── weight-correction synthesis (consumed by Module 2) ──────────────────

    @staticmethod
    def weight_corrections(db: Session) -> Dict[str, float]:
        """Learned bias per factor for the Adaptive Weight Generator."""
        state = LearningEngine.load_state(db)
        return {
            f: float(state["factor_bias"].get(f, 0.0)) for f in (
                "pickup", "route", "time", "capacity", "priority"
            )
        }

    @staticmethod
    def corridor_multiplier_from_state(
        state: Dict[str, Any], corridor: str
    ) -> float:
        """Delay correction factor for a corridor; 1.0 (no-op) if unseen."""
        return float(state.get("corridor_multipliers", {}).get(corridor, 1.0))

    @staticmethod
    def corridor_utilization_from_state(
        state: Dict[str, Any], corridor: str
    ) -> float:
        """Utilization correction factor for a corridor; 1.0 (no-op) if unseen."""
        return float(state.get("corridor_utilization_bias", {}).get(corridor, 1.0))

    @staticmethod
    def corridor_multipliers(db: Session) -> Dict[str, float]:
        """Refitted delay multipliers for all known corridors (for scoring)."""
        return dict(LearningEngine.load_state(db).get("corridor_multipliers", {}))

    @staticmethod
    def corridor_utilization_bias(db: Session) -> Dict[str, float]:
        """Refitted utilization factors for all known corridors (for scoring)."""
        return dict(
            LearningEngine.load_state(db).get("corridor_utilization_bias", {})
        )

    @staticmethod
    def corridor_fuel_multipliers(db: Session) -> Dict[str, float]:
        """Refitted fuel factors for all known corridors."""
        return dict(
            LearningEngine.load_state(db).get("corridor_fuel_multiplier", {})
        )

    @staticmethod
    def corridor_co2_multipliers(db: Session) -> Dict[str, float]:
        """Refitted CO2 factors for all known corridors."""
        return dict(
            LearningEngine.load_state(db).get("corridor_co2_multiplier", {})
        )

    @staticmethod
    def driver_outcome_summary(db: Session) -> Dict[str, Any]:
        """Per-driver rolling outcome summaries (driver_id → metrics)."""
        return dict(LearningEngine.load_state(db).get("driver_outcome_summary", {}))

    @staticmethod
    def corridor_driver_quality(db: Session) -> Dict[str, Any]:
        """Best-driver quality per corridor (corridor → {driver_id, quality, samples})."""
        return dict(
            LearningEngine.load_state(db).get("corridor_driver_quality", {})
        )

    @staticmethod
    def learned_signals(db: Session, corridor: str = "") -> Dict[str, float]:
        """Compact learned corrections for one corridor (context-engine channel)."""
        state = LearningEngine.load_state(db)
        corr = corridor or "unknown"
        return {
            "delay_multiplier": LearningEngine.corridor_multiplier_from_state(
                state, corr
            ),
            "utilization_factor": LearningEngine.corridor_utilization_from_state(
                state, corr
            ),
            "fuel_multiplier": float(
                state.get("corridor_fuel_multiplier", {}).get(corr, 1.0)
            ),
            "co2_multiplier": float(
                state.get("corridor_co2_multiplier", {}).get(corr, 1.0)
            ),
            "delay_residual_mean": float(
                state.get("corridor_delay_residual_mean", {}).get(corr, 0.0)
            ),
            "driver_quality": float(
                state.get("corridor_driver_quality", {}).get(corr, {})
                .get("quality", 0.5)
            ),
        }

    @staticmethod
    def summary(db: Session) -> Dict[str, Any]:
        """Compact status for dashboards / the /context endpoint."""
        state = LearningEngine.load_state(db)
        return {
            "enabled": LearningEngine.learning_enabled(db),
            "refit_enabled": LearningEngine.refit_enabled(db),
            "version": state.get("version", 1),
            "outcomes": state["outcomes"],
            "factor_bias": state["factor_bias"],
            "corridors": list(state.get("corridor", {}).keys()),
            "corridor_multipliers": dict(state.get("corridor_multipliers", {})),
            "corridor_utilization_bias": dict(
                state.get("corridor_utilization_bias", {})
            ),
            "corridor_fuel_multiplier": dict(
                state.get("corridor_fuel_multiplier", {})
            ),
            "corridor_co2_multiplier": dict(
                state.get("corridor_co2_multiplier", {})
            ),
            "drivers_tracked": len(state.get("driver_outcome_summary", {})),
            "corridor_driver_quality": dict(
                state.get("corridor_driver_quality", {})
            ),
            "last_refit_count": state.get("last_refit_count", 0),
            "residual_counts": {
                tag: len(buf) for tag, buf in
                state.get("residuals", {}).items()
            },
            "last_updated": state.get("last_updated"),
        }


# Module-level singleton
learning_engine = LearningEngine()
