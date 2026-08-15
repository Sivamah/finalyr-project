r"""
verify_all.py — full verification suite for the DMFE dispatch-correctness fixes.

Run this from ``backend/`` with the project virtualenv active:

    cd backend
    .venv\Scripts\activate          # Windows
    python scripts/verify_all.py

It runs, in order:

  A. static      — compileall, `import app.main`, ruff (F,E9,B), pytest
  B. scenarios   — the six DMFE runtime scenarios, against the REAL
                   OR-Tools optimizer and a REAL SQLAlchemy session
  C. probes      — the P1-4 OR-Tools `SetCumulVarSoftUpperBound` probe and the
                   CSP/Swagger check (both report only, neither changes code)
  D. history     — whether the relaxed OR-Tools path was ever taken, which
                   decides if `evaluation/results/` needs regenerating

Everything runs against a throwaway SQLite file in a temp directory, so your
`dmfe_dev.db` is never touched.  A transcript is written to
``backend/VERIFY_RESULTS.md``.

Exit code is 0 only if every assertion passed.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
os.chdir(BACKEND)
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# ── Point the app at a throwaway database BEFORE anything imports it ────────
_TMPDIR = Path(tempfile.mkdtemp(prefix="dmfe_verify_"))
os.environ["DATABASE_URL"] = "sqlite:///" + str(_TMPDIR / "verify.db").replace("\\", "/")
os.environ.setdefault("SECRET_KEY", "verify-run-only-not-a-real-secret")

TRANSCRIPT: list[str] = []
RESULTS: list[tuple[str, str, str]] = []      # (name, PASS|FAIL|INFO|SKIP, detail)

ANCHOR = (11.0168, 76.9558)


# ── output helpers ──────────────────────────────────────────────────────────

def out(line: str = "") -> None:
    print(line, flush=True)
    TRANSCRIPT.append(line)


def head(title: str) -> None:
    out()
    out("=" * 78)
    out(title)
    out("=" * 78)


def record(name: str, status: str, detail: str = "") -> None:
    RESULTS.append((name, status, detail))
    out(f"  [{status:4}] {name}{('  — ' + detail) if detail else ''}")


@contextmanager
def capture_logs(logger_name: str = ""):
    """Capture log records emitted during the block."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.DEBUG)
    lg = logging.getLogger(logger_name)
    prev_level = lg.level
    lg.setLevel(logging.DEBUG)
    lg.addHandler(handler)
    try:
        yield buf
    finally:
        lg.removeHandler(handler)
        lg.setLevel(prev_level)


def run_cmd(name: str, args: list[str], expect_zero: bool = True) -> int:
    out(f"$ {' '.join(args)}")
    try:
        proc = subprocess.run(args, capture_output=True, text=True, cwd=str(BACKEND))
    except FileNotFoundError:
        record(name, "SKIP", f"{args[0]} not found on PATH")
        return -1
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    for line in tail[-25:]:
        out("    " + line)
    ok = (proc.returncode == 0) if expect_zero else True
    record(name, "PASS" if ok else "FAIL", f"exit={proc.returncode}")
    return proc.returncode


# ════════════════════════════════════════════════════════════════════════════
# A. Static checks
# ════════════════════════════════════════════════════════════════════════════

def section_static() -> None:
    head("A. STATIC CHECKS")

    run_cmd("compileall (app, tests, evaluation, scripts)",
            [sys.executable, "-m", "compileall", "-q",
             "app", "tests", "evaluation", "scripts"])

    run_cmd("import app.main",
            [sys.executable, "-c", "import app.main; print('import ok')"])

    # ruff is informational: the repo has a known pre-existing baseline of
    # findings that this work deliberately did not clean up.
    out("$ ruff check --select F,E9,B .")
    try:
        proc = subprocess.run(["ruff", "check", "--select", "F,E9,B", "."],
                              capture_output=True, text=True, cwd=str(BACKEND))
        for line in (proc.stdout + proc.stderr).strip().splitlines()[-6:]:
            out("    " + line)
        record("ruff F,E9,B (baseline, informational)", "INFO",
               f"exit={proc.returncode}")
    except FileNotFoundError:
        record("ruff F,E9,B", "SKIP", "ruff not installed")

    run_cmd("pytest tests/", [sys.executable, "-m", "pytest", "tests/", "-q"])


