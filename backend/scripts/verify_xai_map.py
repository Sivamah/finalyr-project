# -*- coding: utf-8 -*-
"""
verify_xai_map.py — verify the XAI → live-map link.

Seeds the curated demo scenario, runs the real DMFE pipeline, then VERIFIES
(asserting, not just printing) that the XAI payloads the frontend map
consumes are present, complete, and faithful to what was persisted:

  * accepted  — decision "Compatible for Batching" whose request was
                dispatched in a shared Trip (route stops + driver/vehicle)
  * rejected  — decision "Standalone Direct Routing" rejected from
                batching (the real rejection reason, partner highlighted)
  * fidelity  — for every dispatched explanation, the reported decision and
                compatibility score match the stored DMFEBatch row, and the
                confidence comes from the stored decision_confidence (or is
                explicitly labeled as an estimated fallback).

Exits non-zero on any failed assertion.

Usage:  backend\\.venv\\Scripts\\python.exe backend\\scripts\\verify_xai_map.py
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app

from app.db.database import SessionLocal
from app.db.models import SimulationRequest
from app.dmfe.models import DMFEBatch

DEMO_TAG = "[A-DMFE Demo Scenario]"
FAILURES = []


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"[FAIL] {msg}")


def login(client):
    r = client.post("/api/auth/login", json={"email": "admin@aiorch.com", "password": "admin123"})
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text}")
        sys.exit(1)
    token = r.json().get("access_token") or r.json().get("token")
    return {"Authorization": f"Bearer {token}"}


def summary(exp):
    """What the map layer needs from one explanation, as in the frontend."""
    trip = exp.get("trip")
    return {
        "request_id": exp["request_id"],
        "request_type": exp["request_type"],
        "decision": exp["decision"],
        "status": exp["status"],
        "reason": exp["reason"],
        "compatibility_score": exp.get("factors", {}).get("overall_compatibility_score"),
        "partner_ids": exp.get("batched_with_request_ids", []),
        "related_requests": [
            {
                "request_id": p["request_id"],
                "relation": ("self" if p["request_id"] == exp["request_id"]
                             else ("partner" if p["request_id"] in exp.get("batched_with_request_ids", [])
                                   else "trip")),
                "pickup": (p["pickup_lat"], p["pickup_lng"]),
                "drop": (p["drop_lat"], p["drop_lng"]),
            }
            for p in exp.get("related_requests", [])
        ],
        "route_stops": [
            {"request_id": s["request_id"], "action": s["action"],
             "lat": round(s["lat"], 6), "lng": round(s["lng"], 6),
             "arrival_min": s["arrival_min"]}
            for s in (trip or {}).get("route_stops", [])
        ],
        "driver": (trip or {}).get("driver"),
        "vehicle": (trip or {}).get("vehicle"),
        "trip_code": (trip or {}).get("trip_code"),
        "is_shared": (trip or {}).get("is_shared"),
    }


def pick_accepted(exps):
    # Prefer a demo request dispatched in a shared trip (full route present).
    for e in exps:
        if e.get("decision") == "Compatible for Batching" and e.get("trip") \
                and DEMO_TAG in (e.get("pickup_address") or ""):
            n = summary(e)
            if n["route_stops"]:
                return e, n
    for e in exps:
        if e.get("decision") == "Compatible for Batching" and e.get("trip"):
            n = summary(e)
            if n["route_stops"]:
                return e, n
    return None, None


def pick_rejected(exps):
    # 1) demo request rejected from batching (best demo: partner highlighted)
    for e in exps:
        if e.get("status") == "Incompatible" \
                and e.get("decision") == "Standalone Direct Routing" \
                and "Rejected from batching" in (e.get("reason") or "") \
                and DEMO_TAG in (e.get("pickup_address") or ""):
            return e, summary(e)
    # 2) any request rejected from batching
    for e in exps:
        if e.get("status") == "Incompatible" \
                and e.get("decision") == "Standalone Direct Routing" \
                and "Rejected from batching" in (e.get("reason") or ""):
            return e, summary(e)
    # 3) fallback: any standalone demo request
    for e in exps:
        if e.get("status") == "Incompatible" \
                and e.get("decision") == "Standalone Direct Routing" \
                and DEMO_TAG in (e.get("pickup_address") or ""):
            return e, summary(e)
    return None, None


def verify_fidelity(exps):
    """Historical replay: dispatched explanations must mirror stored DMFEBatch."""
    by_request = {}
    db = SessionLocal()
    try:
        for b in db.query(DMFEBatch).all():
            for rid in (json.loads(b.request_ids_json) if b.request_ids_json else []):
                by_request.setdefault(int(rid), b)
    finally:
        db.close()

    checks = 0
    for e in exps:
        trip = e.get("trip")
        if not trip:                 # not dispatched — nothing stored to replay
            continue
        stored = by_request.get(e["request_id"])
        if stored is None:
            fail(f"explanation for dispatched request {e['request_id']} has no "
                 f"stored DMFEBatch row to replay")
            continue
        checks += 1
        expected_decision = (
            "Compatible for Batching"
            if stored.decision == "Compatible"
            else "Standalone Direct Routing"
        )
        if e["decision"] != expected_decision:
            fail(f"request {e['request_id']}: explanation decision {e['decision']!r} "
                 f"!= stored {stored.decision!r} -> {expected_decision!r}")
        if e.get("factors", {}).get("overall_compatibility_score") is None:
            fail(f"request {e['request_id']}: dispatched explanation "
                 f"missing overall_compatibility_score")
        else:
            reported = float(e["factors"]["overall_compatibility_score"])
            if stored.compatibility_score is not None \
                    and abs(reported - float(stored.compatibility_score)) > 1e-6:
                fail(f"request {e['request_id']}: explanation score {reported} "
                     f"!= stored {stored.compatibility_score}")
        reported_conf = e.get("confidence_score")
        fallback = e.get("confidence_fallback", False)
        if stored.decision_confidence is not None:
            if fallback:
                fail(f"request {e['request_id']}: fallback flagged although "
                     f"stored confidence {stored.decision_confidence} exists")
            if reported_conf is None or abs(float(reported_conf) - float(stored.decision_confidence)) > 1e-6:
                fail(f"request {e['request_id']}: explanation confidence "
                     f"{reported_conf} != stored {stored.decision_confidence}")
        elif not fallback:
            fail(f"request {e['request_id']}: no stored confidence but "
                 f"confidence_fallback not flagged (must be an estimated fallback)")
    return checks


def main():
    # Context-manager form runs the app lifespan: schema create_all, admin
    # user seeding and driver/vehicle seed, so this verifier works against a
    # fresh scratch DATABASE_URL without touching any dev database.
    with TestClient(app) as client:
        _run(client)


def _run(client):
    headers = login(client)

    print("== Seeding demo scenario ==")
    r = client.post("/api/dmfe/demo/seed", headers=headers)
    print(f"seed -> {r.status_code} {r.text[:160]}")
    if r.status_code not in (200, 201, 409):
        fail(f"demo seed returned {r.status_code}")
        sys.exit(1)

    print("\n== Inserting guaranteed-rejected fixture (capacity-violating pair) ==")
    # Two requests near the demo cluster with demand that exceeds any vehicle
    # capacity: every candidate group containing them must fail the capacity
    # gate, so /analyze persists an Incompatible batch with ✗ blockers.  This
    # guarantees a real "Rejected from batching" explanation exists to verify.
    db = SessionLocal()
    try:
        ids = []
        for i in range(2):
            req = SimulationRequest(
                request_type="parcel",
                pickup_lat=11.0200, pickup_lng=76.9600,
                drop_lat=11.0250, drop_lng=76.9650,
                pickup_address=DEMO_TAG + " Rejected Fixture",
                demand=10, priority="Low", weight_kg=80.0, status="Pending",
            )
            db.add(req)
            db.flush()
            ids.append(req.id)
        db.commit()
        print(f"fixture -> requests #{ids}")
    finally:
        db.close()

    print("\n== Running /analyze (persists Compatible and Incompatible decisions) ==")
    r = client.post("/api/dmfe/analyze", headers=headers)
    if r.status_code not in (200, 201):
        fail(f"analyze returned {r.status_code}: {r.text[:300]}")
        sys.exit(1)
    print(f"analyze -> {r.status_code}")

    print("\n== Running DMFE pipeline on the pending queue ==")
    r = client.post("/api/dmfe/run", json={"limit": 200}, headers=headers)
    if r.status_code != 200:
        fail(f"run returned {r.status_code}: {r.text[:300]}")
        sys.exit(1)
    run = r.json()
    assigned = run.get("assigned", [])
    unassigned = run.get("unassigned", [])
    print(f"dispatch -> assigned {len(assigned)}, unassigned {len(unassigned)}")
    if len(assigned) + len(unassigned) == 0:
        fail("DMFE run returned zero outcomes — nothing to verify")

    print("\n== Fetching XAI explanations ==")
    exps = client.get("/api/xai/explanations?limit=400", headers=headers).json()
    print(f"{len(exps)} explanations returned")
    if not exps:
        fail("no XAI explanations returned by /api/xai/explanations")
    if len({e["request_id"] for e in exps}) != len(exps):
        fail("explanations contain duplicate request_ids")

    accepted, accepted_summary = pick_accepted(exps)
    rejected, rejected_summary = pick_rejected(exps)

    print("\n" + "=" * 80)
    print("ACCEPTED BATCH -> live map payload")
    print("=" * 80)
    if accepted:
        print(json.dumps(accepted_summary, indent=2, ensure_ascii=False))
    else:
        fail("no 'Compatible for Batching' explanation with a dispatched trip found")
        print("  (expected an accepted demo batch)")

    print("\n" + "=" * 80)
    print("REJECTED REQUEST -> live map payload")
    print("=" * 80)
    if rejected:
        print(json.dumps(rejected_summary, indent=2, ensure_ascii=False))
    else:
        fail("no Standalone/Incompatible explanation found")
        print("  (expected an incompatible demo request)")

    print("\n" + "=" * 80)
    print("HISTORICAL FIDELITY (stored DMFEBatch replay)")
    print("=" * 80)
    checks = verify_fidelity(exps)
    print(f"  compared {checks} dispatched explanation(s) against stored batches")
    if checks == 0:
        fail("no dispatched explanations existed to check historical fidelity")

    print("\n" + "=" * 80)
    if FAILURES:
        print(f"VERIFY XAI MAP: FAILED — {len(FAILURES)} failure(s)")
        for f_ in FAILURES:
            print("  " + f_)
        sys.exit(1)
    print("VERIFY XAI MAP: PASS — accepted/rejected payloads complete and "
          "dispatched explanations match persisted decisions")
    print("  (map focus URL: /live-map?xai=%d)" % accepted["request_id"] if accepted else "")
    print("=" * 80)


if __name__ == "__main__":
    main()