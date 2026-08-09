"""
Phase 3 — Intelligent Driver Selection tests.

Ten required scenarios:
  1. No available drivers → no candidate, precise Gate E reason
  2. One feasible driver → selected
  3. Multiple feasible drivers → best by score
  4. Insufficient capacity → vehicle excluded
  5. Incompatible vehicle → still feasible, typed vehicle preferred
  6. Lower ETA wins appropriately
  7. Workload/fairness: rotation among similar drivers, bounded by ETA
  8. Static mode: learning_state has ZERO influence
  9. Adaptive mode: learning_state influences the pick
  10. Decision explanation matches the actual decision
"""

from __future__ import annotations

import pytest

from app.dmfe.adaptive.learning import LearningEngine
from app.dmfe.batch_generator import CandidateGroup
from app.dmfe.compatibility import (
    CompatibilityCalculator,
    _get_ai_rules,
    _get_threshold,
    clear_config_cache,
    resolve_mode,
)
from app.dmfe.decision_engine import (
    DecisionEngine,
    _cached_selector_rules,
    _driver_feasibility,
)
from app.dmfe.driver_selection import DriverSelector

ANCHOR_LAT, ANCHOR_LNG = 11.0168, 76.9558
calc = CompatibilityCalculator()
selector = DriverSelector()


def _pair(db, make_driver, make_vehicle, lat, lng, **vkw):
    """Driver + assigned vehicle at the same location."""
    v = make_vehicle(current_lat=lat, current_lng=lng, **vkw)
    d = make_driver(current_lat=lat, current_lng=lng, assigned_vehicle_id=v.id)
    return d, v


# ── 1. No available drivers ─────────────────────────────────────────────────

def test_no_available_drivers_returns_none(db, make_driver, make_vehicle, make_request):
    d, _v = _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG)
    d.status = "Busy"
    db.flush()

    req = make_request()
    pool = selector.build_pool(db)
    assert selector.select(db, [req], pool=pool) is None

    ok, reason, candidate = _driver_feasibility(
        db, [req], _get_ai_rules(db), selector, pool,
        _cached_selector_rules(db),
    )
    assert not ok
    assert "No driver is currently Available" in reason
    assert candidate is None


def test_unseeded_system_skips_gate(db, make_request):
    """No drivers at all → gate skipped (fresh-install semantic)."""
    req = make_request()
    pool = selector.build_pool(db)
    ok, reason, candidate = _driver_feasibility(
        db, [req], _get_ai_rules(db), selector, pool,
        _cached_selector_rules(db),
    )
    assert ok
    assert "skipped" in reason
    assert candidate is None


# ── 2. One feasible driver ─────────────────────────────────────────────────

def test_one_feasible_driver_selected(db, make_driver, make_vehicle, make_request):
    d, v = _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG)
    req = make_request()

    cand = selector.select(db, [req])
    assert cand is not None
    assert cand.driver.id == d.id
    assert cand.vehicle.id == v.id
    assert cand.eta_min < 1.0
    assert cand.total_score > 1.0


# ── 3. Multiple feasible drivers — best by score ───────────────────────────

def test_multiple_feasible_best_score_wins(db, make_driver, make_vehicle, make_request):
    d_near, _ = _pair(db, make_driver, make_vehicle, 11.0259, 76.9558)   # ~1 km
    _pair(db, make_driver, make_vehicle, 11.0439, 76.9558)               # ~3 km
    _pair(db, make_driver, make_vehicle, 11.0889, 76.9558)               # ~8 km
    req = make_request()

    cand = selector.select(db, [req])
    assert cand is not None
    assert cand.driver.id == d_near.id
    assert cand.proximity_score == pytest.approx(0.92, abs=0.01)
    # the others were candidates too — best-by-score picked the closest
    assert cand.eta_min < 5.0


# ── 4. Insufficient capacity ───────────────────────────────────────────────

