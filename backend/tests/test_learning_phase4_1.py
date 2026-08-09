"""
Phase 4.1 — hot-path optimization guardrail tests (10 scenarios).

Protects the Phase 4.1 changes that made the ingestion hot path cheaper:

  - corridor / batch lookups deduplicated to a single pass per trip
  - refit aggregation skipped except on exact REFIT_INTERVAL multiples
  - residual ring buffers capped at RESIDUAL_BUFFER_SIZE (= one refit
    window), so the per-trip saved payload and JSON parse stay bounded

These tests assert that the optimizations did NOT silently change the
learning contract: ring bounds, refit cadence, per-corridor gating,
factor clamping, signal separation, state durability, corrupt-state
recovery, the no-actuals ingestion guard, and a wall-clock guardrail
for the engine-only hot path.
"""

from __future__ import annotations

import json
import time

from sqlalchemy.orm import sessionmaker

from app.db.models import SystemConfig, Trip
from app.dmfe.adaptive.learning import (
    CORRIDOR_FACTOR_MAX,
    CORRIDOR_FACTOR_MIN,
    MIN_CORRIDOR_SAMPLES,
    REFIT_INTERVAL,
    RESIDUAL_BUFFER_SIZE,
    LearningEngine,
)

engine = LearningEngine()


def _record(db, r, mb, mt, est=10.0, actual=10.0, util_est=70.0,
            util_actual=50.0, *, n=REFIT_INTERVAL):
    """Record ``n`` trips on one corridor with the given predictions."""
    for _ in range(n):
        batch = mb(requests=[r], estimated_delay_min=est,
                   predicted_utilization_pct=util_est)
        trip = mt(requests=[r], batch=batch, max_delay_min=actual,
                  utilization_pct=util_actual)
        engine.record_trip_outcome(db, trip)


# ── 1. Ring bounds: residuals never exceed RESIDUAL_BUFFER_SIZE ─────────────

