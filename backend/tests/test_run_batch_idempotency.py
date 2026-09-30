"""
Regression: /run (PipelineRunner) must not duplicate DMFEBatch rows.

Audit finding: the dequeue step (PipelineRunner.run) never advanced
SimulationRequest.status for requests that could not be dispatched, so
re-running the pipeline on the same pending queue inserted a brand-new
DMFEBatch row with the SAME deterministic batch_code every time.  It also
re-created the exact row a prior /analyze had already persisted, leaving the
analyze row stuck at status="Pending" (a phantom).  Both inflated
/statistics and /history.

decision_engine already de-dupes its own rows via `_find_existing_live_batch`;
this pins the mirror fix in pipeline.py's `_persist_batch` and asserts on the
REAL database state (row counts and ids), not just on the returned result.
"""

from __future__ import annotations

import pytest

from app.dmfe.compatibility import clear_config_cache
from app.dmfe.decision_engine import decision_engine
from app.dmfe.models import DMFEBatch
from app.dmfe.pipeline import PipelineRunner

ANCHOR_LAT, ANCHOR_LNG = 11.0168, 76.9558


@pytest.fixture(autouse=True)
def _fresh_config_cache():
    """The SystemConfig TTL cache is module-level; clear it around each test."""
    clear_config_cache()
    yield
    clear_config_cache()


def _batch_codes(db):
    return sorted(b.batch_code for b in db.query(DMFEBatch).all())


def _batch_ids(db):
    return sorted(b.id for b in db.query(DMFEBatch).all())


def _close_pair(db, make_request):
    r1 = make_request(pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG,
                      drop_lat=11.02, drop_lng=76.97)
    r2 = make_request(pickup_lat=ANCHOR_LAT + 0.001, pickup_lng=ANCHOR_LNG,
                      drop_lat=11.021, drop_lng=76.971)
    db.commit()
    return r1, r2


# ── 1. Repeated /run on unassignable requests must not grow the table ────────

def test_repeated_run_unassignable_requests_keep_row_count(db, make_request):
    """
    No fleet at all → every batch dispatch fails, requests stay Pending, and
    the batch rows are left Rejected.  A second /run over the SAME pending
    queue must REUSE those rejected rows instead of inserting identical
    batch_code rows again.
    """
    _close_pair(db, make_request)

    runner = PipelineRunner()
    runner.run(db)
    codes1 = _batch_codes(db)
    ids1 = _batch_ids(db)
    assert len(ids1) == 1, f"expected exactly one shared batch row, got {codes1}"

    runner.run(db)
    codes2 = _batch_codes(db)
    ids2 = _batch_ids(db)

    assert ids2 == ids1, (
        f"second /run on an unchanged unassignable queue duplicated batch "
        f"rows: ids {ids1} -> {ids2}"
    )
    assert codes2 == codes1
    assert len(set(codes2)) == len(codes2), "duplicate batch_code present"


# ── 2. analyze → run reuses the analyze-created row (no phantom Pending) ─────

def test_analyze_then_run_reuses_same_batch_row_not_a_copy(
    db, make_request, make_driver, make_vehicle
):
    """
    With a fleet available: /analyze persists a shared batch (Pending).
    A following /run must dispatch the SAME row (status → Dispatched) rather
    than inserting a second row and leaving the analyze row stuck at Pending.
    """
    make_vehicle(current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG)
    make_driver(current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG)
    _close_pair(db, make_request)
    db.commit()

    decision_engine.run_analysis(db)
    codes_after_analyze = _batch_codes(db)
    ids_after_analyze = _batch_ids(db)
    assert len(ids_after_analyze) == 1, codes_after_analyze
    analyze_batch_id = ids_after_analyze[0]

    PipelineRunner().run(db)
    rows = db.query(DMFEBatch).all()

    assert [b.id for b in rows] == [analyze_batch_id], (
        "/run must dispatch the existing analyze-created batch row, not copy it"
    )
    assert rows[0].status == "Dispatched"
    assert db.query(DMFEBatch).filter(DMFEBatch.status == "Pending").count() == 0, (
        "phantom Pending batch left behind by analyze→run cycle"
    )


# ── 3. Partial assignment retry reuses rows; only new requests add rows ──────

def test_partial_retry_does_not_duplicate_and_new_requests_are_added(
    db, make_request, make_driver, make_vehicle
):
    """
    One driver/vehicle available: the close pair dispatches, but a far
    high-demand solo request (demand > capacity) cannot be assigned and stays
    Pending with a Rejected TRIP row.  A retry /run reuses both rows; adding a
    genuinely new request then creates exactly one new row.
    """
    make_vehicle(current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG, capacity=4)
    make_driver(current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG)
    _close_pair(db, make_request)
    stuck = make_request(
        pickup_lat=11.30, pickup_lng=76.70,
        drop_lat=11.35, drop_lng=76.65,
        demand=5,
    )
    db.commit()

    runner = PipelineRunner()
    runner.run(db)
    ids1 = _batch_ids(db)
    assert len(ids1) == 2, f"expected shared + individual rows, got {_batch_codes(db)}"

    runner.run(db)
    ids2 = _batch_ids(db)
    assert ids2 == ids1, (
        f"partial-retry /run duplicated rows: {ids1} -> {ids2}"
    )

    brand_new = make_request(pickup_lat=10.99, pickup_lng=77.05,
                             drop_lat=10.95, drop_lng=77.08)
    db.commit()
    runner.run(db)
    rows = db.query(DMFEBatch).all()
    assert len(rows) == 3, (
        f"only the new request should add a row; got {_batch_codes(db)}"
    )
    assert len({b.batch_code for b in rows}) == 3, "duplicate batch_code present"
    assert any(batch_code == f"TRIP-{brand_new.id:04d}" for batch_code in _batch_codes(db))


# ── 4. Duplicate request rows cannot accumulate across many retries ──────────

def test_many_retries_still_one_row_per_request_set(
    db, make_request, make_driver, make_vehicle
):
    """
    Loop-shaped stress: three consecutive /run attempts over a queue that can
    only PARTLY dispatch must keep "one row per request set" — no exponential
    or linear row growth from repeated failures.
    """
    make_vehicle(current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG, capacity=4)
    make_driver(current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG)
    _close_pair(db, make_request)
    stuck_a = make_request(pickup_lat=11.30, pickup_lng=76.70,
                           drop_lat=11.35, drop_lng=76.65, demand=5)
    stuck_b = make_request(pickup_lat=10.99, pickup_lng=77.05,
                           drop_lat=10.95, drop_lng=77.08, demand=5)
    db.commit()

    runner = PipelineRunner()
    runner.run(db)
    base_ids = _batch_ids(db)
    assert len(base_ids) == 3

    for _ in range(3):
        runner.run(db)
        assert _batch_ids(db) == base_ids, (
            f"repeat /run grew the batch table: {base_ids} -> {_batch_ids(db)}"
        )