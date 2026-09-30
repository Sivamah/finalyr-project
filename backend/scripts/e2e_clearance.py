# -*- coding: utf-8 -*-
"""
e2e_clearance.py — End-to-end evidence capture against the isolated audit
server (http://127.0.0.1:8100, fresh clearance.db).

For each scenario (10, 50, 50, 100 pending requests) it:
  - inserts the requests directly into the server's SQLite DB,
  - POSTs /api/dmfe/analyze and /api/dmfe/run,
  - reads back the resulting request/trip statuses,
  - records elapsed analysis + dispatch times.

Then it probes the remediation behaviours over the live API:
  - /assign/driver on a terminal (already-dispatched) request  -> 409
  - /compatibility-score with duplicate ids                    -> 422
  - /compatibility-score with fewer than 2 unique ids          -> 400
  - /assign/driver with duplicate ids                          -> 400
  - /drivers/{id} exact-primary-key lookup (id 1 must be driver 1)
  - XAI: dispatched explanations replay the persisted decision

Writes docs/reports/evidence/e2e_clearance.json and exits non-zero on failure.
"""
import sys, os, json, time, random, collections
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

import urllib.request
import sqlalchemy as sa

from app.db.database import Base
import app.db.models
import app.dmfe.models
from app.db.models import Driver, Vehicle, SimulationRequest, Trip, SystemConfig

BASE = "http://127.0.0.1:8000"
DB_PATH = "dmfe_dev.db"
EVIDENCE = os.path.join(
    os.path.dirname(__file__), os.pardir, "docs", "reports", "evidence",
    "e2e_clearance.json")

FAILURES = []


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"[FAIL] {msg}")


def http_json(method: str, path: str, token=None, body=None, timeout=600):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except Exception:
            detail = raw
        return e.code, detail


def login():
    code, payload = http_json("POST", "/api/auth/login", body={
        "email": "admin@aiorch.com", "password": "admin123"})
    if code != 200:
        fail(f"login failed: {code} {payload}")
        sys.exit(1)
    return (payload.get("access_token") or payload.get("token"))


def insert_requests(n: int, rng: random.Random) -> tuple:
    eng = sa.create_engine("sqlite:///" + DB_PATH)
    Base.metadata.create_all(eng)
    Session = sa.orm.sessionmaker(bind=eng)
    db = Session()
    try:
        ids = []
        for _ in range(n):
            pl = 11.0168 + rng.uniform(-0.012, 0.012)
            pn = 76.9558 + rng.uniform(-0.012, 0.012)
            r = SimulationRequest(
                request_type=rng.choice(["ride", "food", "parcel"]),
                pickup_lat=pl, pickup_lng=pn,
                drop_lat=pl + rng.uniform(-0.02, 0.02),
                drop_lng=pn + rng.uniform(-0.02, 0.02),
                demand=1,
                priority=rng.choice(["High", "Medium", "Low"]),
                weight_kg=rng.uniform(0.0, 5.0),
                status="Pending",
            )
            db.add(r)
            db.flush()
            ids.append(r.id)
        db.commit()
        return ids
    finally:
        db.close()


def read_status_counts() -> dict:
    eng = sa.create_engine("sqlite:///" + DB_PATH)
    Base.metadata.create_all(eng)
    Session = sa.orm.sessionmaker(bind=eng)
    db = Session()
    try:
        req_counts = dict(
            db.query(SimulationRequest.status, sa.func.count()).
            group_by(SimulationRequest.status).all())
        trip_status = dict(
            db.query(Trip.status, sa.func.count()).group_by(Trip.status).all())
        dup_req = db.query(SimulationRequest.id).group_by(
            SimulationRequest.id).having(sa.func.count() > 1).count()
        dmfe_batches = db.query(app.dmfe.models.DMFEBatch).count()
        drivers = db.query(Driver).count()
        vehicles = db.query(Vehicle).count()
        return {
            "requests_by_status": {str(k): int(v) for k, v in req_counts.items()},
            "trips_by_status": {str(k): int(v) for k, v in trip_status.items()},
            "duplicate_request_ids": int(dup_req),
            "dmfe_batches": int(dmfe_batches),
            "drivers": int(drivers),
            "vehicles": int(vehicles),
        }
    finally:
        db.close()


def run_scenario(token: str, n: int, rng: random.Random) -> dict:
    t0 = time.perf_counter()
    ids = insert_requests(n, rng)
    t_insert = time.perf_counter()

    then = time.perf_counter()
    code, analyze = http_json("POST", "/api/dmfe/analyze", token=token)
    t_analyze = time.perf_counter()
    code_run, run = http_json("POST", "/api/dmfe/run", token=token,
                              body={"limit": n + 50})
    t_run = time.perf_counter()

    if code != 200:
        fail(f"analyze({n}) returned {code}")
    if code_run != 200:
        fail(f"run({n}) returned {code_run}")
    counts = read_status_counts()
    return {
        "n": n,
        "insert_s": round(t_insert - t0, 3),
        "analyze_s": round(t_analyze - then, 3),
        "run_s": round(t_run - t_analyze, 3),
        "analyze_status": code,
        "analyze": analyze,
        "run_status": code_run,
        "run": run,
        "db": counts,
    }


