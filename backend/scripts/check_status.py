"""Step 1 verification: DB status distributions and stale trip check."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from collections import Counter
from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.db.models import Driver, Vehicle, Trip

db = SessionLocal()

# Driver status distribution
drivers = db.query(Driver).all()
print("=== DRIVER STATUS ===")
print(dict(Counter(d.status for d in drivers)))
print(f"Total drivers: {len(drivers)}")

# Vehicle status distribution
vehicles = db.query(Vehicle).all()
print("\n=== VEHICLE STATUS ===")
print(dict(Counter(v.status for v in vehicles)))
print(f"Total vehicles: {len(vehicles)}")

# Trip status distribution
trips = db.query(Trip).all()
print("\n=== TRIP STATUS ===")
print(dict(Counter(t.status for t in trips)))
print(f"Total trips: {len(trips)}")

# Active/Planned trips detail
stale = db.query(Trip).filter(Trip.status.in_(["Planned", "Active"])).all()
print(f"\n=== ACTIVE/PLANNED TRIPS: {len(stale)} ===")
now = datetime.now(timezone.utc)
for t in stale[:15]:
    age_min = (now - t.created_at).total_seconds() / 60.0
    dur = getattr(t, "expected_duration_min", "N/A")
    print(f"  Trip#{t.id} status={t.status} age_min={age_min:.1f} expected_dur={dur}")

# Available driver/vehicle count
avail_drivers = db.query(Driver).filter(Driver.status == "Available").count()
avail_vehicles = db.query(Vehicle).filter(Vehicle.status == "Available", Vehicle.is_active.is_(True)).count()
print(f"\n=== AVAILABILITY ===")
print(f"Available drivers: {avail_drivers}/{len(drivers)}")
print(f"Available vehicles: {avail_vehicles}/{len(vehicles)}")

db.close()
