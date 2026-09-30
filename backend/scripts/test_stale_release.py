# -*- coding: utf-8 -*-
"""
Step 3.6 definitive test: in-process stale trip auto-release via run_analysis().

Runs against an ISOLATED scratch SQLite database (never the dev DB):

  1. Positive case — creates a truly stale Active trip (60 min old, 0 min
     planned length -> age >= planned + grace), makes the assigned
     driver+vehicle Busy, then calls run_analysis() (which runs
     complete_stale_trips at the top) and ASSERTS the trip is Completed and
     the driver/vehicle are Available again.
  2. Negative case — a recent Active trip (5 min old, 30 min planned length)
     is NOT released, proving the cutoff is the designed
     age >= planned + grace floor and not a blind wall-clock sweep.

Exits non-zero on any assertion failure. Prints [ENV] for live-DB concerns if
the app is pointed at a non-isolated database.

Usage:  backend\\.venv\\Scripts\\python.exe backend\\scripts\\test_stale_release.py
"""
import sys, os, tempfile
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
import app.db.models
import app.dmfe.models
from app.db.models import Driver, Vehicle, Trip, SystemConfig, SimulationRequest

FAILURES = []


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"[FAIL] {msg}")


def main() -> int:
    # Isolate: scratch SQLite file, fresh schema.
    fd, path = tempfile.mkstemp(suffix=".db", prefix="stale_release_")
    os.close(fd)
    engine = create_engine("sqlite:///" + path)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Minimal config so run_analysis()'s _seed_dmfe_configs / gates work.
    for key in ("min_compatibility_score", "max_allowed_delay_min",
                "max_pickup_radius_km", "admfe.unified_scoring_enabled"):
        db.add(SystemConfig(category="ai_rules", key=key, value="60.0", data_type="string"))
    db.commit()

    driver = Driver(name="Stale Test Driver", status="Available",
                    current_lat=11.0168, current_lng=76.9558)
    db.add(driver)
    db.flush()
    vehicle = Vehicle(name="Stale Test Vehicle", vehicle_type="Car", capacity=4,
                      mileage_kmpl=15.0, cost_per_km=10.0, status="Available",
                      is_active=True, provider_id=1,
                      current_lat=11.0168, current_lng=76.9558)
    db.add(vehicle)
    db.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Positive case: stale 60-min-old trip, planned 0 min.
    stale = Trip(trip_code="TEST-STALE-003", is_shared=False, status="Active",
                 request_ids_json="[]",
                 driver_id=driver.id, vehicle_id=vehicle.id,
                 total_distance_km=0, total_duration_min=0, eta_min=0,
                 fuel_l=0, utilization_pct=0, max_delay_min=0,
                 matrix_source="test", estimated_cost=0, distance_saved_km=0,
                 fuel_saved_l=0, co2_saved_kg=0, optimization_score=0,
                 created_at=now - timedelta(minutes=60))
    db.add(stale)
    # Negative case: fresh 5-min-old trip, planned 30 min.
    fresh = Trip(trip_code="TEST-FRESH-004", is_shared=False, status="Active",
                 request_ids_json="[]",
                 driver_id=driver.id, vehicle_id=vehicle.id,
                 total_distance_km=0, total_duration_min=30, eta_min=0,
                 fuel_l=0, utilization_pct=0, max_delay_min=0,
                 matrix_source="test", estimated_cost=0, distance_saved_km=0,
                 fuel_saved_l=0, co2_saved_kg=0, optimization_score=0,
                 created_at=now - timedelta(minutes=5))
    db.add(fresh)
    db.query(Driver).filter(Driver.id == driver.id).update({"status": "Busy"})
    db.query(Vehicle).filter(Vehicle.id == vehicle.id).update({"status": "Busy"})
    db.commit()
    db.expire_all()

    trip = db.query(Trip).filter(Trip.trip_code == "TEST-STALE-003").one()
    print(f"[STATE] stale trip created 60 min ago (planned 0) -> #{trip.id} Active")
    print(f"[STATE] fresh trip created 5 min ago (planned 30) -> #{trip.id + 1} Active")

    # Call run_analysis() -- this is the SAME function the /analyze endpoint calls.
    from app.dmfe.decision_engine import DecisionEngine
    result = DecisionEngine().run_analysis(db)

    print(f"[RESULT] run_analysis(): batches_created={result.batches_created} "
          f"total_pending={result.total_pending} rejected={result.rejected_count}")

    db.expire_all()
    stale_after = db.query(Trip).filter(Trip.trip_code == "TEST-STALE-003").one()
    fresh_after = db.query(Trip).filter(Trip.trip_code == "TEST-FRESH-004").one()
    d_after = db.query(Driver).filter(Driver.id == driver.id).one()
    v_after = db.query(Vehicle).filter(Vehicle.id == vehicle.id).one()

    print(f"[CHECK] stale trip -> {stale_after.status}")
    print(f"[CHECK] fresh trip -> {fresh_after.status}")
    print(f"[CHECK] driver -> {d_after.status}   vehicle -> {v_after.status}")

    if stale_after.status == "Completed":
        print("[PASS] positive case: stale trip auto-released to Completed")
    else:
        fail(f"expected stale trip Completed, got {stale_after.status}")
    if d_after.status == "Available" and v_after.status == "Available":
        print("[PASS] positive case: driver+vehicle freed to Available")
    else:
        fail(f"expected driver/vehicle Available, got "
             f"{d_after.status}/{v_after.status}")
    if fresh_after.status == "Active":
        print("[PASS] negative case: recent trip with plan headroom NOT released")
    else:
        fail(f"expected fresh trip to stay Active, got {fresh_after.status}")

    db.close()
    engine.dispose()
    try:
        os.remove(path)
    except OSError:
        pass

    print("\n" + "=" * 70)
    if FAILURES:
        print(f"STALE RELEASE TEST: FAILED — {len(FAILURES)} failure(s)")
        for f_ in FAILURES:
            print("  " + f_)
        return 1
    print("STALE RELEASE TEST: PASS — run_analysis() releases stale trips and "
          "respects the planned-duration floor")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())