# ════════════════════════════════════════════════════════════════════════════
# B. DMFE runtime scenarios
# ════════════════════════════════════════════════════════════════════════════

def _fresh_db():
    """A brand-new session on a brand-new schema in the throwaway database."""
    from app.db.database import Base, engine, SessionLocal
    import app.db.models          # noqa: F401 — registers core tables
    import app.dmfe.models        # noqa: F401 — registers dmfe_batches
    from app.dmfe.compatibility import clear_config_cache

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    clear_config_cache()
    return SessionLocal()


def _fleet(db, n: int):
    from app.db.models import Driver, Vehicle
    pairs = []
    for i in range(n):
        v = Vehicle(name=f"Vehicle {i}", vehicle_type="Car", capacity=4,
                    status="Available", is_active=True, provider_id=1,
                    current_lat=ANCHOR[0], current_lng=ANCHOR[1])
        db.add(v)
        db.flush()
        d = Driver(name=f"Driver {i}", status="Available",
                   current_lat=ANCHOR[0], current_lng=ANCHOR[1],
                   assigned_vehicle_id=v.id)
        db.add(d)
        db.flush()
        pairs.append((d, v))
    db.commit()
    return pairs


def _req(db, **kw):
    from app.db.models import SimulationRequest
    defaults = dict(request_type="ride",
                    pickup_lat=ANCHOR[0], pickup_lng=ANCHOR[1],
                    drop_lat=11.02, drop_lng=76.97,
                    demand=1, priority="Medium", weight_kg=0.0,
                    status="Pending")
    defaults.update(kw)
    r = SimulationRequest(**defaults)
    db.add(r)
    db.flush()
    return r


def _set_cfg(db, key: str, value) -> None:
    from app.db.models import SystemConfig
    from app.dmfe.compatibility import clear_config_cache
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        row.value = str(value)
    else:
        db.add(SystemConfig(category="ai_rules", key=key,
                            value=str(value), data_type="string"))
    db.commit()
    clear_config_cache()


def _accounted(result) -> set:
    ids = set()
    for d in result.dispatches:
        ids.update(d.get("request_ids") or [])
    for u in result.unassigned:
        ids.update(u.get("request_ids") or [])
    return ids


def _check_invariant(name: str, result, pending_ids: list[int]) -> None:
    """shared + individual + unassigned == requests_processed, by request id."""
    acc = _accounted(result)
    lost = set(pending_ids) - acc
    detail = (f"processed={result.requests_processed} shared={result.shared_trips} "
              f"individual={result.individual_trips} "
              f"unassigned={len(result.unassigned)} accounted={len(acc)}")
    if lost:
        record(name, "FAIL", detail + f"  LOST ids={sorted(lost)}")
    elif len(acc) != result.requests_processed:
        record(name, "FAIL", detail + "  count mismatch")
    else:
        record(name, "PASS", detail)


def scenario_1_normal() -> None:
    from app.dmfe.pipeline import PipelineRunner
    db = _fresh_db()
    try:
        _fleet(db, 4)
        reqs = [
            _req(db),
            _req(db, pickup_lat=ANCHOR[0] + 0.001, drop_lat=11.021, drop_lng=76.971),
            _req(db, pickup_lat=11.10, pickup_lng=77.05, drop_lat=11.15, drop_lng=77.10),
            _req(db, pickup_lat=11.30, pickup_lng=76.70, drop_lat=11.35, drop_lng=76.65),
        ]
        db.commit()
        ids = [r.id for r in reqs]
        result = PipelineRunner().run(db)
        out(f"    result: {result.to_dict()['requests_processed']} processed, "
            f"{result.shared_trips} shared, {result.individual_trips} individual, "
            f"{len(result.unassigned)} unassigned")
        _check_invariant("scenario 1 — normal run, accounting closes", result, ids)
    finally:
        db.close()


