# -*- coding: utf-8 -*-
"""
Step 3 verification script -- exercises the DMFE engine via API and direct DB.
Covers Step 3 items #3 through #6.
"""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from datetime import datetime, timezone, timedelta
import requests as http_requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE = "http://127.0.0.1:8000"

# -- Helper: get auth token ---------------------------------------------------
def get_token():
    r = http_requests.post(f"{BASE}/api/auth/login", json={
        "email": "admin@aiorch.com",
        "password": "admin123"
    })
    if r.status_code != 200:
        r = http_requests.post(f"{BASE}/api/auth/login", data={
            "username": "admin@aiorch.com",
            "password": "admin123"
        })
    data = r.json()
    return data.get("access_token") or data.get("token")


token = get_token()
if not token:
    print("FATAL: could not obtain auth token")
    sys.exit(1)
headers = {"Authorization": f"Bearer {token}"}
print(f"Auth token obtained: {token[:20]}...")

# ==============================================================================
# Step 3.3 -- POST /api/dmfe/analyze on freed fleet
# ==============================================================================
print("\n" + "=" * 70)
print("STEP 3.3 -- POST /api/dmfe/analyze (freed fleet)")
print("=" * 70)

r = http_requests.post(f"{BASE}/api/dmfe/analyze", headers=headers)
print(f"HTTP {r.status_code}")
result = r.json()
print(json.dumps({
    "run_id": result.get("run_id"),
    "total_pending": result.get("total_pending"),
    "total_pairs_evaluated": result.get("total_pairs_evaluated"),
    "batches_created": result.get("batches_created"),
    "rejected_count": result.get("rejected_count"),
    "avg_compatibility_score": result.get("avg_compatibility_score"),
    "threshold_used": result.get("threshold_used"),
}, indent=2))

batches_created = result.get("batches_created", 0)
total_pending = result.get("total_pending", 0)
if total_pending > 0 and batches_created > 0:
    print(f"[PASS] {batches_created} batches created from {total_pending} pending")
elif total_pending == 0:
    print("[INFO] No pending requests -- need to seed data for a proper test")
else:
    print(f"[WARN] {batches_created} batches from {total_pending} pending -- check if expected")

# ==============================================================================
# Step 3.4 -- Minimal control case: 2 compatible requests + 1 driver + 1 vehicle
# ==============================================================================
print("\n" + "=" * 70)
print("STEP 3.4 -- Minimal control case")
print("=" * 70)

from app.db.database import SessionLocal
from app.db.models import SimulationRequest, Driver, Vehicle

db = SessionLocal()

avail_d = db.query(Driver).filter(Driver.status == "Available").first()
avail_v = db.query(Vehicle).filter(Vehicle.status == "Available", Vehicle.is_active.is_(True)).first()

if not avail_d or not avail_v:
    print("SKIP: No available driver/vehicle for control case")
else:
    print(f"Using driver #{avail_d.id} ({avail_d.name}) and vehicle #{avail_v.id} ({avail_v.vehicle_type}, cap={avail_v.capacity})")

    now = datetime.now(timezone.utc)
    req1 = SimulationRequest(
        request_type="ride",
        pickup_lat=12.9716, pickup_lng=77.5946,
        drop_lat=12.9816, drop_lng=77.6046,
        demand=1, weight_kg=5.0,
        priority="Medium",
        status="Pending",
        created_at=now,
    )
    req2 = SimulationRequest(
        request_type="ride",
        pickup_lat=12.9720, pickup_lng=77.5950,
        drop_lat=12.9820, drop_lng=77.6050,
        demand=1, weight_kg=5.0,
        priority="Medium",
        status="Pending",
        created_at=now,
    )
    db.add_all([req1, req2])
    db.commit()
    db.refresh(req1)
    db.refresh(req2)
    print(f"Created test requests: #{req1.id}, #{req2.id}")

    r = http_requests.post(f"{BASE}/api/dmfe/analyze", headers=headers)
    ctrl = r.json()
    print(f"HTTP {r.status_code}")
    print(json.dumps({
        "run_id": ctrl.get("run_id"),
        "total_pending": ctrl.get("total_pending"),
        "batches_created": ctrl.get("batches_created"),
        "rejected_count": ctrl.get("rejected_count"),
        "avg_compatibility_score": ctrl.get("avg_compatibility_score"),
    }, indent=2))

    if ctrl.get("batches_created", 0) > 0:
        print("[PASS] Compatible requests formed a batch with available driver/vehicle")
    elif ctrl.get("total_pending", 0) > 0 and ctrl.get("rejected_count", 0) > 0:
        rej = ctrl.get("rejected_batches", [])
        if rej:
            reasons = rej[0].get("decision_reasons", rej[0].get("reasons", []))
            for rs in reasons[-3:]:
                print(f"  -> {rs}")
        print("[WARN] Batch rejected -- may be legitimate compatibility/feasibility, not stale-trip issue")
    else:
        print("[INFO] Unexpected result -- reviewing")

    # Cleanup test requests
    db.query(SimulationRequest).filter(SimulationRequest.id.in_([req1.id, req2.id])).update(
        {"status": "Completed"}, synchronize_session=False
    )
    db.commit()

# ==============================================================================
# Step 3.5 -- No-driver control case
# ==============================================================================
print("\n" + "=" * 70)
print("STEP 3.5 -- No-driver control case")
print("=" * 70)

