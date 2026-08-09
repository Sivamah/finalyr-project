"""
CompatibilityCalculator tests — the A/B-baseline invariants.

The static-mode result must be byte-identical regardless of learning-state
contents (the baseline arm of run_admfe_experiments.py depends on it), and
the adaptive-mode delay must scale exactly by the refitted corridor
multiplier — only when refit is enabled AND the corridor matches.
"""

from __future__ import annotations

import pytest

from app.dmfe.compatibility import CompatibilityCalculator

calc = CompatibilityCalculator()


@pytest.fixture()
def pair_requests(make_request):
    """One food + one ride request ~1.6 km apart (delay ≈ 3.2 min)."""
    food = make_request(
        request_type="food",
        pickup_lat=11.0168, pickup_lng=76.9558,
        drop_lat=11.0300, drop_lng=76.9700,
    )
    ride = make_request(
        request_type="ride",
        pickup_lat=11.0200, pickup_lng=76.9700,
        drop_lat=11.0350, drop_lng=76.9850,
    )
    return food, ride


def test_static_mode_independent_of_learning_state(db, pair_requests, learning_state):
    r1, r2 = pair_requests

    base = calc.compute([r1, r2], db, mode="static")
    polluted = learning_state(corridor_multipliers={"food|ride": 3.0})
    alt = calc.compute([r1, r2], db, mode="static", learning_state=polluted)

    assert alt.compatibility_score == base.compatibility_score
    assert alt.estimated_delay_min == base.estimated_delay_min
    assert alt.factor_scores == base.factor_scores


def test_adaptive_refit_disabled_ignores_corridor_multipliers(
    db, pair_requests, learning_state, set_config
):
    r1, r2 = pair_requests
    set_config("admfe.refit_enabled", "false")

    base = calc.compute([r1, r2], db, mode="adaptive",
                        learning_state=learning_state())
    scaled = calc.compute([r1, r2], db, mode="adaptive",
                          learning_state=learning_state(
                              corridor_multipliers={"food|ride": 2.0}
                          ))

    assert scaled.estimated_delay_min == pytest.approx(
        base.estimated_delay_min, abs=1e-9
    )


def test_adaptive_refit_enabled_scales_matching_corridor(
    db, pair_requests, learning_state
):
    r1, r2 = pair_requests

    base = calc.compute([r1, r2], db, mode="adaptive",
                        learning_state=learning_state())
    scaled = calc.compute([r1, r2], db, mode="adaptive",
                          learning_state=learning_state(
                              corridor_multipliers={"food|ride": 2.0}
                          ))

    assert base.estimated_delay_min > 0.0
    assert scaled.estimated_delay_min == pytest.approx(
        2.0 * base.estimated_delay_min, abs=0.5
    )
    assert scaled.estimated_delay_min > base.estimated_delay_min


def test_adaptive_refit_enabled_ignores_non_matching_corridor(
    db, make_request, learning_state
):
    r1 = make_request(
        request_type="food",
        pickup_lat=11.0168, pickup_lng=76.9558,
        drop_lat=11.0300, drop_lng=76.9700,
    )
    r2 = make_request(
        request_type="food",
        pickup_lat=11.0200, pickup_lng=76.9700,
        drop_lat=11.0350, drop_lng=76.9850,
    )

    base = calc.compute([r1, r2], db, mode="adaptive",
                        learning_state=learning_state())
    alt = calc.compute([r1, r2], db, mode="adaptive",
                       learning_state=learning_state(
                           corridor_multipliers={"food|ride": 2.0}
                       ))

    # corridor is "food" — multiplier for "food|ride" must not apply
    assert alt.estimated_delay_min == base.estimated_delay_min