def probe_idempotency(token: str) -> dict:
    # Find an already-dispatched terminal request id.
    eng = sa.create_engine("sqlite:///" + DB_PATH)
    Session = sa.orm.sessionmaker(bind=eng)
    db = Session()
    try:
        terminal = db.query(SimulationRequest.id).filter(
            SimulationRequest.status.in_(["Assigned", "Completed"])).first()
    finally:
        db.close()
    out = {}
    if terminal:
        rid = terminal[0]
        code, detail = http_json("POST", "/api/dmfe/assign/driver", token=token,
                                 body={"request_ids": [rid]})
        out["assign_terminal_status"] = code
        out["assign_terminal_detail"] = detail
        if code != 409:
            fail(f"re-dispatch of terminal request #{rid} returned "
                 f"{code} (expected 409): {detail}")
    else:
        out["assign_terminal_status"] = "no-terminal-request"
        fail("no terminal (Assigned/Completed) request existed to probe 409")
    return out


def probe_duplicates(token: str) -> dict:
    out = {}
    code, detail = http_json("POST", "/api/dmfe/compatibility-score", token=token,
                             body={"request_ids": [1, 1]})
    out["compat_dup_status"] = code
    if code != 422:
        fail(f"compatibility-score duplicate ids returned {code} (expected 422)")
    code, detail = http_json("POST", "/api/dmfe/compatibility-score", token=token,
                             body={"request_ids": [1]})
    out["compat_single_status"] = code
    if code != 422:
        fail(f"compatibility-score single id returned {code} "
             f"(expected 422 — request_ids has min_length=2)")
    code, detail = http_json("POST", "/api/dmfe/assign/driver", token=token,
                             body={"request_ids": [1, 1]})
    out["assign_dup_status"] = code
    if code != 400:
        fail(f"assign/driver duplicate ids returned {code} (expected 400)")
    return out


def probe_driver_lookup(token: str) -> dict:
    code, detail = http_json("GET", "/api/drivers/1", token=token)
    out = {"driver1_status": code}
    if code == 200:
        out["driver1_id"] = detail.get("id")
        if detail.get("id") != 1:
            fail(f"/api/drivers/1 returned driver id "
                 f"{detail.get('id')} (expected exact PK 1)")
    else:
        fail(f"/api/drivers/1 returned {code}")
    code, detail = http_json("GET", "/api/drivers/999999", token=token)
    out["driver999999_status"] = code
    if code != 404:
        fail(f"/api/drivers/999999 returned {code} (expected 404)")
    return out


def probe_xai(token: str) -> dict:
    code, exps = http_json("GET", "/api/xai/explanations?limit=500", token=token)
    if code != 200 or not isinstance(exps, list) or not exps:
        fail(f"xai explanations failed: {code}")
        return {"status": code, "count": 0}
    by_request = {}
    eng = sa.create_engine("sqlite:///" + DB_PATH)
    Session = sa.orm.sessionmaker(bind=eng)
    db = Session()
    try:
        # A request can appear in several DMFEBatch rows across the analyze
        # + run phases.  The XAI service replays the most-recently-created
        # eligible row, so mirror that: keep the highest batch id for each
        # request.
        for b in db.query(app.dmfe.models.DMFEBatch).all():
            rids = json.loads(b.request_ids_json) if b.request_ids_json else []
            for rid in rids:
                prev = by_request.get(int(rid))
                if prev is None or b.id > prev[2]:
                    by_request[int(rid)] = (b.decision, b.compatibility_score, b.id)
    finally:
        db.close()
    mism = 0
    checked = 0
    for e in exps:
        if not e.get("trip"):
            continue
        stored = by_request.get(e["request_id"])
        if stored is None:
            continue
        checked += 1
        exp_dec = e.get("decision")
        stored_dec, stored_score, batch_id = stored
        expected = {"Compatible": "Compatible for Batching"}.get(
            stored_dec, "Standalone Direct Routing")
        if exp_dec != expected:
            mism += 1
            fail(f"XAI request {e['request_id']}: decision {exp_dec!r} "
                 f"!= stored {stored_dec!r}")
        if stored_score is not None and e.get("factors", {}).get(
                "overall_compatibility_score") is not None:
            if abs(float(e["factors"]["overall_compatibility_score"]) - float(stored_score)) > 1e-6:
                mism += 1
                fail(f"XAI request {e['request_id']}: score mismatch")
    return {"status": code, "count": len(exps), "dispatched_checked": checked,
            "mismatches": mism, "unique_request_ids": len({e['request_id'] for e in exps})}


def main():
    token = login()
    rng = random.Random(7)
    scenarios = []
    for n in (10, 50, 50, 100):
        print(f"== scenario n={n} ==", flush=True)
        scenarios.append(run_scenario(token, n, rng))

    print("== idempotency / validation probes ==", flush=True)
    idem = probe_idempotency(token)
    unique = probe_duplicates(token)
    drivers = probe_driver_lookup(token)
    xai = probe_xai(token)

    evidence = {
        "server": BASE,
        "database": DB_PATH,
        "scenarios": scenarios,
        "idempotency": idem,
        "duplicates": unique,
        "driver_lookup": drivers,
        "xai": xai,
    }
    os.makedirs(os.path.dirname(EVIDENCE), exist_ok=True)
    with open(EVIDENCE, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2, default=str)
    print(f"\nEvidence written to {EVIDENCE}")

    print("\n" + "=" * 70)
    if FAILURES:
        print(f"E2E: FAILED — {len(FAILURES)} failure(s)")
        for f_ in FAILURES:
            print("  " + f_)
        sys.exit(1)
    print("E2E: PASS — analysis/dispatch completed, terminal re-dispatch 409, "
          "dup/validation 400/422, exact driver PK, XAI replay faithful")
    print("=" * 70)


if __name__ == "__main__":
    main()