def test_insufficient_capacity_excludes_vehicle(db, make_driver, make_vehicle, make_request):
    _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG, capacity=2)
    req = make_request(demand=3, weight_kg=0.0)

    pool = selector.build_pool(db)
    assert pool.fitting_vehicles(3) == []
    assert selector.select(db, [req], pool=pool) is None

    # a fitting vehicle now exists → same request is dispatchable
    _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG, capacity=6)
    cand = selector.select(db, [req])
    assert cand is not None
    assert cand.vehicle.capacity >= 6


# ── 5. Incompatible vehicle ────────────────────────────────────────────────

def test_incompatible_vehicle_still_feasible(db, make_driver, make_vehicle, make_request):
    req = make_request(vehicle_type="Car")
    _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG, vehicle_type="Bike", capacity=1)

    cand = selector.select(db, [req])
    assert cand is not None                      # feasible, just lower type score
    assert cand.type_score == pytest.approx(0.4)

    d_car, _ = _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG, vehicle_type="Car")
    cand2 = selector.select(db, [req])
    assert cand2.driver.id == d_car.id
    assert cand2.type_score == pytest.approx(1.0)


# ── 6. Lower ETA wins appropriately ────────────────────────────────────────

def test_lower_eta_wins(db, make_driver, make_vehicle, make_request):
    _pair(db, make_driver, make_vehicle, 11.1069, 76.9558)   # ~10 km
    d_near, _ = _pair(db, make_driver, make_vehicle, 11.0348, 76.9558)  # ~2 km
    req = make_request()

    cand = selector.select(db, [req])
    assert cand.driver.id == d_near.id
    assert cand.eta_min < 6.0


# ── 7. Workload / fairness ─────────────────────────────────────────────────

def test_fairness_rotates_to_fresh_driver(db, make_driver, make_vehicle, make_history, make_request):
    d_a, v_a = _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG)
    d_b, _v = _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG)
    for _ in range(20):
        make_history(d_a, v_a)                    # A has been worked a lot
    req = make_request()

    cand = selector.select(db, [req])
    assert cand.driver.id == d_b.id               # fresh driver preferred
    assert cand.fairness_score > 0.99


def test_fairness_bounded_by_eta_gap(db, make_driver, make_vehicle, make_history, make_request):
    d_a, v_a = _pair(db, make_driver, make_vehicle, 11.0348, 76.9558)  # ~2 km, worked hard
    for _ in range(20):
        make_history(d_a, v_a)
    _pair(db, make_driver, make_vehicle, 11.1069, 76.9558)             # ~10 km, fresh
    req = make_request()

    cand = selector.select(db, [req])
    assert cand.driver.id == d_a.id               # fairness cannot beat 8 km ETA gap
    assert cand.fairness_score < 0.5


# ── 8. Static mode: learning_state has ZERO influence ──────────────────────

def test_static_mode_unaffected_by_learning_state(
    db, make_driver, make_vehicle, make_history, make_request, set_config,
):
    set_config("admfe.mode", "static")
    assert resolve_mode(db) == "static"

    # "flip" scenario: near-but-poor-history vs far-but-perfect driver
    d_near, v_near = _pair(db, make_driver, make_vehicle, 11.0213, 76.9558, vehicle_type="Bike", capacity=1)
    for _ in range(30):
        make_history(d_near, v_near, status="Cancelled")
    d_far, _ = _pair(db, make_driver, make_vehicle, 11.1249, 76.9558)

    req = make_request(vehicle_type="Car")
    base = selector.select(db, [req])
    assert base is not None
    assert base.learning_proximity_bump == 0.0

    # poison the learning state — static mode must ignore it completely
    LearningEngine.save_state(db, {
        "outcomes": {"delay_bias_min": 30.0, "utilization_bias_pct": 0.0},
        "factor_bias": {"time": 0.0, "route": 0.0, "capacity": 0.0},
        "corridor_multipliers": {"ride": 2.0},
        "refit_enabled": True,
        "version": 1,
    })
    db.flush()
    poisoned = selector.select(db, [req])

    assert poisoned.driver.id == base.driver.id == d_far.id
    assert poisoned.total_score == pytest.approx(base.total_score, abs=1e-12)
    assert poisoned.learning_proximity_bump == 0.0