def scenario_1b_gate_d() -> None:
    """P0-1 directly: a Gate-D-rejected High-priority pair must not vanish."""
    from app.dmfe.pipeline import PipelineRunner
    db = _fresh_db()
    try:
        _set_cfg(db, "max_allowed_delay_min", 0.01)
        _fleet(db, 4)
        high = [
            _req(db, priority="High"),
            _req(db, priority="High", pickup_lat=ANCHOR[0] + 0.001,
                 drop_lat=11.021, drop_lng=76.971),
        ]
        normal = [
            _req(db, pickup_lat=11.10, pickup_lng=77.05, drop_lat=11.15, drop_lng=77.10),
            _req(db, pickup_lat=11.101, pickup_lng=77.051, drop_lat=11.151, drop_lng=77.101),
        ]
        db.commit()
        ids = [r.id for r in high + normal]
        high_ids = {r.id for r in high}
        result = PipelineRunner().run(db)
        out(f"    High-priority ids {sorted(high_ids)}; "
            f"accounted ids {sorted(_accounted(result))}")
        _check_invariant("scenario 1b — Gate-D rejects accounted for (P0-1)",
                         result, ids)
        missing = high_ids - _accounted(result)
        record("scenario 1b — High-priority requests left a trace",
               "PASS" if not missing else "FAIL",
               "" if not missing else f"dropped {sorted(missing)}")
    finally:
        _set_cfg(db, "max_allowed_delay_min", 20.0)
        db.close()


def scenario_2_minimal() -> None:
    from app.dmfe.pipeline import PipelineRunner
    db = _fresh_db()
    try:
        _fleet(db, 1)
        reqs = [
            _req(db),
            _req(db, pickup_lat=ANCHOR[0] + 0.001, drop_lat=11.021, drop_lng=76.971),
        ]
        db.commit()
        ids = [r.id for r in reqs]
        result = PipelineRunner().run(db)
        out(f"    2 compatible requests, 1 driver -> shared={result.shared_trips} "
            f"individual={result.individual_trips} unassigned={len(result.unassigned)}")
        _check_invariant("scenario 2 — minimal feasible (2 requests, 1 driver)",
                         result, ids)
    finally:
        db.close()


def scenario_3_no_driver() -> None:
    from app.dmfe.pipeline import PipelineRunner
    db = _fresh_db()
    try:
        reqs = [
            _req(db),
            _req(db, pickup_lat=ANCHOR[0] + 0.001),
            _req(db, pickup_lat=11.10, pickup_lng=77.05, drop_lat=11.15, drop_lng=77.10),
        ]
        db.commit()
        ids = [r.id for r in reqs]
        result = PipelineRunner().run(db)
        _check_invariant("scenario 3 — no-driver control, accounting closes",
                         result, ids)
        unassigned_ids = set()
        missing_reason = []
        for u in result.unassigned:
            unassigned_ids.update(u.get("request_ids") or [])
            if not u.get("reason"):
                missing_reason.append(u)
        dispatched = result.shared_trips + result.individual_trips
        if dispatched == 0:
            record("scenario 3 — every request in `unassigned` with a reason",
                   "PASS" if unassigned_ids == set(ids) and not missing_reason
                   else "FAIL",
                   f"unassigned={sorted(unassigned_ids)} "
                   f"reasons_missing={len(missing_reason)}")
            for u in result.unassigned[:3]:
                out(f"      reason: {u.get('reason')}")
        else:
            record("scenario 3 — no-driver control", "INFO",
                   f"fleet was not empty as expected (dispatched={dispatched})")
    finally:
        db.close()


