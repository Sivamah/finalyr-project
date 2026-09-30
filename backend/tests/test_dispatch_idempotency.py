"""
Regression: dispatch idempotency — no re-dispatch of already-handled requests.

Audit finding #1 (HIGH): /assign/driver re-dispatched requests that were
already Assigned (duplicate Active trip 4453) or already Completed (trip
4454 revived request 6562).  The lifecycle guard in `dispatch_trip` must
reject any request not in an assignable state, while leaving the normal
Pending/Evaluated dispatch path untouched.
"""

from __future__ import annotations

import pytest

from app.dmfe.driver_selection import dispatch_trip
from app.dmfe.models import DMFEBatch

ANCHOR_LAT, ANCHOR_LNG = 11.0168, 76.9558


def _seed_pair(db, make_driver, make_vehicle):
    """Book-keeping-free seed: one implementation checkbox."""
    v = make_vehicle(current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG)
    d = make_driver(current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG,
                    assigned_vehicle_id=v.id)
    return d, v


def test_rejects_assigned_request(db, make_driver, make_vehicle, make_request):
    _seed_pair(db, make_driver, make_vehicle)
    req = make_request(status="Assigned")
    db.flush()

    with pytest.raises(ValueError) as exc:
        dispatch_trip(db, [req])
    assert "Cannot dispatch" in str(exc.value)
    assert f"#{req.id}" in str(exc.value)


def test_rejects_completed_request(db, make_driver, make_vehicle, make_request):
    _seed_pair(db, make_driver, make_vehicle)
    req = make_request(status="Completed")
    db.flush()

    with pytest.raises(ValueError) as exc:
        dispatch_trip(db, [req])
    assert "Cannot dispatch" in str(exc.value)
    assert "Completed" in str(exc.value)


def test_rejects_mixed_terminal_and_pending(db, make_driver, make_vehicle, make_request):
    _seed_pair(db, make_driver, make_vehicle)
    pending = make_request(status="Pending")
    done = make_request(status="Completed")
    db.flush()

    with pytest.raises(ValueError) as exc:
        dispatch_trip(db, [pending, done])
    assert f"#{done.id} (Completed)" in str(exc.value)


def test_pending_dispatch_still_succeeds(db, make_driver, make_vehicle, make_request):
    """The guard must not over-block the normal path."""
    _seed_pair(db, make_driver, make_vehicle)
    r1 = make_request(pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG,
                      drop_lat=11.02, drop_lng=76.97)
    r2 = make_request(pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG,
                      drop_lat=11.021, drop_lng=76.972)
    batch = DMFEBatch(
        batch_code="BATCH-TEST-01",
        request_ids_json="[]",
        decision="Compatible",
        status="Pending",
    )
    db.add(batch)
    db.flush()
    batch.request_ids_json = f"[{r1.id}, {r2.id}]"
    db.flush()

    outcome = dispatch_trip(db, [r1, r2], batch=batch,
                            trip_key=batch.batch_code, commit=True)
    trip = outcome["trip"]
    assert trip.status == "Active"
    assert r1.status == "Assigned"
    assert r2.status == "Assigned"
    assert batch.status == "Dispatched"

    # Second dispatch of the SAME requests must now fail the guard —
    # even though the driver is Busy, the request-state guard fires first.
    db.flush()
    with pytest.raises(ValueError) as exc:
        dispatch_trip(db, [r1, r2], batch=batch,
                      trip_key=batch.batch_code, commit=False)
    assert "Cannot dispatch" in str(exc.value)


def test_evaluated_status_is_assignable(db, make_driver, make_vehicle, make_request):
    """Requests evaluated by /analyze (status Evaluated) remain assignable."""
    _seed_pair(db, make_driver, make_vehicle)
    req = make_request(status="Evaluated")
    db.flush()

    outcome = dispatch_trip(db, [req], commit=True)
    assert outcome["trip"].status == "Active"
    assert req.status == "Assigned"


def test_rejects_request_inside_active_trip(db, make_driver, make_vehicle, make_request):
    """
    Active trip -> assign again must be rejected.

    A request that is part of a LIVE (status="Active") trip is Assigned; the
    lifecycle guard must refuse to dispatch it a second time so no duplicate
    Active trip is ever created for it.
    """
    _seed_pair(db, make_driver, make_vehicle)
    req = make_request(status="Assigned")
    db.flush()
    from app.db.models import Trip

    trip = Trip(
        trip_code="TRIP-ACTIVE-GUARD",
        driver_id=None,
        vehicle_id=None,
        request_ids_json=f"[{req.id}]",
        is_shared=False,
        status="Active",
        total_distance_km=0.0,
    )
    db.add(trip)
    db.flush()

    with pytest.raises(ValueError) as exc:
        dispatch_trip(db, [req])
    assert "Cannot dispatch" in str(exc.value)
    assert f"#{req.id}" in str(exc.value)

    # And the Active trip itself must still be the only trip for the request.
    trips = db.query(Trip).filter(Trip.trip_code == "TRIP-ACTIVE-GUARD").all()
    assert len(trips) == 1
    assert trips[0].status == "Active"