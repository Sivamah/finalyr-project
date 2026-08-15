"""
Pipeline accounting invariant — the regression guard for P0-1.

The module contract in ``app/dmfe/pipeline.py`` states:

    A request is dispatched either in a Shared Trip or as an Individual
    Trip — never both, never skipped silently.

Before the P0-1 fix, Gate D wrote ``covered_ids[r.id] = "high_priority_reject"``
while the individual-dispatch loop skipped on *membership* (``req.id in
covered_ids``) rather than on the value.  Gate-D rejects were therefore counted
in ``requests_processed``, never dispatched, and never listed in
``result.unassigned`` — they vanished.  Because Gate D only fires on
High-priority batches, the requests that disappeared were the most urgent ones.

These tests assert the accounting closes, counting *actual request ids* rather
than assuming two requests per shared trip (triples are possible).
"""

from __future__ import annotations

import pytest

from app.dmfe.compatibility import clear_config_cache
from app.dmfe.pipeline import PipelineRunner

ANCHOR_LAT, ANCHOR_LNG = 11.0168, 76.9558


# ── helpers ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _fresh_config_cache():
    """The SystemConfig TTL cache is module-level; clear it around each test."""
    clear_config_cache()
    yield
    clear_config_cache()


def _fleet(db, make_driver, make_vehicle, n):
    """n Available driver+vehicle pairs parked at the Coimbatore anchor."""
    pairs = []
    for i in range(n):
        v = make_vehicle(name=f"Vehicle {i}", current_lat=ANCHOR_LAT,
                         current_lng=ANCHOR_LNG)
        d = make_driver(name=f"Driver {i}", current_lat=ANCHOR_LAT,
                        current_lng=ANCHOR_LNG, assigned_vehicle_id=v.id)
        pairs.append((d, v))
    db.flush()
    return pairs


def _accounted_ids(result):
    """Every request id the run claims to have handled, dispatched or not."""
    ids = set()
    for d in result.dispatches:
        ids.update(d.get("request_ids") or [])
    for u in result.unassigned:
        ids.update(u.get("request_ids") or [])
    return ids


def _assert_accounting_closes(result, pending_ids):
    """
    THE invariant.  Every processed request must be dispatched (shared or
    individual) or explicitly reported as unassigned with a reason — nothing
    may silently disappear between the two.
    """
    accounted = _accounted_ids(result)
    lost = set(pending_ids) - accounted
    assert not lost, (
        f"requests silently dropped: {sorted(lost)} — "
        f"processed={result.requests_processed} "
        f"shared={result.shared_trips} individual={result.individual_trips} "
        f"unassigned={len(result.unassigned)}"
    )
    assert len(accounted) == result.requests_processed, (
        f"accounted {len(accounted)} ids but requests_processed="
        f"{result.requests_processed}"
    )
    # Dispatched and unassigned sets must be disjoint: never both.
    dispatched = set()
    for d in result.dispatches:
        dispatched.update(d.get("request_ids") or [])
    unassigned = set()
    for u in result.unassigned:
        unassigned.update(u.get("request_ids") or [])
    assert not (dispatched & unassigned), (
        f"requests both dispatched and unassigned: {sorted(dispatched & unassigned)}"
    )
    # Every unassigned entry must carry a reason.
    for u in result.unassigned:
        assert u.get("reason"), f"unassigned entry without a reason: {u}"


# ── 1. Mixed queue, drivers available ───────────────────────────────────────

def test_every_request_is_dispatched_or_unassigned(
    db, make_request, make_driver, make_vehicle
):
    _fleet(db, make_driver, make_vehicle, 4)

    pending = [
        make_request(pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG,
                     drop_lat=11.02, drop_lng=76.97),
        make_request(pickup_lat=ANCHOR_LAT + 0.001, pickup_lng=ANCHOR_LNG,
                     drop_lat=11.021, drop_lng=76.971),
        make_request(pickup_lat=11.10, pickup_lng=77.05,
                     drop_lat=11.15, drop_lng=77.10),
        make_request(pickup_lat=11.30, pickup_lng=76.70,
                     drop_lat=11.35, drop_lng=76.65),
    ]
    db.commit()
    ids = [r.id for r in pending]

    result = PipelineRunner().run(db)

    assert result.requests_processed == len(ids)
    _assert_accounting_closes(result, ids)