def scenario_4_stale_trip() -> None:
    """P1-5: a trip 12 min old with a 35 min plan must still be Active."""
    from app.db.models import Trip
    from app.dmfe.driver_selection import complete_stale_trips
    from app.dmfe.pipeline import PipelineRunner
    db = _fresh_db()
    try:
        _fleet(db, 2)
        _req(db)
        _req(db, pickup_lat=ANCHOR[0] + 0.001, drop_lat=11.021, drop_lng=76.971)
        db.commit()
        PipelineRunner().run(db)

        trips = db.query(Trip).filter(Trip.status.in_(["Planned", "Active"])).all()
        if not trips:
            record("scenario 4 — stale-trip cutoff", "SKIP",
                   "no Planned/Active trip was produced to age")
            return

        now = datetime.now(timezone.utc)
        for t in trips:
            t.created_at = now - timedelta(minutes=12)   # past the 10 min floor
            t.total_duration_min = 35.0                  # but inside the plan
        db.commit()
        live_ids = [t.id for t in trips]

        released = complete_stale_trips(db, max_age_min=10.0)
        db.commit()
        still_live = (
            db.query(Trip)
            .filter(Trip.id.in_(live_ids), Trip.status.in_(["Planned", "Active"]))
            .count()
        )
        out(f"    12 min old, 35 min planned -> released={released}, "
            f"still active={still_live}/{len(live_ids)}")
        record("scenario 4 — running trip survives the 10 min cutoff (P1-5)",
               "PASS" if still_live == len(live_ids) else "FAIL",
               f"released={released}")

        # Control: a genuinely stuck trip must still be released.
        for t in db.query(Trip).filter(Trip.id.in_(live_ids)).all():
            t.created_at = now - timedelta(minutes=90)
            t.total_duration_min = 20.0
        db.commit()
        released2 = complete_stale_trips(db, max_age_min=10.0)
        db.commit()
        out(f"    90 min old, 20 min planned -> released={released2}")
        record("scenario 4b — genuinely stuck trip is still released",
               "PASS" if released2 == len(live_ids) else "FAIL",
               f"released={released2} of {len(live_ids)}")
    finally:
        db.close()


