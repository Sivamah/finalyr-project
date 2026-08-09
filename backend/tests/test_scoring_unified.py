import pytest
from app.dmfe.score_engine import (
    cost_score,
    fuel_score,
    co2_score,
    delay_penalty_score,
)
from app.dmfe.scoring import unified_decision_score, UNIFIED_WEIGHTS

def test_normalization_bounds():
    # Fuel
    assert fuel_score(0.0)[0] == 1.0
    assert fuel_score(5.0, max_acceptable_fuel_l=10.0)[0] == 0.5
    assert fuel_score(15.0, max_acceptable_fuel_l=10.0)[0] == 0.0

    # CO2
    assert co2_score(0.0)[0] == 1.0
    assert co2_score(12.5, max_acceptable_co2_kg=25.0)[0] == 0.5
    assert co2_score(30.0, max_acceptable_co2_kg=25.0)[0] == 0.0

    # Cost
    assert cost_score(0.0)[0] == 1.0
    assert cost_score(25.0, max_acceptable_cost=50.0)[0] == 0.5
    assert cost_score(60.0, max_acceptable_cost=50.0)[0] == 0.0

    # Delay
    assert delay_penalty_score(0.0)[0] == 1.0
    assert delay_penalty_score(10.0, max_delay_min=20.0)[0] == 0.5
    assert delay_penalty_score(30.0, max_delay_min=20.0)[0] == 0.0

def test_unified_decision_score_perfect():
    weights = UNIFIED_WEIGHTS.copy()
    score_pct, factors = unified_decision_score(
        weights=weights,
        compatibility_pct=100.0,
        driver_score=1.0,
        cost=0.0,
        fuel_l=0.0,
        co2_kg=0.0,
        delay_min=0.0,
    )
    assert score_pct == 100.0
    for val in factors.values():
        assert val == 1.0

def test_unified_decision_score_worst():
    weights = UNIFIED_WEIGHTS.copy()
    score_pct, factors = unified_decision_score(
        weights=weights,
        compatibility_pct=0.0,
        driver_score=0.0,
        cost=100.0,
        fuel_l=100.0,
        co2_kg=100.0,
        delay_min=100.0,
    )
    assert score_pct == 0.0
    for val in factors.values():
        assert val == 0.0

def test_unified_decision_score_partial():
    weights = UNIFIED_WEIGHTS.copy()
    score_pct, factors = unified_decision_score(
        weights=weights,
        compatibility_pct=50.0,
        driver_score=0.5,
        cost=25.0,
        fuel_l=5.0,
        co2_kg=12.5,
        delay_min=10.0,
    )
    assert score_pct == 50.0

def test_unified_decision_score_zero_weights():
    weights = {k: 0.0 for k in UNIFIED_WEIGHTS}
    score_pct, _ = unified_decision_score(
        weights=weights,
        compatibility_pct=100.0,
        driver_score=1.0,
        cost=0.0,
        fuel_l=0.0,
        co2_kg=0.0,
        delay_min=0.0,
    )
    assert score_pct == 0.0
