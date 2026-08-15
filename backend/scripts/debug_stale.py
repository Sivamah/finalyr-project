# -*- coding: utf-8 -*-
"""Debug: check what complete_stale_trips sees when called directly."""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone, timedelta
from app.db.database import SessionLocal
from app.db.models import Driver, Vehicle, Trip

db = SessionLocal()

# Check current Active/Planned trips
stale = db.query(Trip).filter(Trip.status.in_(["Planned", "Active"])).all()
print(f"Active/Planned trips: {len(stale)}")
now_utc = datetime.utcnow()  # naive UTC to match SQLite storage
for t in stale:
    if t.created_at is not None:
        ca = t.created_at.replace(tzinfo=None) if t.created_at.tzinfo else t.created_at
        age_sec = (now_utc - ca).total_seconds()
        print(f"  Trip#{t.id} status={t.status} created_at={t.created_at} tzinfo={t.created_at.tzinfo} age_sec={age_sec:.1f}")
    else:
        print(f"  Trip#{t.id} status={t.status} created_at=None")

# Try calling complete_stale_trips directly
from app.dmfe.driver_selection import complete_stale_trips
released = complete_stale_trips(db, max_age_min=10.0)
print(f"\ncomplete_stale_trips(max_age=10min) released: {released}")

# Re-check
stale2 = db.query(Trip).filter(Trip.status.in_(["Planned", "Active"])).all()
print(f"Active/Planned trips after release: {len(stale2)}")
for t in stale2:
    print(f"  Trip#{t.id} still Active/Planned")

# Check driver/vehicle status
d1 = db.query(Driver).filter(Driver.id == 1).first()
v1 = db.query(Vehicle).filter(Vehicle.id == 1).first()
if d1: print(f"\nDriver #1 status: {d1.status}")
if v1: print(f"Vehicle #1 status: {v1.status}")

db.close()
