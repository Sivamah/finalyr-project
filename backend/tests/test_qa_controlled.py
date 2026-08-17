"""
QA-controlled software tests (P5) — isolated in-memory SQLite per test.

These tests never touch the dev/demo database: every test builds its own
in-memory schema, so the simulation, fleet, and dashboard data stay intact.
They exercise ordinary integration behaviour of the DMFE pipeline:

    A. Compatible requests + available fleet  -> batch created & dispatched
    B. No drivers available                  -> requests clearly rejected
    C. Fresh Active trip                     -> stays Active (not force-completed)
    D. Stale trip                            -> released, driver/vehicle freed
    E. Double pipeline run                   -> no duplicate assignment
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.dmfe.compatibility import clear_config_cache
from app.dmfe.driver_selection import complete_stale_trips
from app.dmfe.models import DMFEBatch
from app.dmfe.pipeline import PipelineRunner
from app.db.models import Driver, SimulationRequest, Trip, Vehicle

ANCHOR_LAT, ANCHOR_LNG = 11.0168, 76.9558


@pytest.fixture(autouse=True)
def _fresh_config_cache():
    """The SystemConfig TTL cache is module-level; clear it around each test."""
    clear_config_cache()
    yield
    clear_config_cache()


def _fleet(db, make_driver, make_vehicle, n):
    pairs = []
    for i in range(n):
        v = make_vehicle(name=f"QA Vehicle {i}")
        d = make_driver(name=f"QA Driver {i}", assigned_vehicle_id=v.id)
        pairs.append((d, v))
    db.flush()
    return pairs


def _accounted_ids(result):
    ids = set()
    for d in result.dispatches:
        ids.update(d.get("request_ids") or [])
    for u in result.unassigned:
        ids.update(u.get("request_ids") or [])
    return ids


def _trip_ids_for(db, request_ids):
    trips = []
    for t in db.query(Trip).all():
        import json as _json
        ids = _json.loads(t.request_ids_json or "[]")
        if set(ids) & set(request_ids):
            trips.append(t)
    return trips


# ── A. Compatible requests + available fleet → batch created ────────────────

def test_compatible_pair_with_fleet_is_batched_and_dispatched(
    db, make_request, make_driver, make_vehicle,
):
    _fleet(db, make_driver, make_vehicle, 1)

    ts = datetime.now(timezone.utc)
    reqs = [
        make_request(
            pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG,
            drop_lat=11.02, drop_lng=76.97,
            demand=1, request_timestamp=ts,
        ),
        make_request(
            pickup_lat=ANCHOR_LAT + 0.0005, pickup_lng=ANCHOR_LNG + 0.0005,
            drop_lat=11.021, drop_lng=76.971,
            demand=1, request_timestamp=ts + timedelta(minutes=1),
        ),
    ]
    db.commit()
    ids = [r.id for r in reqs]

    result = PipelineRunner().run(db)

    # Every request was handled, nothing vanished.
    assert _accounted_ids(result) == set(ids)
    # The pair must actually be batched: a shared trip is created.
    assert result.shared_trips >= 1, f"expected a shared trip, got {result}"

    trips = _trip_ids_for(db, ids)
    assert trips, "no trip references the two requests"
    assert any(t.is_shared for t in trips), "trip is not marked shared"

    batches = (
        db.query(DMFEBatch)
        .filter(DMFEBatch.decision == "Compatible")
        .all()
    )
    assert batches, "no Compatible batch rows were created"

    # Requests left the queue (Assigned until the trip completes — the
    # completion path is covered by tests C/D).
    assert any(t.driver_id is not None for t in trips)
    for r in db.query(SimulationRequest).filter(SimulationRequest.id.in_(ids)).all():
        assert r.status != "Pending", f"request {r.id} still pending after dispatch"


# ── B. No drivers → every request clearly rejected ───────────────────────────

def test_no_drivers_rejects_every_request_with_reason(
    db, make_request,
):
    reqs = [
        make_request(pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG),
        make_request(pickup_lat=ANCHOR_LAT + 0.001, pickup_lng=ANCHOR_LNG),
    ]
    db.commit()
    ids = [r.id for r in reqs]

    result = PipelineRunner().run(db)

    assert _accounted_ids(result) == set(ids)
    assert result.shared_trips == 0
    assert result.individual_trips == 0
    unassigned_ids = set()
    for u in result.unassigned:
        assert u.get("reason"), f"unassigned entry without a reason: {u}"
        unassigned_ids.update(u.get("request_ids") or [])
    assert unassigned_ids == set(ids), (
        f"unassigned {sorted(unassigned_ids)} != {sorted(ids)}"
    )


# ── C. Fresh Active trip stays active ────────────────────────────────────────

def test_fresh_active_trip_is_not_force_completed(
    db, make_driver, make_vehicle, make_request, make_trip,
):
    d, v = _fleet(db, make_driver, make_vehicle, 1)[0]
    d.status = "Busy"
    v.status = "Busy"
    req = make_request(pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG)
    trip = make_trip(
        requests=[req],
        status="Active",
        driver_id=d.id,
        vehicle_id=v.id,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        total_duration_min=30.0,
    )
    db.commit()

    released = complete_stale_trips(db, max_age_min=45.0)

    assert released == 0, "a 5-minute-old trip must not be force-completed"
    db.refresh(trip)
    db.refresh(d)
    db.refresh(v)
    assert trip.status == "Active"
    assert d.status == "Busy", "driver was released mid-trip"
    assert v.status == "Busy", "vehicle was released mid-trip"


# ── D. Stale trip is released, driver & vehicle freed ────────────────────────

def test_stale_trip_is_released_and_resources_freed(
    db, make_driver, make_vehicle, make_request, make_trip,
):
    d, v = _fleet(db, make_driver, make_vehicle, 1)[0]
    d.status = "Busy"
    v.status = "Busy"
    req = make_request(pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG)
    trip = make_trip(
        requests=[req],
        status="Active",
        driver_id=d.id,
        vehicle_id=v.id,
        created_at=datetime.now(timezone.utc) - timedelta(hours=3),
        total_duration_min=30.0,
    )
    db.commit()

    released = complete_stale_trips(db, max_age_min=45.0)

    assert released == 1, "the 3-hour-old trip must be considered stale"
    db.refresh(trip)
    db.refresh(d)
    db.refresh(v)
    db.refresh(req)
    assert trip.status == "Completed"
    assert trip.completed_at is not None
    assert d.status == "Available", "driver not released after stale completion"
    assert v.status == "Available", "vehicle not released after stale completion"
    assert req.status == "Completed", "request not marked completed"


# ── E. Double pipeline run → no duplicate assignment ─────────────────────────

def test_double_run_never_duplicates_assignments(
    db, make_request, make_driver, make_vehicle,
):
    _fleet(db, make_driver, make_vehicle, 2)
    reqs = [
        make_request(pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG),
        make_request(pickup_lat=ANCHOR_LAT + 0.001, pickup_lng=ANCHOR_LNG),
    ]
    db.commit()
    ids = [r.id for r in reqs]

    runner = PipelineRunner()
    first = runner.run(db)
    assert _accounted_ids(first) == set(ids)

    trips_after_first = _trip_ids_for(db, ids)
    assert trips_after_first, "first run created no trips"

    second = runner.run(db)
    assert second.requests_processed == 0, (
        f"second run processed {second.requests_processed} requests on an "
        f"empty queue"
    )
    assert second.dispatches == []

    trips_after_second = _trip_ids_for(db, ids)
    assert len(trips_after_second) == len(trips_after_first), (
        "second run created additional trips for the same requests"
    )

    # Every request id appears in exactly one trip (no double assignment).
    from collections import Counter
    from app.core.json_utils import json_loads

    occurrences = Counter()
    for t in trips_after_second:
        occurrences.update(json_loads(t.request_ids_json, []))
    for rid in ids:
        assert occurrences[rid] == 1, (
            f"request {rid} assigned to {occurrences[rid]} trips"
        )