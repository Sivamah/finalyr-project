"""
LearningEngine tests — residual ingestion, corridor refit, ring buffers.

Mirrors the manual refit experiment: 450 trips, 1.4x injected on the
``food|ride`` corridor, ~1.0 on ``parcel|ride``, asserting convergence of
``corridor_multipliers`` within ±0.05.
"""

from __future__ import annotations

import json

import pytest

from app.dmfe.adaptive.learning import (
    EMPTY_STATE,
    MAX_BIAS,
    REFIT_INTERVAL,
    RESIDUAL_BUFFER_SIZE,
    LearningEngine,
)

engine = LearningEngine()


def _empty_state() -> dict:
    return json.loads(json.dumps(EMPTY_STATE))


def test_learning_disabled_is_noop(db, make_request, make_batch, make_trip, set_config):
    set_config("admfe.learning_enabled", "false")
    r = make_request()
    batch = make_batch(requests=[r], estimated_delay_min=5.0)
    trip = make_trip(requests=[r], batch=batch, max_delay_min=12.0)

    assert engine.record_trip_outcome(db, trip) is None
    assert LearningEngine.load_state(db) == _empty_state()


def test_large_positive_delay_residual_raises_time_route_bias_to_cap(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    batch = make_batch(requests=[r], estimated_delay_min=0.0)
    trip = make_trip(requests=[r], batch=batch, max_delay_min=60.0)

    state = engine.record_trip_outcome(db, trip)

    assert state is not None
    assert state["outcomes"]["delay_bias_min"] == 60.0
    assert state["factor_bias"]["time"] == MAX_BIAS
    assert state["factor_bias"]["route"] == MAX_BIAS
    assert state["factor_bias"]["capacity"] == 0.0


def test_utilization_residual_drives_capacity_bias(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    # Predicted 80% utilization, realized 40% → −40 p.p. residual
    batch = make_batch(requests=[r], predicted_utilization_pct=80.0)
    trip = make_trip(requests=[r], batch=batch, utilization_pct=40.0)

    state = engine.record_trip_outcome(db, trip)

    assert state is not None
    assert state["outcomes"]["util_bias_pp"] == -40.0
    assert state["factor_bias"]["capacity"] > 0.0


def test_corridor_multipliers_converge_to_injected_ratio(
    db, make_request, make_batch, make_trip
):
    food = make_request(
        request_type="food",
        pickup_lat=11.00, pickup_lng=76.90, drop_lat=11.01, drop_lng=76.91,
    )
    ride = make_request(
        request_type="ride",
        pickup_lat=11.02, pickup_lng=76.96, drop_lat=11.03, drop_lng=76.97,
    )
    parcel = make_request(
        request_type="parcel",
        pickup_lat=11.04, pickup_lng=76.99, drop_lat=11.05, drop_lng=77.00,
    )

    # 225 trips on food|ride with a 1.4x injected delay multiplier
    for _ in range(225):
        batch = make_batch(requests=[food, ride], estimated_delay_min=10.0)
        trip = make_trip(requests=[food, ride], batch=batch, max_delay_min=14.0)
        engine.record_trip_outcome(db, trip)

    # 225 trips on parcel|ride with a 1.0x multiplier
    for _ in range(225):
        batch = make_batch(requests=[parcel, ride], estimated_delay_min=10.0)
        trip = make_trip(requests=[parcel, ride], batch=batch, max_delay_min=10.0)
        engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    mult = state["corridor_multipliers"]

    assert abs(mult["food|ride"] - 1.4) < 0.05
    assert abs(mult["parcel|ride"] - 1.0) < 0.05
    assert state["last_refit_count"] == 400


def test_ring_buffer_never_exceeds_capacity(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    for _ in range(550):
        batch = make_batch(
            requests=[r], estimated_delay_min=5.0, predicted_utilization_pct=60.0
        )
        trip = make_trip(requests=[r], batch=batch,
                         max_delay_min=5.0, utilization_pct=60.0)
        engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    assert len(state["residuals"]["delay"]) == RESIDUAL_BUFFER_SIZE
    assert len(state["residuals"]["utilization"]) == RESIDUAL_BUFFER_SIZE
    assert state["outcomes"]["count"] == 550


def test_refit_fires_only_on_exact_multiples_of_interval(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    checkpoints = {}
    for i in range(1, 450):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trip = make_trip(requests=[r], batch=batch, max_delay_min=10.0)
        engine.record_trip_outcome(db, trip)
        if i in (199, 200, 399, 400, 449):
            checkpoints[i] = LearningEngine.load_state(db)["last_refit_count"]

    assert checkpoints[199] == 0
    assert checkpoints[200] == REFIT_INTERVAL
    assert checkpoints[399] == REFIT_INTERVAL
    assert checkpoints[400] == 2 * REFIT_INTERVAL
    assert checkpoints[449] == 2 * REFIT_INTERVAL


def test_refit_disabled_flag_blocks_corridor_refit(
    db, make_request, make_batch, make_trip, set_config
):
    set_config("admfe.refit_enabled", "false")
    r = make_request()
    for _ in range(REFIT_INTERVAL + 5):
        batch = make_batch(requests=[r], estimated_delay_min=10.0)
        trip = make_trip(requests=[r], batch=batch, max_delay_min=14.0)
        engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    assert state["corridor_multipliers"] == {}
    assert state["last_refit_count"] == 0
    # residuals are still logged — only the refit is gated (ring is capped
    # at one refit window worth of samples)
    assert len(state["residuals"]["delay"]) == min(
        REFIT_INTERVAL + 5, RESIDUAL_BUFFER_SIZE
    )


def test_corridor_multiplier_from_state_defaults_to_one():
    state = _empty_state()
    assert LearningEngine.corridor_multiplier_from_state(state, "food|food") == 1.0
    assert LearningEngine.corridor_multiplier_from_state(state, "never_seen") == 1.0
    state["corridor_multipliers"]["food|ride"] = 1.4
    assert LearningEngine.corridor_multiplier_from_state(state, "food|ride") == 1.4


def test_utilization_residuals_are_tagged_separately(
    db, make_request, make_batch, make_trip
):
    r = make_request()
    batch = make_batch(requests=[r], estimated_delay_min=3.0, predicted_utilization_pct=70.0)
    trip = make_trip(requests=[r], batch=batch, max_delay_min=8.0, utilization_pct=35.0)

    engine.record_trip_outcome(db, trip)
    state = LearningEngine.load_state(db)

    delay_res = state["residuals"]["delay"]
    util_res = state["residuals"]["utilization"]
    assert delay_res[-1] == {"corridor": "ride", "estimated": 3.0, "actual": 8.0}
    assert util_res[-1] == {"corridor": "ride", "estimated": 70.0, "actual": 35.0}


def test_utilization_corridor_factor_refits_on_interval(
    db, make_request, make_batch, make_trip
):
    food = make_request(request_type="food", pickup_lat=11.0, pickup_lng=76.9)
    ride = make_request(request_type="ride", pickup_lat=11.02, pickup_lng=76.96)

    # predicted 50% utilization, realized 25% → 0.5x factor
    for _ in range(REFIT_INTERVAL + 10):
        batch = make_batch(requests=[food, ride], predicted_utilization_pct=50.0)
        trip = make_trip(requests=[food, ride], batch=batch, utilization_pct=25.0)
        engine.record_trip_outcome(db, trip)

    state = LearningEngine.load_state(db)
    assert abs(state["corridor_utilization_bias"]["food|ride"] - 0.5) < 0.05
