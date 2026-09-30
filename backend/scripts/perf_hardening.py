"""
perf_hardening.py
================
Evidence-based performance measurement for the final hardening pass.

Measures:
  1. Batch-formation time (compatibility + batch generation) for
     N = 10 / 25 / 50 / 75 / 100 pending requests on an ISOLATED scratch
     SQLite database (never the dev/demo DB).  Uses the exact same code path
     as ``POST /api/dmfe/batch/create`` (``BatchGenerator.create_feasible_batches``).
  2. AI Insights (XAI) retrieval latency against a large request table
     (default: the current 12K+ row dev database, opened read-only via a
     dedicated engine).

No research logic is invoked or modified.  Results are printed as JSON so
they can be compared before/after a change.

Usage:
    python scripts/perf_hardening.py [--batch-db <path>] [--xai-db <path>]
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# The batch-formation stage runs against an isolated scratch database.  It is
# important to point DATABASE_URL there BEFORE importing app modules, because
# app.db.database binds its module-level engine from it.
SCRATCH_DB = os.environ.get(
    "PERF_SCRATCH_DB",
    str(Path(tempfile.gettempdir()) / "admfe_perf_batch.db"),
)
os.environ["DATABASE_URL"] = f"sqlite:///{SCRATCH_DB}"

BATCH_SIZES = (10, 25, 50, 75, 100)


def seed_requests(db, n: int):
    """Create n geographically varied pending SimulationRequest rows."""
    from app.db.models import SimulationRequest

    types = ("ride", "food", "parcel")
    base_lat, base_lng = 11.0168, 76.9558
    for i in range(n):
        # Spread requests across rings around the Coimbatore anchor so the
        # geometric/time/capacity gates produce realistic batches.
        ring = (i % 5) * 0.004
        jitter = (i * 37 % 11) * 0.0007
        lat = base_lat + ring + jitter
        lng = base_lng + ring - jitter
        db.add(
            SimulationRequest(
                request_type=types[i % len(types)],
                pickup_lat=lat,
                pickup_lng=lng,
                drop_lat=lat + 0.003,
                drop_lng=lng + 0.004,
                demand=(i % 3) + 1,
                priority=("Low", "Medium", "High")[i % 3],
                weight_kg=float((i % 4) * 2),
                status="Pending",
            )
        )
    db.commit()


def measure_batch_formation() -> dict:
    import shutil
    if Path(SCRATCH_DB).exists():
        try:
            Path(SCRATCH_DB).unlink()
        except OSError:
            shutil.rmtree(SCRATCH_DB, ignore_errors=True)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.database import Base
    from app.db.models import SimulationRequest  # noqa: F401  (register tables)
    from app.dmfe.models import DMFEBatch  # noqa: F401
    from app.dmfe.batch_generator import BatchGenerator

    engine = create_engine(f"sqlite:///{SCRATCH_DB}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    generator = BatchGenerator()

    results = {}
    for n in BATCH_SIZES:
        db = Session()
        try:
            seed_requests(db, n)
            pending = (
                db.query(SimulationRequest)
                .filter(SimulationRequest.status == "Pending")
                .order_by(SimulationRequest.created_at.asc())
                .all()
            )
            assert len(pending) == n, f"expected {n} pending, got {len(pending)}"
            t0 = time.perf_counter()
            feasible = generator.create_feasible_batches(pending, db)
            dt = time.perf_counter() - t0
            covered = set()
            for cg in feasible:
                covered.update(r.id for r in cg.requests)
            results[str(n)] = {
                "batch_formation_s": round(dt, 4),
                "batches": len(feasible),
                "covered_requests": len(covered),
                "individual_requests": n - len(covered),
            }
            # Reset for the next N by recreating the scratch DB so each
            # measurement starts from a clean queue.
            db.close()
            Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)
        finally:
            db.close()
    engine.dispose()
    return results


def measure_xai(xai_db: str) -> dict:
    """Time AI Insights retrieval against a large request table (read-only)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.services.xai_service import xai_service

    engine = create_engine(
        f"sqlite:///{xai_db}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        out = {}
        # 1) Dashboard default: newest 50, no post-filters.
        t0 = time.perf_counter()
        exps = xai_service.get_explanations(db, limit=50)
        out["limit50_no_filter_s"] = round(time.perf_counter() - t0, 3)
        out["limit50_returned"] = len(exps)

        # 2) Legacy frontend value: newest 200, no post-filters.
        t0 = time.perf_counter()
        exps = xai_service.get_explanations(db, limit=200)
        out["limit200_no_filter_s"] = round(time.perf_counter() - t0, 3)
        out["limit200_returned"] = len(exps)

        # 3) Post-filter path (decision=...) — historically the O(n) SQL-limit
        #    bypass that scanned the whole request table.
        t0 = time.perf_counter()
        exps = xai_service.get_explanations(db, limit=200, decision="compatible")
        out["limit200_decision_filter_s"] = round(time.perf_counter() - t0, 3)
        out["limit200_decision_returned"] = len(exps)

        return out
    finally:
        db.close()
        engine.dispose()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xai-db", default=str(BACKEND / "dmfe_dev.db"))
    ap.add_argument("--batch-only", action="store_true")
    ap.add_argument("--xai-only", action="store_true")
    args = ap.parse_args()

    report = {"batch_sizes": BATCH_SIZES, "timestamps": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if not args.xai_only:
        report["batch_formation"] = measure_batch_formation()
    if not args.batch_only:
        if not Path(args.xai_db).exists():
            print(f"[FAIL] XAI DB not found: {args.xai_db}", file=sys.stderr)
            return 1
        report["xai"] = measure_xai(args.xai_db)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())