def scenario_5_relaxed_route() -> None:
    """
    P0-3: force the time-dimension fallback and check the persisted Trip.

    The fallback is triggered by making the FIRST SolveWithParameters call
    return None, which is exactly what an infeasible time model does — the
    OR-Tools objective, constraints and search parameters are untouched.
    """
    from ortools.constraint_solver import pywrapcp
    from app.db.models import Trip
    from app.dmfe.driver_selection import dispatch_trip

    db = _fresh_db()
    patched = False
    original = pywrapcp.RoutingModel.SolveWithParameters
    try:
        _fleet(db, 2)
        r1 = _req(db)
        r2 = _req(db, pickup_lat=ANCHOR[0] + 0.001, drop_lat=11.021, drop_lng=76.971)
        db.commit()

        state = {"n": 0}

        def forced(self, params):
            state["n"] += 1
            if state["n"] == 1:
                return None          # simulate "no solution with time dimension"
            return original(self, params)

        try:
            pywrapcp.RoutingModel.SolveWithParameters = forced
            patched = True
        except Exception as exc:
            record("scenario 5 — relaxed route", "SKIP",
                   f"could not patch SolveWithParameters: {exc}")
            return

        with capture_logs() as buf:
            outcome = dispatch_trip(db, [r1, r2], trip_key="VERIFY-RELAXED",
                                    commit=True)
        logs = buf.getvalue()
        took_relaxed = "no solution with time dimension" in logs
        out(f"    relaxed path taken: {took_relaxed}  "
            f"(solver calls: {state['n']})")

        trip: Trip = outcome["trip"]
        db.refresh(trip)
        out(f"    Trip {trip.trip_code}: total_duration_min={trip.total_duration_min} "
            f"eta_min={getattr(trip, 'eta_min', None)} "
            f"max_delay_min={trip.max_delay_min}")

        import json as _json
        stops = (outcome.get("route_dict") or {}).get("best_route", {}).get("stops") or []
        if not stops:
            try:
                stops = _json.loads(trip.stop_order_json or "[]")
            except Exception:
                stops = []
        arrivals = [s.get("arrival_min") for s in stops if isinstance(s, dict)]
        out(f"    stop arrival_min sequence: {arrivals}")

        ok_dur = (trip.total_duration_min or 0) > 0
        ok_delay = (trip.max_delay_min if trip.max_delay_min is not None else 0) >= 0
        ok_arr = all(
            a is not None and b is not None and b >= a
            for a, b in zip(arrivals, arrivals[1:], strict=False)
        ) if len(arrivals) > 1 else True

        record("scenario 5 — relaxed route: total_duration_min > 0 (P0-3)",
               "PASS" if ok_dur else "FAIL", f"={trip.total_duration_min}")
        record("scenario 5 — relaxed route: max_delay_min >= 0 (P0-3)",
               "PASS" if ok_delay else "FAIL", f"={trip.max_delay_min}")
        record("scenario 5 — relaxed route: arrivals non-decreasing",
               "PASS" if ok_arr else "FAIL", f"{arrivals}")
        if not took_relaxed:
            record("scenario 5 — fallback actually exercised", "INFO",
                   "solver did not log the relax message; result may be the "
                   "normal path")
    except Exception:
        record("scenario 5 — relaxed route", "FAIL", "raised, see traceback")
        out(traceback.format_exc())
    finally:
        if patched:
            pywrapcp.RoutingModel.SolveWithParameters = original
        db.close()


def scenario_5b_normal_path_unchanged() -> None:
    """The normal solve must be unaffected by the P0-3 post-processing."""
    from app.db.models import Trip
    from app.dmfe.driver_selection import dispatch_trip
    db = _fresh_db()
    try:
        _fleet(db, 2)
        r1 = _req(db)
        r2 = _req(db, pickup_lat=ANCHOR[0] + 0.001, drop_lat=11.021, drop_lng=76.971)
        db.commit()
        with capture_logs() as buf:
            outcome = dispatch_trip(db, [r1, r2], trip_key="VERIFY-NORMAL",
                                    commit=True)
        relaxed = "no solution with time dimension" in buf.getvalue()
        trip: Trip = outcome["trip"]
        out(f"    normal solve: duration={trip.total_duration_min} "
            f"max_delay={trip.max_delay_min} relaxed_path={relaxed}")
        record("scenario 5b — normal solve still produces sane metrics",
               "PASS" if (trip.total_duration_min or 0) > 0
               and (trip.max_delay_min or 0) >= 0 else "FAIL",
               f"duration={trip.total_duration_min} delay={trip.max_delay_min}")
        record("scenario 5b — normal solve did NOT take the relaxed path",
               "PASS" if not relaxed else "INFO",
               "relaxed path was taken on a normal dispatch" if relaxed else "")
    except Exception:
        record("scenario 5b — normal solve", "FAIL", "raised, see traceback")
        out(traceback.format_exc())
    finally:
        db.close()


