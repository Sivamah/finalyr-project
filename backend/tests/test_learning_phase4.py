"""
Phase 4 — Adaptive Learning Engine tests (14 scenarios).

Covers the newly closed loops:

  - fuel / CO2 residuals and corridor multipliers (Steps 3/5)
  - per-driver outcome summaries + corridor driver quality (Step 6)
  - utilization prediction fallback from batch factor details (Step 4)
  - learned-signal injection into the ContextProfile (Step 8)
  - learned-pressure weight gains (Step 7)
  - learning safety: no-actuals guard, refit gating, bounded biases (Step 9)

The original 10 scenarios live in test_learning_engine.py (unchanged).
"""

from __future__ import annotations

import json

import pytest

from app.dmfe.adaptive.learning import (
    EMPTY_STATE,
    FLEET_MILEAGE_FALLBACK,
    LEARNING_RATE,
    MAX_BIAS,
    REFIT_INTERVAL,
    RESIDUAL_BUFFER_SIZE,
    LearningEngine,
)
from app.dmfe.adaptive.context import ContextAwarenessEngine
from app.dmfe.adaptive.weights import AdaptiveWeightGenerator

engine = LearningEngine()


def _empty_state() -> dict:
    return json.loads(json.dumps(EMPTY_STATE))


# ── 1+2. Fuel / CO2 residuals are logged into their own ring buffers ────────

