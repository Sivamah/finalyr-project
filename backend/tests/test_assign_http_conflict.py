"""
Regression: HTTP-level assignment conflicts + API validation.

Proves at the route layer (not just the unit layer) that:
  - assigning the same request twice returns HTTP 409 (conflict), never a
    duplicate Active trip / duplicate DriverAssignment
  - completed requests cannot be dispatched again (409)
  - missing request ids -> 400, duplicate request_ids -> 400
  - optimize/route rejects duplicate request_ids (400) and references a
    nonexistent driver/vehicle as 404 instead of silently accepting them

The TestClient uses dependency overrides for BOTH the auth dependency and
`get_db`, so the request handlers run against a fresh in-memory SQLite
schema — the dev/demo database is never mutated (the app lifespan still runs
its idempotent create_all/seed against the real engine, as it already does in
test_datasets_upload.py).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api import deps as api_deps
from app.db.database import Base
from app.db.models import Driver, DriverAssignment, SimulationRequest, Trip, User, Vehicle

ANCHOR_LAT, ANCHOR_LNG = 11.0168, 76.9558


@pytest.fixture()
def env():
    """Hermetic TestClient running handlers against an in-memory SQLite DB."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def override_get_db():
        return session

    def override_get_current_user():
        return User(id=1, email="test@test.com", role="Admin")

    # Snapshot/restore instead of blanket clear(): other test modules register
    # module-level overrides at import time (e.g. test_datasets_upload.py) and
    # would be silently disabled by a blanket clear() during teardown.
    previous_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[api_deps.get_current_user] = override_get_current_user
    app.dependency_overrides[api_deps.get_db] = override_get_db
    with TestClient(app) as client:
        yield client, session
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)
    session.close()
    engine.dispose()


def _seed_fleet(db):
    v = Vehicle(
        provider_id=1, name="V1", vehicle_type="Car", capacity=4,
        status="Available", current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG,
    )
    db.add(v)
    db.flush()
    d = Driver(
        provider_id=1, name="D1", status="Available",
        current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG,
        assigned_vehicle_id=v.id,
    )
    db.add(d)
    db.flush()
    return d, v


def _pair(db, **kw):
    r1 = SimulationRequest(
        request_type="ride",
        pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG,
        drop_lat=11.02, drop_lng=76.97,
        demand=1, priority="Medium", weight_kg=0.0,
        status="Pending", **kw,
    )
    r2 = SimulationRequest(
        request_type="ride",
        pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG,
        drop_lat=11.021, drop_lng=76.972,
        demand=1, priority="Medium", weight_kg=0.0,
        status="Pending",
    )
    db.add_all([r1, r2])
    db.flush()
    return r1, r2


def test_assign_driver_twice_returns_409(env):
    client, db = env
    _seed_fleet(db)
    r1, r2 = _pair(db)

    first = client.post("/api/dmfe/assign/driver", json={"request_ids": [r1.id, r2.id]})
    assert first.status_code == 200, first.text
    assert first.json()["trip"]["status"] == "Active"

    # Same batch / same requests assigned a second time -> 409 conflict,
    # and NO second Active trip / assignment is created.
    second = client.post("/api/dmfe/assign/driver", json={"request_ids": [r1.id, r2.id]})
    assert second.status_code == 409, second.text
    assert "Cannot dispatch" in second.json()["detail"]

    active_trips = db.query(Trip).filter(Trip.status == "Active").all()
    assignments = db.query(DriverAssignment).all()
    assert len(active_trips) == 1
    assert len(assignments) == 1


def test_assign_driver_completed_request_returns_409(env):
    client, db = env
    _seed_fleet(db)
    done = SimulationRequest(
        request_type="ride",
        pickup_lat=ANCHOR_LAT, pickup_lng=ANCHOR_LNG,
        drop_lat=11.02, drop_lng=76.97,
        status="Completed",
    )
    db.add(done)
    db.flush()

    resp = client.post("/api/dmfe/assign/driver", json={"request_ids": [done.id]})
    assert resp.status_code == 409, resp.text
    assert "Cannot dispatch" in resp.json()["detail"]
    assert db.query(Trip).count() == 0


def test_assign_driver_missing_request_returns_400(env):
    client, _ = env
    resp = client.post("/api/dmfe/assign/driver", json={"request_ids": [999999]})
    assert resp.status_code == 400, resp.text
    assert "not found" in resp.json()["detail"]


def test_assign_driver_duplicate_request_ids_returns_400(env):
    client, db = env
    _seed_fleet(db)
    r1, r2 = _pair(db)

    resp = client.post(
        "/api/dmfe/assign/driver",
        json={"request_ids": [r1.id, r1.id, r2.id]},
    )
    assert resp.status_code == 400, resp.text
    assert "Duplicate" in resp.json()["detail"]


def test_optimize_route_duplicate_request_ids_returns_400(env):
    client, db = env
    r1, r2 = _pair(db)

    resp = client.post(
        "/api/dmfe/optimize/route",
        json={"request_ids": [r1.id, r1.id, r2.id]},
    )
    assert resp.status_code == 400, resp.text
    assert "Duplicate" in resp.json()["detail"]


def test_optimize_route_invalid_driver_returns_404(env):
    client, db = env
    r1, r2 = _pair(db)

    resp = client.post(
        "/api/dmfe/optimize/route",
        json={"request_ids": [r1.id, r2.id], "driver_id": 424242},
    )
    assert resp.status_code == 404, resp.text
    assert "Driver #424242 not found" in resp.json()["detail"]


def test_optimize_route_invalid_vehicle_returns_404(env):
    client, db = env
    r1, r2 = _pair(db)

    resp = client.post(
        "/api/dmfe/optimize/route",
        json={"request_ids": [r1.id, r2.id], "vehicle_id": 424243},
    )
    assert resp.status_code == 404, resp.text
    assert "Vehicle #424243 not found" in resp.json()["detail"]


def test_optimize_route_nonexistent_batch_returns_404(env):
    client, _ = env
    resp = client.post("/api/dmfe/optimize/route", json={"batch_id": 999999})
    assert resp.status_code == 404, resp.text
    assert "DMFE batch not found" in resp.json()["detail"]