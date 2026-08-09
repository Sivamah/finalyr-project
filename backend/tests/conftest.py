"""
Shared pytest fixtures — in-memory SQLite per test.

Each test gets a fresh engine + schema + session, so SystemConfig state
(learning/refit flags, learning_state JSON) never leaks between tests.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.database import Base  # noqa: E402
from app.db.models import (  # noqa: E402,F401
    Driver,
    DriverAssignmentHistory,
    SimulationRequest,
    SystemConfig,
    Trip,
    Vehicle,
)
from app.dmfe.models import DMFEBatch  # noqa: E402,F401
import app.db.models  # noqa: E402,F401  (registers core tables)
import app.dmfe.models  # noqa: E402,F401  (registers dmfe_batches)

_trip_seq = itertools.count(1)


@pytest.fixture()
def db():
    """Fresh in-memory SQLite database + session, per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def make_request(db):
    """Factory for minimal SimulationRequest rows with sane defaults."""
    def _make(**overrides):
        defaults = dict(
            request_type="ride",
            pickup_lat=11.0168, pickup_lng=76.9558,
            drop_lat=11.02, drop_lng=76.97,
            demand=1,
            priority="Medium",
            weight_kg=0.0,
            status="Pending",
        )
        defaults.update(overrides)
        r = SimulationRequest(**defaults)
        db.add(r)
        db.flush()
        return r

    return _make


@pytest.fixture()
def make_batch(db):
    """Factory for minimal DMFEBatch rows (linked to requests if given)."""
    def _make(requests=None, **overrides):
        ids = [r.id for r in requests] if requests else []
        defaults = dict(
            batch_code=f"BATCH-{next(_trip_seq):05d}",
            request_ids_json=json.dumps(ids),
            compatibility_score=80.0,
            decision="Compatible",
            status="Pending",
            estimated_delay_min=0.0,
            predicted_utilization_pct=0.0,
        )
        defaults.update(overrides)
        b = DMFEBatch(**defaults)
        db.add(b)
        db.flush()
        return b

    return _make


@pytest.fixture()
def make_trip(db):
    """Factory for minimal Trip rows (linked to requests/batch if given)."""
    def _make(requests=None, batch=None, **overrides):
        ids = [r.id for r in requests] if requests else []
        defaults = dict(
            trip_code=f"TRIP-{next(_trip_seq):05d}",
            request_ids_json=json.dumps(ids),
            is_shared=len(ids) > 1,
            status="Completed",
            max_delay_min=0.0,
            utilization_pct=50.0,
            fuel_l=0.5,
            total_duration_min=15.0,
        )
        defaults.update(overrides)
        if batch is not None:
            defaults["batch_id"] = batch.id
        t = Trip(**defaults)
        db.add(t)
        db.flush()
        return t

    return _make


@pytest.fixture()
def set_config(db):
    """Upsert a SystemConfig row (string values, like the runtime writers)."""
    def _set(key: str, value) -> None:
        row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if row:
            row.value = str(value)
        else:
            db.add(SystemConfig(
                category="ai_rules", key=key,
                value=str(value), data_type="string",
            ))
        db.flush()

    return _set


@pytest.fixture()
def learning_state():
    """Deep-copied EMPTY_STATE with optional corridor factors injected."""
    from app.dmfe.adaptive.learning import EMPTY_STATE

    def _make(corridor_multipliers=None, corridor_utilization_bias=None):
        state = json.loads(json.dumps(EMPTY_STATE))
        if corridor_multipliers:
            state["corridor_multipliers"] = dict(corridor_multipliers)
        if corridor_utilization_bias:
            state["corridor_utilization_bias"] = dict(corridor_utilization_bias)
        return state

    return _make


@pytest.fixture()
def make_driver(db):
    """Factory for minimal Driver rows (Available, at Coimbatore anchor)."""
    def _make(**overrides):
        defaults = dict(
            name="Driver T",
            status="Available",
            current_lat=11.0168,
            current_lng=76.9558,
        )
        defaults.update(overrides)
        d = Driver(**defaults)
        db.add(d)
        db.flush()
        return d

    return _make


@pytest.fixture()
def make_vehicle(db):
    """Factory for minimal Vehicle rows (Available Car, capacity 4)."""
    def _make(**overrides):
        defaults = dict(
            name="Vehicle T",
            vehicle_type="Car",
            capacity=4,
            status="Available",
            is_active=True,
            provider_id=1,
            current_lat=11.0168,
            current_lng=76.9558,
        )
        defaults.update(overrides)
        v = Vehicle(**defaults)
        db.add(v)
        db.flush()
        return v

    return _make


@pytest.fixture()
def make_history(db):
    """Factory for DriverAssignmentHistory rows (now, any status)."""
    from datetime import datetime, timezone

    def _make(driver, vehicle, status="Completed", hours_ago=0):
        from datetime import timedelta

        h = DriverAssignmentHistory(
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            driver_name=driver.name,
            vehicle_name=vehicle.name,
            status=status,
            assignment_time=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        )
        db.add(h)
        db.flush()
        return h

    return _make