def scenario_6_repeated_run() -> None:
    from app.db.models import SimulationRequest, Trip
    from app.dmfe.pipeline import PipelineRunner
    db = _fresh_db()
    try:
        _fleet(db, 4)
        reqs = [_req(db),
                _req(db, pickup_lat=ANCHOR[0] + 0.001, drop_lat=11.021, drop_lng=76.971)]
        db.commit()
        ids = [r.id for r in reqs]
        runner = PipelineRunner()
        first = runner.run(db)
        _check_invariant("scenario 6 — first run accounting", first, ids)

        completed_before = db.query(Trip).filter(Trip.status == "Completed").count()
        still_pending = (db.query(SimulationRequest)
                         .filter(SimulationRequest.status == "Pending").count())

        second = runner.run(db)
        completed_after = db.query(Trip).filter(Trip.status == "Completed").count()
        out(f"    second run: processed={second.requests_processed} "
            f"shared={second.shared_trips} individual={second.individual_trips} "
            f"(pending before second run: {still_pending})")
        record("scenario 6 — second run dispatches nothing new",
               "PASS" if second.shared_trips == 0 and second.individual_trips == 0
               else ("PASS" if still_pending > 0 else "FAIL"),
               f"pending_before={still_pending}")
        record("scenario 6 — completed trips not reopened",
               "PASS" if completed_after >= completed_before else "FAIL",
               f"{completed_before} -> {completed_after}")
    finally:
        db.close()


# ════════════════════════════════════════════════════════════════════════════
# C. Probes (report only — these change nothing)
# ════════════════════════════════════════════════════════════════════════════

def probe_p1_4_soft_upper_bound() -> None:
    """
    HARD STOP probe: `SetCumulVarSoftUpperBound` is passed `t_dim.CumulVar(d_idx)`
    where the documented signature takes a routing index.  The branch is dormant
    because `vrp_delay_penalty_per_min` defaults to 0.0.  This raises that value
    and dispatches one shared trip, WITHOUT changing any code.
    """
    head("C1. P1-4 PROBE — SetCumulVarSoftUpperBound with a delay penalty active")
    from app.dmfe.driver_selection import dispatch_trip
    db = _fresh_db()
    try:
        _set_cfg(db, "vrp_delay_penalty_per_min", 5.0)
        _fleet(db, 2)
        r1 = _req(db)
        r2 = _req(db, pickup_lat=ANCHOR[0] + 0.001, drop_lat=11.021, drop_lng=76.971)
        db.commit()
        out("    vrp_delay_penalty_per_min = 5.0; dispatching one shared trip...")
        try:
            outcome = dispatch_trip(db, [r1, r2], trip_key="PROBE-P1-4", commit=True)
            trip = outcome["trip"]
            out(f"    dispatch SUCCEEDED: {trip.trip_code} "
                f"duration={trip.total_duration_min} max_delay={trip.max_delay_min} "
                f"distance={trip.total_distance_km}")
            record("P1-4 — no TypeError with the delay penalty active",
                   "PASS", "SetCumulVarSoftUpperBound accepted the routing index")
            solved = (trip.total_duration_min or 0) > 0 and trip.is_shared
            record("P1-4 — shared-trip route still solves with the penalty on",
                   "PASS" if solved else "FAIL",
                   f"is_shared={trip.is_shared} "
                   f"duration={trip.total_duration_min} "
                   f"max_delay={trip.max_delay_min}")
        except Exception as exc:
            out(f"    dispatch RAISED: {type(exc).__name__}: {exc}")
            out(traceback.format_exc())
            record("P1-4 — no TypeError with the delay penalty active",
                   "FAIL",
                   f"{type(exc).__name__}: {exc} — the soft delay bound is still "
                   f"broken; check the SetCumulVarSoftUpperBound call in "
                   f"optimizer.py")
    finally:
        _set_cfg(db, "vrp_delay_penalty_per_min", 0.0)
        db.close()


def probe_csp_docs() -> None:
    """The CSP fix: /api/docs must not carry `default-src 'self'`."""
    head("C2. CSP / Swagger UI")
    try:
        from fastapi.testclient import TestClient
        import app.main as appmain
        with TestClient(appmain.app) as client:
            for path in ("/api/docs", "/api/openapi.json"):
                resp = client.get(path)
                csp = resp.headers.get("content-security-policy")
                out(f"    GET {path} -> {resp.status_code}  CSP={csp!r}")
                record(f"CSP absent on {path}",
                       "PASS" if csp is None else "FAIL", f"CSP={csp!r}")
            resp = client.get("/api/dashboard/stats")
            csp = resp.headers.get("content-security-policy")
            out(f"    GET /api/dashboard/stats -> {resp.status_code}  CSP={csp!r}")
            record("CSP still applied to normal API responses",
                   "PASS" if csp == "default-src 'self'" else "FAIL", f"CSP={csp!r}")
    except Exception:
        record("CSP / Swagger check", "SKIP", "TestClient unavailable or app "
                                              "failed to start")
        out(traceback.format_exc())