def test_residual_ring_bounded_at_cap(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    _record(db, r, make_batch, make_trip, n=3 * RESIDUAL_BUFFER_SIZE)

    state = LearningEngine.load_state(db)
    assert state["outcomes"]["count"] == 3 * RESIDUAL_BUFFER_SIZE
    for tag in ("delay", "utilization"):
        assert len(state["residuals"][tag]) == RESIDUAL_BUFFER_SIZE


# ── 2. Factor clamp: extreme ratio can never leave [min, max] ───────────────

def test_corridor_factor_clamped_to_bounds(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    _record(db, r, make_batch, make_trip, est=10.0, actual=500.0)

    state = LearningEngine.load_state(db)
    factor = state["corridor_multipliers"]["ride"]
    assert factor == CORRIDOR_FACTOR_MAX  # cold start: 50.0 clamped → 2.0
    assert CORRIDOR_FACTOR_MIN <= factor <= CORRIDOR_FACTOR_MAX


# ── 3. Refit cadence: factors only move on exact REFIT_INTERVAL multiples ──

def test_refit_fires_only_at_interval_multiples(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    for i in range(2 * REFIT_INTERVAL):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trip = make_trip(requests=[r], batch=batch, max_delay_min=10.0,
                         utilization_pct=50.0)
        state = engine.record_trip_outcome(db, trip)
        expected = (i + 1) // REFIT_INTERVAL * REFIT_INTERVAL
        if (i + 1) % REFIT_INTERVAL == 0:
            assert state["last_refit_count"] == i + 1
        else:
            assert state["last_refit_count"] == expected

    assert state["last_refit_count"] == 2 * REFIT_INTERVAL


# ── 4. Per-corridor gating: < MIN_CORRIDOR_SAMPLES → no factor ─────────────

def test_refit_requires_min_corridor_samples(
    db, make_request, make_batch, make_trip
):
    sparse = make_request()
    dense = make_request(request_type="food")
    _record(db, sparse, make_batch, make_trip, n=MIN_CORRIDOR_SAMPLES - 1)
    _record(db, dense, make_batch, make_trip,
            est=10.0, actual=20.0,
            n=REFIT_INTERVAL - (MIN_CORRIDOR_SAMPLES - 1))

    state = LearningEngine.load_state(db)
    assert "ride" not in state["corridor_multipliers"]
    assert state["corridor_multipliers"]["food"] == 2.0
    assert state["last_refit_count"] == REFIT_INTERVAL


# ── 5. Corridor isolation: one corridor's drift never leaks into another ───

def test_corridors_refit_independently(
    db, make_request, make_batch, make_trip
):
    stable = make_request()
    drift = make_request(request_type="parcel")
    _record(db, stable, make_batch, make_trip, est=10.0, actual=10.0,
            n=REFIT_INTERVAL // 2)
    _record(db, drift, make_batch, make_trip, est=10.0, actual=15.0,
            n=REFIT_INTERVAL // 2)

    state = LearningEngine.load_state(db)
    assert state["corridor_multipliers"]["ride"] == 1.0
    assert state["corridor_multipliers"]["parcel"] == 1.5


# ── 6. Signal separation: delay vs utilization refit into their own maps ────

def test_signal_tracks_refit_separately(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    _record(db, r, make_batch, make_trip,
            est=10.0, actual=12.0, util_est=70.0, util_actual=35.0)

    state = LearningEngine.load_state(db)
    assert state["corridor_multipliers"]["ride"] == 1.2
    assert state["corridor_utilization_bias"]["ride"] == 0.5


# ── 7. Durability: persisted multipliers survive a full session restart ────

def test_state_survives_restart_round_trip(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    _record(db, r, make_batch, make_trip, est=10.0, actual=13.0)
    db.commit()

    fresh = sessionmaker(bind=db.bind)()
    try:
        state = LearningEngine.load_state(fresh)
        assert state["corridor_multipliers"]["ride"] == 1.3
        assert state["outcomes"]["count"] == REFIT_INTERVAL
        assert len(state["residuals"]["delay"]) == REFIT_INTERVAL
    finally:
        fresh.close()


# ── 8. Corrupt state JSON falls back to a clean state, not a crash ─────────

def test_corrupt_state_json_falls_back_to_clean(
    db, make_request, make_batch, make_trip
):
    db.add(SystemConfig(
        category="ai_rules", key="admfe.learning_state",
        value="this-is-not-json", data_type="json",
    ))
    db.commit()

    state = LearningEngine.load_state(db)
    assert state["outcomes"]["count"] == 0
    assert state["corridor_multipliers"] == {}

    r = make_request()
    batch = make_batch(requests=[r], estimated_delay_min=10.0)
    trip = make_trip(requests=[r], batch=batch, max_delay_min=13.0,
                     utilization_pct=50.0)
    engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    assert state["outcomes"]["count"] == 1


# ── 9. Ingestion guard: zero-filled trip without batch poisons nothing ─────

def test_zero_outcome_trip_without_batch_is_skipped(
    db, make_request, make_trip
):
    r = make_request()
    trip = make_trip(requests=[r], max_delay_min=0.0, utilization_pct=0.0,
                     fuel_l=0.0, total_duration_min=0.0)
    assert trip.batch_id is None

    engine.record_trip_outcome(db, trip)
    state = LearningEngine.load_state(db)
    assert state["outcomes"]["count"] == 0
    assert state["corridor"] == {}
    assert state["residuals"]["delay"] == []


# ── 10. Hot-path performance guardrail (catastrophic-regression tripwire) ───

def test_ingest_hot_path_performance_guardrail(
    db, make_request, make_batch, make_trip
):
    """2000 trips through the engine-only hot path finish under budget.

    Measured on the dev box this takes ~12s (the dominant costs are the
    per-trip state load + save round trip, ~2.5ms).  The 25s budget is a
    tripwire with 2x headroom: it catches catastrophic regressions such
    as per-trip full-corridor rescans or re-introduced N+1 query loops,
    without being flaky on slower CI machines.
    """
    r = make_request()
    trips = []
    for _ in range(2000):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trips.append(make_trip(requests=[r], batch=batch,
                               max_delay_min=12.0, utilization_pct=50.0))

    t0 = time.perf_counter()
    for trip in trips:
        engine.record_trip_outcome(db, trip)
    elapsed = time.perf_counter() - t0

    assert elapsed < 25.0, f"hot path too slow: {elapsed:.2f}s for 2000 trips"
    state = LearningEngine.load_state(db)
    assert state["outcomes"]["count"] == 2000
    assert state["last_refit_count"] == 10 * REFIT_INTERVAL