# Temporarily set all drivers to Busy
db.query(Driver).update({"status": "Busy"}, synchronize_session=False)
db.commit()
print("All drivers set to Busy")

now = datetime.now(timezone.utc)
req_nd = SimulationRequest(
    request_type="ride",
    pickup_lat=12.9716, pickup_lng=77.5946,
    drop_lat=12.9816, drop_lng=77.6046,
    demand=1, weight_kg=5.0,
    priority="Medium", status="Pending",
    created_at=now,
)
req_nd2 = SimulationRequest(
    request_type="ride",
    pickup_lat=12.9718, pickup_lng=77.5948,
    drop_lat=12.9818, drop_lng=77.6048,
    demand=1, weight_kg=5.0,
    priority="Medium", status="Pending",
    created_at=now,
)
db.add_all([req_nd, req_nd2])
db.commit()
db.refresh(req_nd)
db.refresh(req_nd2)

r = http_requests.post(f"{BASE}/api/dmfe/analyze", headers=headers)
nd_result = r.json()
print(f"HTTP {r.status_code}")
print(json.dumps({
    "run_id": nd_result.get("run_id"),
    "total_pending": nd_result.get("total_pending"),
    "batches_created": nd_result.get("batches_created"),
    "rejected_count": nd_result.get("rejected_count"),
}, indent=2))

rej_batches = nd_result.get("rejected_batches", [])
found_driver_reason = False
for b in rej_batches:
    reasons = b.get("decision_reasons", b.get("reasons", []))
    for reason in reasons:
        if isinstance(reason, str) and ("Available" in reason or "driver" in reason.lower() or "busy" in reason.lower()):
            print(f"[PASS] Clear driver-unavailability rejection: '{reason}'")
            found_driver_reason = True
            break
    if found_driver_reason:
        break

if not found_driver_reason and nd_result.get("rejected_count", 0) > 0:
    print("[WARN] Rejected but reason didn't clearly mention driver unavailability")
    if rej_batches:
        reasons = rej_batches[0].get("decision_reasons", rej_batches[0].get("reasons", []))
        for r_str in reasons[-3:]:
            print(f"  -> {r_str}")

# Restore drivers
db.query(Driver).update({"status": "Available"}, synchronize_session=False)
db.commit()
print("Drivers restored to Available")

# Cleanup
db.query(SimulationRequest).filter(SimulationRequest.id.in_([req_nd.id, req_nd2.id])).update(
    {"status": "Completed"}, synchronize_session=False
)
db.commit()

# ==============================================================================
# Step 3.6 -- Stale trip auto-release verification
# ==============================================================================
print("\n" + "=" * 70)
print("STEP 3.6 -- Stale trip auto-release verification")
print("=" * 70)

from app.db.models import Trip

test_driver = db.query(Driver).filter(Driver.status == "Available").first()
test_vehicle = db.query(Vehicle).filter(Vehicle.status == "Available", Vehicle.is_active.is_(True)).first()

if test_driver and test_vehicle:
    # Mark driver+vehicle busy
    test_driver.status = "Busy"
    test_vehicle.status = "Busy"

    # Create a stale trip (20 minutes old)
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=20)
    stale_trip = Trip(
        trip_code="TEST-STALE-001",
        is_shared=False,
        status="Active",
        request_ids_json=json.dumps([]),
        created_at=stale_time,
        driver_id=test_driver.id,
        vehicle_id=test_vehicle.id,
    )
    db.add(stale_trip)
    db.commit()
    db.refresh(stale_trip)
    print(f"Created stale trip #{stale_trip.id} (age=20min, status=Active)")
    print(f"Driver #{test_driver.id} -> Busy, Vehicle #{test_vehicle.id} -> Busy")

    # Verify they're busy
    db.refresh(test_driver)
    db.refresh(test_vehicle)
    assert test_driver.status == "Busy", f"Driver should be Busy, got {test_driver.status}"
    assert test_vehicle.status == "Busy", f"Vehicle should be Busy, got {test_vehicle.status}"

    # Now call /analyze -- should trigger complete_stale_trips and free them
    r = http_requests.post(f"{BASE}/api/dmfe/analyze", headers=headers)
    stale_result = r.json()
    print(f"\nPost-analyze HTTP {r.status_code}")

    # Refresh from DB
    db.expire_all()
    test_driver = db.query(Driver).filter(Driver.id == test_driver.id).first()
    test_vehicle = db.query(Vehicle).filter(Vehicle.id == test_vehicle.id).first()
    stale_trip = db.query(Trip).filter(Trip.id == stale_trip.id).first()

    print(f"Driver #{test_driver.id} status: {test_driver.status}")
    print(f"Vehicle #{test_vehicle.id} status: {test_vehicle.status}")
    print(f"Trip #{stale_trip.id} status: {stale_trip.status}")

    if test_driver.status == "Available" and test_vehicle.status == "Available" and stale_trip.status == "Completed":
        print("[PASS] Stale trip auto-released by run_analysis() -- driver and vehicle freed!")
    else:
        print("[FAIL] Stale trip was NOT released by the new code path")
else:
    print("SKIP: No available driver/vehicle for stale trip test")

db.close()

print("\n" + "=" * 70)
print("ALL VERIFICATION STEPS COMPLETE")
print("=" * 70)
