# -*- coding: utf-8 -*-
"""
End-to-end hardening scenario (Task 10).

Drives the REAL FastAPI app over HTTP against a fresh isolated SQLite DB and
asserts the engine invariants the audit cares about:

  * accounting closes: processed + unassigned == N (no requests vanish)
  * zero double-processing: every request appears in at most ONE trip and at
    most ONE realized (Dispatched/Individual/Rejected) DMFEBatch
  * zero duplicates: no trip assigns the same request twice
  * state consistency: all fresh trips Active; every assignment has a
    driver_id and vehicle_id
  * full coverage when the fleet is ample: unassigned == 0
  * idempotent re-run: a second /api/dmfe/run creates NO new trips
  * XAI historical fidelity: the replay for a dispatched request matches its
    real trip (shared -> "Compatible for Batching", solo -> "Standalone
    Direct Routing") and never contradicts it

Usage:
    python scripts/e2e_hardening.py --requests 50

The DB lives at %TEMP%/dmfe_e2e_n{N}.db; a fresh one is created per run so
each scenario starts from a clean, reproducible state (callers can vary N).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

AP = argparse.ArgumentParser()
AP.add_argument("--requests", type=int, required=True)
AP.add_argument("--db", type=str, default="")
ARGS = AP.parse_args()

N = ARGS.requests
if ARGS.db:
    DB_PATH = ARGS.db
else:
    DB_PATH = os.path.join(os.environ.get("TEMP", "/tmp"), f"dmfe_e2e_n{N}.db")
for suffix in ("", "-wal", "-shm"):
    try:
        os.remove(DB_PATH + suffix)
    except OSError:
        pass
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.replace(os.sep, '/')}"

sys.stdout.reconfigure(encoding="utf-8")
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_ROOT)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.db.models import (  # noqa: E402
    Driver, DriverAssignment, Provider, SimulationRequest, Trip, Vehicle,
)
from app.dmfe.models import DMFEBatch  # noqa: E402

ANCHOR_LAT, ANCHOR_LNG = 11.0168, 76.9558

fails = []


def check(desc, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {desc} {' ' + detail if detail else ''}")
    if not cond:
        fails.append(desc)


def login(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@aiorch.com", "password": "admin123"})
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text}")
        sys.exit(2)
    tok = r.json().get("access_token") or r.json().get("token")
    return {"Authorization": f"Bearer {tok}"}


def seed_fleet(db, n):
    provider = db.query(Provider).first()
    if provider is None:
        provider = Provider(name="E2E Provider", provider_type="Fleet")
        db.add(provider)
        db.flush()
    vehicles, drivers = [], []
    for i in range(n):
        v = Vehicle(
            provider_id=provider.id,
            name=f"E2E-V-{i:04d}",
            vehicle_type="Car",
            capacity=4,
            status="Available",
            current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG,
        )
        db.add(v)
        db.flush()
        d = Driver(
            provider_id=provider.id,
            name=f"E2E-D-{i:04d}",
            status="Available",
            current_lat=ANCHOR_LAT, current_lng=ANCHOR_LNG,
            assigned_vehicle_id=v.id,
        )
        db.add(d)
        db.flush()
        vehicles.append(v)
        drivers.append(d)
    return provider, vehicles, drivers


def seed_requests(db, n):
    """n Pending near-Coimbatore requests, grouped into compatible pairs."""
    reqs = []
    for i in range(n):
        reqs.append(SimulationRequest(
            request_type="ride",
            pickup_lat=ANCHOR_LAT + 0.0005 * (i % 3),
            pickup_lng=ANCHOR_LNG + 0.0005 * (i % 2),
            drop_lat=ANCHOR_LAT + 0.01 + 0.001 * (i % 5),
            drop_lng=ANCHOR_LNG + 0.012 + 0.001 * ((i + 1) % 4),
            demand=1,
            priority="High" if i % 5 == 0 else "Medium",
            weight_kg=0.0,
            status="Pending",
            provider_id=1,
            created_at=datetime.now(timezone.utc),
        ))
    db.add_all(reqs)
    db.commit()
    return reqs


def realized_batch_requests(db):
    """All request_ids recorded inside Dispatched/Individual/Rejected batches."""
    ids = []
    for b in db.query(DMFEBatch).all():
        if b.status in ("Dispatched", "Individual", "Rejected"):
            ids.extend(json.loads(b.request_ids_json or "[]"))
    return ids


def trip_requests(db):
    ids = []
    for t in db.query(Trip).all():
        ids.extend(json.loads(t.request_ids_json or "[]"))
    return ids


def main():
    print(f"\n===== E2E hardening scenario: N={N} ({DB_PATH}) =====")
    with TestClient(app) as client:
        headers = login(client)
        db = SessionLocal()

        provider, vehicles, drivers = seed_fleet(db, N)
        print(f"  fleet seeded: {len(drivers)} drivers / {len(vehicles)} vehicles")
        # (lifespan already created a default provider; normalize provider_id)
        p_id = provider.id
        for r in db.query(SimulationRequest).all():
            r.provider_id = p_id
        db.commit()

        reqs = seed_requests(db, N)
        print(f"  requests seeded: {len(reqs)} (ids {reqs[0].id}..{reqs[-1].id})")

        # ── Run #1 ────────────────────────────────────────────────────────
        t0 = time.perf_counter()
        r = client.post("/api/dmfe/run", headers=headers, json={"limit": N})
        dt = time.perf_counter() - t0
        print(f"  /api/dmfe/run -> {r.status_code} in {dt:.3f}s")
        if r.status_code != 200:
            print("  BODY:", r.text[:2000])
            sys.exit(3)
        res = r.json()
        processed = res.get("requests_processed", 0)
        unassigned = res.get("unassigned", [])
        print(f"  processed={processed} shared={res.get('shared_trips')} "
              f"individual={res.get('individual_trips')} unassigned={len(unassigned)}")

        check("accounting closes (processed + unassigned == N)",
              processed + len(unassigned) == N,
              f"processed={processed} unassigned={len(unassigned)} N={N}")
        check("full coverage with ample fleet (unassigned == 0)",
              len(unassigned) == 0, f"unassigned={len(unassigned)}")

        trips = db.query(Trip).all()
        assignments = db.query(DriverAssignment).all()
        check("trips created", len(trips) > 0, f"trips={len(trips)}")
        check("assignments created", len(assignments) == len(trips) and len(assignments) > 0,
              f"assignments={len(assignments)} trips={len(trips)}")

        tr_ids = trip_requests(db)
        dup_in_trips = [rid for rid, c in Counter(tr_ids).items() if c > 1]
        check("no duplicate request inside/across trips", not dup_in_trips,
              f"dups={sorted(dup_in_trips)[:10]}")
        whole = set(tr_ids)
        check("trip requests are a subset of the seeded N",
              whole <= {rq.id for rq in reqs})
        check("dispatched uniqueness covers every processed request",
              len(whole) == processed, f"in_trips={len(whole)} processed={processed}")

        rb_ids = realized_batch_requests(db)
        dup_b = [rid for rid, c in Counter(rb_ids).items() if c > 1]
        check("no request in >1 realized DMFEBatch", not dup_b,
              f"dups={sorted(dup_b)[:10]}")

        # Every dispatched-one-accountable: batch records exactly the same set.
        check("realized batches match trips' request set exactly",
              set(rb_ids) == whole)

        check("all fresh trips Active",
              all(t.status == "Active" for t in trips),
              f"statuses={sorted({t.status for t in trips})}")
        missing_link = [
            a.id for a in assignments
            if a.driver_id is None or a.vehicle_id is None
        ]
        check("every assignment has driver + vehicle", not missing_link,
              f"broken={missing_link[:5]}")

        # ── Run #2 (idempotency) ──────────────────────────────────────────
        trips_before = db.query(Trip).count()
        r2 = client.post("/api/dmfe/run", headers=headers, json={"limit": N})
        trips_after = db.query(Trip).count()
        check("second run HTTP 200", r2.status_code == 200)
        check("second run creates no new trips (idempotent)",
              trips_after == trips_before,
              f"trips {trips_before} -> {trips_after}")
        check("second run dispatches nothing new",
              r2.json().get("requests_processed", 0) == 0,
              f"processed={r2.json().get('requests_processed')}")

        # ── XAI historical fidelity spot-check ────────────────────────────
        if trips:
            t = max(trips, key=lambda x: x.id)
            tid = json.loads(t.request_ids_json or "[]")
            if tid:
                sample = tid[0]
                x = client.get(f"/api/xai/explanations/{sample}", headers=headers)
                check("XAI endpoint returns 200", x.status_code == 200, x.text[:300])
                if x.status_code == 200:
                    ex = x.json()
                    batched = bool(t.is_shared)
                    if batched:
                        ok = (ex.get("decision") == "Compatible for Batching"
                              and ex.get("batched_with_request_ids"))
                    else:
                        ok = ex.get("decision") == "Standalone Direct Routing"
                    check("XAI replay matches real dispatched trip",
                          ok,
                          f"decision={ex.get('decision')} trip_shared={bool(t.is_shared)}")
                    check("XAI replay carries trip code + confidence flag",
                          ex.get("trip_code") == t.trip_code
                          and "confidence_fallback" in ex)

    db.close()
    print(f"\n===== N={N}: {len(fails)} failure(s) =====")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()