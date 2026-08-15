# -*- coding: utf-8 -*-
"""
Step 3.6 definitive test: in-process stale trip auto-release via run_analysis().
Creates a stale trip, makes a driver+vehicle Busy, then calls run_analysis()
(which now includes complete_stale_trips at the top) and verifies release.
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from app.db.database import SessionLocal
from app.db.models import Driver, Vehicle, Trip

db = SessionLocal()

# Pick a test driver and vehicle
test_driver = db.query(Driver).filter(Driver.status == "Available").first()
test_vehicle = db.query(Vehicle).filter(Vehicle.status == "Available", Vehicle.is_active.is_(True)).first()

if not test_driver or not test_vehicle:
    print("SKIP: No available driver/vehicle")
    sys.exit(0)

driver_id = test_driver.id
vehicle_id = test_vehicle.id

# Create stale trip (20 min old)
stale_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)
stale_time_str = stale_time.strftime("%Y-%m-%d %H:%M:%S.%f")

db.execute(text("""
    INSERT INTO trips (trip_code, is_shared, status, request_ids_json, created_at, driver_id, vehicle_id,
                       total_distance_km, total_duration_min, eta_min, fuel_l, utilization_pct,
                       max_delay_min, matrix_source, estimated_cost, distance_saved_km,
                       fuel_saved_l, co2_saved_kg, optimization_score)
    VALUES (:code, 0, 'Active', '[]', :created, :did, :vid,
            0, 0, 0, 0, 0, 0, 'test', 0, 0, 0, 0, 0)
"""), {"code": "TEST-STALE-003", "created": stale_time_str, "did": driver_id, "vid": vehicle_id})
db.execute(text("UPDATE drivers SET status = 'Busy' WHERE id = :id"), {"id": driver_id})
db.execute(text("UPDATE vehicles SET status = 'Busy' WHERE id = :id"), {"id": vehicle_id})
db.commit()

# Verify pre-state
db.expire_all()
trip = db.execute(text("SELECT id, status FROM trips WHERE trip_code = 'TEST-STALE-003'")).fetchone()
d_status = db.execute(text("SELECT status FROM drivers WHERE id = :id"), {"id": driver_id}).fetchone()[0]
v_status = db.execute(text("SELECT status FROM vehicles WHERE id = :id"), {"id": vehicle_id}).fetchone()[0]
print(f"PRE-STATE:")
print(f"  Trip #{trip[0]} status={trip[1]}")
print(f"  Driver #{driver_id} status={d_status}")
print(f"  Vehicle #{vehicle_id} status={v_status}")
assert trip[1] == "Active"
assert d_status == "Busy"
assert v_status == "Busy"

# Call run_analysis() -- this is the SAME function the /analyze endpoint calls
from app.dmfe.decision_engine import DecisionEngine
engine = DecisionEngine()
result = engine.run_analysis(db)

print(f"\nrun_analysis() result:")
print(f"  batches_created={result.batches_created}")
print(f"  total_pending={result.total_pending}")
print(f"  rejected={result.rejected_count}")

# Verify post-state
db.expire_all()
trip_after = db.execute(text("SELECT id, status FROM trips WHERE trip_code = 'TEST-STALE-003'")).fetchone()
d_after = db.execute(text("SELECT status FROM drivers WHERE id = :id"), {"id": driver_id}).fetchone()[0]
v_after = db.execute(text("SELECT status FROM vehicles WHERE id = :id"), {"id": vehicle_id}).fetchone()[0]

print(f"\nPOST-STATE:")
print(f"  Trip #{trip_after[0]} status={trip_after[1]}")
print(f"  Driver #{driver_id} status={d_after}")
print(f"  Vehicle #{vehicle_id} status={v_after}")

if trip_after[1] == "Completed" and d_after == "Available" and v_after == "Available":
    print("\n[PASS] Stale trip auto-released by run_analysis() -- the fix works end-to-end!")
else:
    print(f"\n[FAIL] Expected Completed/Available/Available, got {trip_after[1]}/{d_after}/{v_after}")

db.close()