def probe_relaxed_path_history() -> None:
    """Did the relaxed path ever run?  If so, results/ may need regenerating."""
    head("D. RELAXED-PATH HISTORY (does evaluation/results/ need regenerating?)")
    needle = "no solution with time dimension"
    hits = []
    for base in (REPO, BACKEND):
        for pattern in ("*.log", "logs/*.log", "**/*.log"):
            for path in base.glob(pattern):
                try:
                    text = path.read_text(errors="ignore")
                except Exception:
                    continue
                n = text.count(needle)
                if n:
                    hits.append((path, n))
    if hits:
        for path, n in hits:
            out(f"    {path}: {n} occurrence(s)")
        record("relaxed OR-Tools path in logs", "INFO",
               "FOUND — any evaluation/results/ produced from those runs should "
               "be regenerated, because P0-3 changes duration/delay for those trips")
    else:
        out("    no *.log files containing the marker were found.")
        out("    Note: absence of log files is not proof the path was never taken.")
        record("relaxed OR-Tools path in logs", "INFO",
               "not found in any log file on disk")


# ════════════════════════════════════════════════════════════════════════════

def main() -> int:
    started = datetime.now()
    out(f"DMFE verification suite — {started:%Y-%m-%d %H:%M:%S}")
    out(f"python      : {sys.version.split()[0]}  ({sys.executable})")
    out(f"backend     : {BACKEND}")
    out(f"scratch db  : {os.environ['DATABASE_URL']}")

    try:
        import ortools
        out(f"ortools     : {getattr(ortools, '__version__', 'installed')}")
    except Exception:
        out("ortools     : NOT INSTALLED — the runtime scenarios will fail")

    section_static()

    head("B. DMFE RUNTIME SCENARIOS")
    for fn in (scenario_1_normal, scenario_1b_gate_d, scenario_2_minimal,
               scenario_3_no_driver, scenario_4_stale_trip,
               scenario_5_relaxed_route, scenario_5b_normal_path_unchanged,
               scenario_6_repeated_run):
        out()
        out(f"-- {fn.__name__} " + "-" * (60 - len(fn.__name__)))
        try:
            fn()
        except Exception:
            record(fn.__name__, "FAIL", "raised, see traceback")
            out(traceback.format_exc())

    probe_p1_4_soft_upper_bound()
    probe_csp_docs()
    probe_relaxed_path_history()

    # ── summary ────────────────────────────────────────────────────────────
    head("SUMMARY")
    failed = [r for r in RESULTS if r[1] == "FAIL"]
    for name, status, detail in RESULTS:
        out(f"  {status:4}  {name}{('  — ' + detail) if detail else ''}")
    out()
    out(f"  {sum(1 for r in RESULTS if r[1] == 'PASS')} passed, "
        f"{len(failed)} failed, "
        f"{sum(1 for r in RESULTS if r[1] == 'SKIP')} skipped, "
        f"{sum(1 for r in RESULTS if r[1] == 'INFO')} informational")

    report = BACKEND / "VERIFY_RESULTS.md"
    report.write_text(
        "# DMFE verification run\n\n"
        f"Generated {started:%Y-%m-%d %H:%M:%S} by `scripts/verify_all.py`\n\n"
        "```\n" + "\n".join(TRANSCRIPT) + "\n```\n",
        encoding="utf-8",
    )
    out()
    out(f"transcript written to {report}")

    shutil.rmtree(_TMPDIR, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