# ── 9. Adaptive mode: learning_state influences the pick ───────────────────

def test_adaptive_mode_uses_learning_state(
    db, make_driver, make_vehicle, make_history, make_request,
):
    assert resolve_mode(db) == "adaptive"         # default

    d_near, v_near = _pair(db, make_driver, make_vehicle, 11.0213, 76.9558, vehicle_type="Bike", capacity=1)
    for _ in range(30):
        make_history(d_near, v_near, status="Cancelled")
    d_far, _ = _pair(db, make_driver, make_vehicle, 11.1249, 76.9558)

    req = make_request(vehicle_type="Car")

    # with a neutral state, the perfect far driver wins (score .77 > .70)
    neutral = selector.select(db, [req])
    assert neutral.driver.id == d_far.id

    # learned delay bias (30 min) × corridor multiplier 2 → bump 0.2
    LearningEngine.save_state(db, {
        "outcomes": {"delay_bias_min": 30.0, "utilization_bias_pct": 0.0},
        "factor_bias": {"time": 0.0, "route": 0.0, "capacity": 0.0},
        "corridor_multipliers": {"ride": 2.0},
        "refit_enabled": True,
        "version": 1,
    })
    db.flush()
    clear_config_cache()                          # drop the cached empty state
    adapted = selector.select(db, [req])

    assert adapted.learning_proximity_bump == pytest.approx(0.2, abs=1e-9)
    assert adapted.driver.id == d_near.id         # ETA matters more now
    assert adapted.proximity_score > neutral.proximity_score


# ── 10. Decision explanation matches the actual decision ───────────────────

def _cg(db, make_request, score_gap=0.0):
    r1 = make_request(
        request_type="food",
        pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG,
        drop_lat=11.0300, drop_lng=76.9700,
    )
    r2 = make_request(
        request_type="ride",
        pickup_lat=11.0200, pickup_lng=76.9700,
        drop_lat=11.0350, drop_lng=76.9850,
    )
    result = calc.compute([r1, r2], db, mode=resolve_mode(db))
    result.compatibility_score = max(result.compatibility_score, 80.0) - score_gap
    return CandidateGroup(requests=[r1, r2], result=result)


def _evaluate(db, cg, selector, pool):
    decision, _status, reasons = DecisionEngine()._evaluate_group(
        cg, _get_ai_rules(db), _get_threshold(db), db,
        selector=selector, driver_pool=pool,
        selector_rules=_cached_selector_rules(db),
    )
    return decision, reasons


def test_decision_explanation_accepted(db, make_driver, make_vehicle, make_request):
    d, v = _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG)
    cg = _cg(db, make_request)
    pool = selector.build_pool(db)

    decision, reasons = _evaluate(db, cg, selector, pool)
    assert decision == "Compatible"
    text = "\n".join(reasons)
    assert f"Driver #{d.id}" in text
    assert "selected" in text
    assert "capacity" in text.lower()


def test_decision_explanation_rejected_no_driver(db, make_driver, make_vehicle, make_request):
    d, _v = _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG)
    d.status = "Busy"
    db.flush()
    cg = _cg(db, make_request)
    pool = selector.build_pool(db)

    decision, reasons = _evaluate(db, cg, selector, pool)
    assert decision == "Incompatible"
    text = "\n".join(reasons)
    assert "No driver is currently Available" in text


def test_decision_explanation_rejected_below_threshold(
    db, make_driver, make_vehicle, make_request,
):
    _pair(db, make_driver, make_vehicle, ANCHOR_LAT, ANCHOR_LNG)
    cg = _cg(db, make_request, score_gap=100.0)   # score ≪ threshold
    pool = selector.build_pool(db)

    decision, reasons = _evaluate(db, cg, selector, pool)
    assert decision == "Incompatible"
    assert any("threshold" in r.lower() for r in reasons)