# ── 2. Gate-D rejects must fall through, not vanish ─────────────────────────

def test_gate_d_rejects_are_not_silently_dropped(
    db, make_request, make_driver, make_vehicle, set_config
):
    """
    P0-1 reproduction.  ``max_allowed_delay_min`` is driven to ~0 so that any
    shared batch containing a High-priority request violates Gate D.  Those
    requests must still be dispatched individually (or reported unassigned) —
    before the fix they were dropped from the run entirely.
    """
    set_config("max_allowed_delay_min", 0.01)
    db.commit()
    clear_config_cache()

    _fleet(db, make_driver, make_vehicle, 4)

    high_pair = [
        make_request(priority="High",
                     pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG,
                     drop_lat=11.02, drop_lng=76.97),
        make_request(priority="High",
                     pickup_lat=ANCHOR_LAT + 0.001, pickup_lng=ANCHOR_LNG,
                     drop_lat=11.021, drop_lng=76.971),
    ]
    normal_pair = [
        make_request(priority="Medium",
                     pickup_lat=11.10, pickup_lng=77.05,
                     drop_lat=11.15, drop_lng=77.10),
        make_request(priority="Medium",
                     pickup_lat=11.101, pickup_lng=77.051,
                     drop_lat=11.151, drop_lng=77.101),
    ]
    db.commit()
    ids = [r.id for r in high_pair + normal_pair]
    high_ids = {r.id for r in high_pair}

    result = PipelineRunner().run(db)

    assert result.requests_processed == len(ids)
    _assert_accounting_closes(result, ids)

    # The specific regression: the High-priority requests are accounted for.
    assert high_ids <= _accounted_ids(result), (
        f"Gate-D rejected High-priority requests {sorted(high_ids)} left no "
        f"trace in the run"
    )


# ── 3. No-driver control: everything must land in `unassigned` ──────────────

def test_no_drivers_puts_every_request_in_unassigned(db, make_request):
    """
    Driver starvation is the case that used to lose the most metadata.  With
    no fleet at all nothing can dispatch, so every request must appear in
    ``unassigned`` with a reason — none may be silently swallowed.
    """
    pending = [
        make_request(pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG),
        make_request(pickup_lat=ANCHOR_LAT + 0.001, pickup_lng=ANCHOR_LNG),
        make_request(pickup_lat=11.10, pickup_lng=77.05,
                     drop_lat=11.15, drop_lng=77.10),
    ]
    db.commit()
    ids = [r.id for r in pending]

    result = PipelineRunner().run(db)

    assert result.requests_processed == len(ids)
    _assert_accounting_closes(result, ids)
    if result.shared_trips == 0 and result.individual_trips == 0:
        unassigned_ids = set()
        for u in result.unassigned:
            unassigned_ids.update(u.get("request_ids") or [])
        assert unassigned_ids == set(ids)


# ── 4. Repeated run is a no-op ──────────────────────────────────────────────

def test_second_run_with_no_new_requests_dispatches_nothing(
    db, make_request, make_driver, make_vehicle
):
    _fleet(db, make_driver, make_vehicle, 4)
    pending = [
        make_request(pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG),
        make_request(pickup_lat=ANCHOR_LAT + 0.001, pickup_lng=ANCHOR_LNG),
    ]
    db.commit()
    ids = [r.id for r in pending]

    runner = PipelineRunner()
    first = runner.run(db)
    _assert_accounting_closes(first, ids)

    from app.db.models import SimulationRequest
    still_pending = (
        db.query(SimulationRequest)
        .filter(SimulationRequest.status == "Pending")
        .count()
    )

    second = runner.run(db)
    assert second.requests_processed == still_pending
    if still_pending == 0:
        assert second.shared_trips == 0
        assert second.individual_trips == 0
        assert second.dispatches == []
    else:
        _assert_accounting_closes(second, [r.id for r in (
            db.query(SimulationRequest)
            .filter(SimulationRequest.status == "Pending")
            .all()
        )])