def test_fuel_residual_logged_against_fleet_benchmark(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    batch = make_batch(requests=[r], estimated_delay_min=5.0)
    # 15 km at the 15 km/l fallback benchmark → expected 1.0 L; actual 2.0 L
    trip = make_trip(requests=[r], batch=batch, max_delay_min=5.0,
                     utilization_pct=50.0, fuel_l=2.0, total_distance_km=15.0)

    engine.record_trip_outcome(db, trip)
    state = LearningEngine.load_state(db)

    res = state["residuals"]["fuel"]
    assert res[-1]["corridor"] == "ride"
    assert abs(res[-1]["estimated"] - 1.0) < 1e-3
    assert res[-1]["actual"] == 2.0
    assert abs(state["outcomes"]["fuel_ratio"] - 2.0) < 1e-3


def test_co2_residual_logged_as_emissions_ratio(db, make_request, make_batch, make_trip):
    r = make_request()
    batch = make_batch(requests=[r])
    trip = make_trip(requests=[r], batch=batch, max_delay_min=3.0,
                     utilization_pct=50.0, fuel_l=2.0, total_distance_km=15.0)

    engine.record_trip_outcome(db, trip)
    state = LearningEngine.load_state(db)

    res = state["residuals"]["co2"]
    assert abs(res[-1]["estimated"] - 2.3) < 1e-3        # 1.0 L × 2.3
    assert abs(res[-1]["actual"] - 4.6) < 1e-3           # 2.0 L × 2.3


# ── 3+4. Fuel / CO2 corridor multipliers converge to the injected ratio ─────

def test_fuel_multiplier_converges_to_injected_ratio(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    for _ in range(REFIT_INTERVAL + 20):
        batch = make_batch(requests=[r], estimated_delay_min=5.0)
        # 2× the fleet benchmark fuel → ratio 2.0 → multiplier clamps at 2.0
        trip = make_trip(requests=[r], batch=batch, max_delay_min=5.0,
                         utilization_pct=50.0, fuel_l=2.0, total_distance_km=15.0)
        engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    assert abs(state["corridor_fuel_multiplier"]["ride"] - 2.0) < 0.01
    assert abs(state["corridor_co2_multiplier"]["ride"] - 2.0) < 0.01


def test_fuel_multiplier_absent_when_no_distance(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    for _ in range(REFIT_INTERVAL + 5):
        batch = make_batch(requests=[r])
        trip = make_trip(requests=[r], batch=batch, max_delay_min=5.0,
                         utilization_pct=50.0, fuel_l=1.0)
        engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    assert state["corridor_fuel_multiplier"] == {}
    assert len(state["residuals"]["fuel"]) == 0


# ── 5. Per-corridor mean delay residual is recorded at refit ────────────────

def test_delay_residual_mean_recorded_at_refit(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    for _ in range(REFIT_INTERVAL + 5):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trip = make_trip(requests=[r], batch=batch, max_delay_min=13.0,
                         utilization_pct=50.0)
        engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    assert abs(state["corridor_delay_residual_mean"]["ride"] - 3.0) < 1e-3


# ── 6. Refits are drift-damped toward the target ratio ──────────────────────

def test_refit_is_drift_damped_not_jumpy(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    # First refit window: ratio 1.0 → multiplier lands exactly at 1.0
    for _ in range(REFIT_INTERVAL):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trip = make_trip(requests=[r], batch=batch, max_delay_min=10.0,
                         utilization_pct=50.0)
        engine.record_trip_outcome(db, trip)
    state = LearningEngine.load_state(db)
    assert abs(state["corridor_multipliers"]["ride"] - 1.0) < 1e-3

    # Second window: ratio 2.0 → the ring (cap = one refit window) holds
    # window-2 alone, so the damped step = 0.5·2.0 + 0.5·1.0 = 1.5
    for _ in range(REFIT_INTERVAL):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trip = make_trip(requests=[r], batch=batch, max_delay_min=20.0,
                         utilization_pct=50.0)
        engine.record_trip_outcome(db, trip)
    state = LearningEngine.load_state(db)
    assert abs(state["corridor_multipliers"]["ride"] - 1.5) < 1e-3
    assert state["last_refit_count"] == 2 * REFIT_INTERVAL


# ── 7+8. Per-driver summaries and corridor driver quality ───────────────────

def test_driver_outcome_summary_accumulates(
    db, make_request, make_batch, make_trip, make_driver
):
    driver = make_driver()
    r = make_request()
    for i in range(10):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trip = make_trip(requests=[r], batch=batch, driver_id=driver.id,
                         max_delay_min=15.0, utilization_pct=60.0, fuel_l=1.0)
        engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    summary = state["driver_outcome_summary"][str(driver.id)]
    assert summary["trips"] == 10
    assert abs(summary["avg_delay_residual_min"] - 5.0) < 1e-3
    assert abs(summary["avg_util_pct"] - 60.0) < 1e-3
    assert summary["completion_rate"] == 1.0


def test_corridor_driver_quality_tracks_best_driver(
    db, make_request, make_batch, make_trip, make_driver
):
    punctual = make_driver(name="Punctual")
    late = make_driver(name="Late")
    r = make_request()

    # Punctual driver: zero delay residual → quality 1.0
    for _ in range(5):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trip = make_trip(requests=[r], batch=batch, driver_id=punctual.id,
                         max_delay_min=10.0, utilization_pct=100.0)
        engine.record_trip_outcome(db, trip)

    # Late driver: +20 min residual → quality ≈ 0.7·(1−20/30) + 0.3·0.5 ≈ 0.38
    for _ in range(5):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trip = make_trip(requests=[r], batch=batch, driver_id=late.id,
                         max_delay_min=30.0, utilization_pct=50.0)
        engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    q = state["corridor_driver_quality"]["ride"]
    assert q["driver_id"] == punctual.id
    assert q["quality"] > 0.8  # challenger drag is bounded by the 0.05 EMA
    assert q["samples"] >= 10


# ── 9. Safety: trips without actuals are never ingested ─────────────────────

def test_trip_without_actuals_is_skipped(db, make_request, make_batch, make_trip):
    r = make_request()
    # Zero-filled defaults + no batch linkage → auto-created row, never ingested
    trip = make_trip(requests=[r], max_delay_min=0.0,
                     utilization_pct=0.0, fuel_l=0.0)

    outcome = engine.record_trip_outcome(db, trip)
    state = LearningEngine.load_state(db)

    assert outcome is None
    assert state["outcomes"]["count"] == 0
    assert state == _empty_state()


# ── 10. Gating: learning_enabled / refit_enabled keep their contract ────────

def test_learning_disabled_noop(db, make_request, make_batch, make_trip, set_config):
    set_config("admfe.learning_enabled", "false")
    r = make_request()
    batch = make_batch(requests=[r], estimated_delay_min=5.0)
    trip = make_trip(requests=[r], batch=batch, max_delay_min=12.0,
                     utilization_pct=50.0, fuel_l=1.0, total_distance_km=15.0)

    assert engine.record_trip_outcome(db, trip) is None
    assert LearningEngine.load_state(db) == _empty_state()


def test_refit_disabled_logs_residuals_but_emits_no_factors(
    db, make_request, make_batch, make_trip, set_config
):
    set_config("admfe.refit_enabled", "false")
    r = make_request()
    for _ in range(REFIT_INTERVAL + 5):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trip = make_trip(requests=[r], batch=batch, max_delay_min=14.0,
                         utilization_pct=50.0, fuel_l=1.0, total_distance_km=15.0)
        engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    assert state["corridor_multipliers"] == {}
    assert state["corridor_fuel_multiplier"] == {}
    assert state["last_refit_count"] == 0
    assert len(state["residuals"]["delay"]) == min(
        REFIT_INTERVAL + 5, RESIDUAL_BUFFER_SIZE
    )
    assert len(state["residuals"]["fuel"]) == min(
        REFIT_INTERVAL + 5, RESIDUAL_BUFFER_SIZE
    )


# ── 11. Utilization predictions fall back to batch factor details ───────────

def test_utilization_prediction_falls_back_to_batch_factor_details(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    batch = make_batch(
        requests=[r],
        predicted_utilization_pct=0.0,
        factor_details_json=json.dumps({"capacity_utilization_pct": 75.0}),
    )
    trip = make_trip(requests=[r], batch=batch, max_delay_min=5.0,
                     utilization_pct=40.0)

    engine.record_trip_outcome(db, trip)
    state = LearningEngine.load_state(db)

    res = state["residuals"]["utilization"][-1]
    assert res["estimated"] == 75.0
    assert res["actual"] == 40.0
    assert abs(state["outcomes"]["util_bias_pp"] + 35.0) < 1e-3


# ── 12. Context profile carries learned signals (deterministic) ─────────────

def test_context_profile_injects_learned_signals(db, make_request, make_driver, make_vehicle):
    r1 = make_request(request_type="ride")
    r2 = make_request(request_type="food")
    make_driver()
    make_vehicle()

    pending = [r1, r2]
    first = ContextAwarenessEngine().build(db, pending)
    # default state → multipliers 1.0, pressures 0
    assert first.fuel_pressure == 0.0
    assert first.utilization_gap == 0.0
    assert first.raw["learned_delay_multiplier"] == 1.0
    assert first.raw["learned_corridor"] == "food|ride"

    # inject learned state → pressures appear
    state = LearningEngine.load_state(db)
    state["corridor_fuel_multiplier"]["food|ride"] = 1.8
    state["corridor_co2_multiplier"]["food|ride"] = 1.5
    state["corridor_utilization_bias"]["food|ride"] = 0.5
    state["corridor_multipliers"]["food|ride"] = 1.4
    LearningEngine.save_state(db, state)

    second = ContextAwarenessEngine().build(db, pending)
    assert abs(second.fuel_pressure - 0.8) < 1e-3
    assert abs(second.co2_pressure - 0.5) < 1e-3
    assert abs(second.utilization_gap - 0.5) < 1e-3
    assert second.raw["learned_delay_multiplier"] == 1.4

    third = ContextAwarenessEngine().build(db, pending)
    assert second.to_dict() == third.to_dict()  # deterministic


# ── 13. Adaptive weights react to learned pressures (static untouched) ──────

def test_learned_pressures_shift_adaptive_weights(
    db, make_request, make_driver, make_vehicle
):
    make_driver()
    make_vehicle()
    r = make_request()
    from app.dmfe.adaptive.context import ContextProfile

    ctx_clean = ContextAwarenessEngine().build(db, [r])
    w_clean = AdaptiveWeightGenerator(mode="adaptive").generate(db, ctx_clean, {})

    state = LearningEngine.load_state(db)
    state["corridor_fuel_multiplier"]["ride"] = 1.8
    state["corridor_utilization_bias"]["ride"] = 0.5
    LearningEngine.save_state(db, state)
    ctx_learned = ContextAwarenessEngine().build(db, [r])
    w_learned = AdaptiveWeightGenerator(mode="adaptive").generate(
        db, ctx_learned, LearningEngine.weight_corrections(db)
    )

    assert ctx_learned.fuel_pressure > 0
    assert w_learned["route"] > w_clean["route"]
    assert w_learned["capacity"] > w_clean["capacity"]
    assert abs(sum(w_learned.values()) - 1.0) < 1e-6

    # static mode ignores everything
    w_static = AdaptiveWeightGenerator(mode="static").generate(
        db, ctx_learned, LearningEngine.weight_corrections(db)
    )
    from app.dmfe.adaptive.weights import load_base_weights

    base = load_base_weights(db)
    assert all(abs(w_static[k] - base[k]) < 1e-9 for k in base)


# ── 14. Weight corrections stay bounded and feed the generator ──────────────

def test_weight_corrections_bounded_and_applied(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    # 60 min delay residual on every trip → time/route bias pushed to the cap
    for _ in range(10):
        batch = make_batch(requests=[r], estimated_delay_min=0.0)
        trip = make_trip(requests=[r], batch=batch, max_delay_min=60.0,
                         utilization_pct=50.0)
        engine.record_trip_outcome(db, trip)

    corrections = LearningEngine.weight_corrections(db)
    for factor, value in corrections.items():
        assert -MAX_BIAS - 1e-9 <= value <= MAX_BIAS + 1e-9
    assert corrections["time"] == MAX_BIAS
    assert corrections["route"] == MAX_BIAS


def test_state_schema_upgraded_to_version_three(db):
    state = LearningEngine.load_state(db)
    assert state["version"] == 3
    assert "corridor_fuel_multiplier" in state
    assert "corridor_co2_multiplier" in state
    assert "corridor_driver_quality" in state
    assert "driver_outcome_summary" in state
    assert "corridor_delay_residual_mean" in state
    assert set(state["residuals"]) == {"delay", "utilization", "fuel", "co2"}
    summary = LearningEngine.summary(db)
    assert summary["version"] == 3
    assert "corridor_fuel_multiplier" in summary
