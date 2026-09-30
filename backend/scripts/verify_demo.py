# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.db.models import SimulationRequest, Provider
from datetime import datetime, timezone

db = SessionLocal()

# Run inside the TestClient context so the FastAPI lifespan actually fires:
# schema is created and the default Admin account is seeded against whatever
# DATABASE_URL is configured (this script used to rely silently on a
# pre-existing dmfe_dev.db, which crashed on a fresh DB with
# "no such table: users").
with TestClient(app) as client:
    # 1. Login to get token
    r = client.post("/api/auth/login", json={"email": "admin@aiorch.com", "password": "admin123"})
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text}")
        sys.exit(1)
    token = r.json().get("access_token") or r.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}

    # 2a. Ensure at least one provider exists so the seeded demo requests have
    # a home (a truly empty scratch DB has none).
    provider = db.query(Provider).first()
    if provider is None:
        provider = Provider(name="Demo Provider", provider_type="Fleet")
        db.add(provider)
        db.commit()
    p_id = provider.id

    # 2b. Insert demo requests to simulate a fresh seed
    demo_reqs = [
        SimulationRequest(request_type="ride", pickup_address="[A-DMFE Demo Scenario] Location A", drop_address="Location B", pickup_lat=12.97, pickup_lng=77.59, drop_lat=12.98, drop_lng=77.60, status="Pending", provider_id=p_id, created_at=datetime.now(timezone.utc)),
        SimulationRequest(request_type="ride", pickup_address="[A-DMFE Demo Scenario] Location C", drop_address="Location D", pickup_lat=12.971, pickup_lng=77.591, drop_lat=12.981, drop_lng=77.601, status="Pending", provider_id=p_id, created_at=datetime.now(timezone.utc)),
        SimulationRequest(request_type="food", pickup_address="[A-DMFE Demo Scenario] Restaurant X", drop_address="Customer Y", pickup_lat=12.972, pickup_lng=77.592, drop_lat=12.982, drop_lng=77.602, status="Pending", provider_id=p_id, created_at=datetime.now(timezone.utc)),
        SimulationRequest(request_type="parcel", pickup_address="[A-DMFE Demo Scenario] Warehouse Z", drop_address="Customer W", pickup_lat=12.973, pickup_lng=77.593, drop_lat=12.983, drop_lng=77.603, status="Pending", provider_id=p_id, created_at=datetime.now(timezone.utc)),
    ]
    db.add_all(demo_reqs)
    db.commit()

    # 3. Check non-demo behavior (queue)
    q1 = client.get("/api/simulation/queue", headers=headers).json()
    print(f"Non-demo queue total items: {q1.get('total', 0)}")

    # 4. Check demo behavior (queue)
    q2 = client.get("/api/simulation/queue?demo_only=true", headers=headers).json()
    print(f"Demo queue total items: {q2.get('total', 0)}")
    for i, item in enumerate(q2.get('items', [])):
        print(f"  Demo req {i}: {item['pickup_address']}")

    # 5. Run analysis
    r_analyze = client.post("/api/dmfe/analyze", headers=headers).json()
    print(f"Analysis result: {r_analyze.get('batches_created')} batches created, {r_analyze.get('rejected_count')} rejected")

    # 6. Check non-demo behavior (batches)
    b1 = client.get("/api/dmfe/batches", headers=headers).json()
    print(f"Non-demo batches total: {len(b1)}")

    # 7. Check demo behavior (batches)
    b2 = client.get("/api/dmfe/batches?demo_only=true", headers=headers).json()
    print(f"Demo batches total: {len(b2)}")
    for i, b in enumerate(b2):
        print(f"  Demo batch {i}: {b['batch_code']} containing {b['request_ids']}")

    # 8. Exit-code gating: fail if demo_only filtering didn't actually isolate the seeded demo data
    failed = False
    demo_prefix = "[A-DMFE Demo Scenario]"
    if q2.get('total', 0) < len(demo_reqs):
        print(f"[FAIL] Expected at least {len(demo_reqs)} demo-tagged requests in demo queue, got {q2.get('total', 0)}")
        failed = True
    if any(not item.get('pickup_address', '').startswith(demo_prefix) for item in q2.get('items', [])):
        print("[FAIL] Demo queue (demo_only=true) contained a non-demo-tagged item")
        failed = True
    if r_analyze.get('batches_created', 0) > 0 and len(b2) == 0:
        print("[FAIL] Batches were created but none appear in the demo-filtered batch list")
        failed = True

    db.close()
    if failed:
        print("Verification FAILED.")
        sys.exit(1)
    print("Verification complete.")
    sys.exit(0)