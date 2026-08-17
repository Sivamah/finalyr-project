"""
DMFE REST API — dmfe_v2
========================
Exposes four endpoints for the Dynamic Multi-Service Feasibility Engine.

Endpoints:
  POST /api/dmfe/analyze      — run DMFE on all pending requests
  GET  /api/dmfe/batches      — list persisted DMFE batches
  GET  /api/dmfe/history      — list analysis run summaries
  GET  /api/dmfe/statistics   — aggregate statistics
  POST /api/dmfe/demo/seed    — seed the curated demo scenario
  DEL  /api/dmfe/demo/clear   — remove pending demo-scenario requests

All routes require authentication (Bearer token).
No OR-Tools, no vehicle assignment, no routing.
"""

from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import func

from app.api.deps import SessionDep, CurrentUser
from app.dmfe.models import DMFEBatch, DMFEAnalysisRun
from app.dmfe.decision_engine import decision_engine
from app.dmfe.serializers import batch_to_dict, run_to_dict

router = APIRouter(prefix="/api/dmfe", tags=["DMFE"])

# Demo-scenario requests are tagged by this prefix on pickup_address. Both
# GET /api/dmfe/batches?demo_only=true and GET /api/simulation/queue?demo_only=true
# filter on it. Keep the three in sync — if this string changes, Demo Mode
# silently returns an empty set rather than erroring.
DEMO_TAG = "[A-DMFE Demo Scenario]"

# Curated, fully deterministic scenario. No randomness, so every demo run
# produces the same batching decisions and the walkthrough is reproducible.
# All coordinates lie inside COIMBATORE_BOUNDS (app/core/coimbatore.py:
# lat 10.95-11.15, lng 76.85-77.05).
#
# Designed to exercise three distinct engine outcomes:
#   pairs 1+2 : same-service (ride), near pickups, near drops  -> should batch
#   pairs 3+4 : same-service (food), near pickups, near drops   -> should batch
#   5         : parcel, isolated corridor                       -> solo trip
#   6         : ride, far from everything                       -> solo trip
DEMO_SCENARIO = [
    # (type, pickup_name, p_lat, p_lng, drop_name, d_lat, d_lng, priority, demand)
    ("ride",   "Gandhipuram Bus Stand", 11.0168, 76.9558, "Peelamedu",          11.0300, 77.0000, "Medium", 1),
    ("ride",   "Gandhipuram Signal",    11.0180, 76.9570, "Peelamedu Tech Park", 11.0310, 77.0010, "Medium", 1),
    ("food",   "Race Course",           11.0050, 76.9650, "R.S. Puram",          11.0080, 76.9500, "High",   1),
    ("food",   "Race Course Road",      11.0060, 76.9660, "R.S. Puram West",     11.0090, 76.9510, "Medium", 1),
    ("parcel", "Singanallur",           11.0000, 77.0280, "Ondipudur",           10.9950, 77.0400, "Low",    2),
    ("ride",   "Kalapatti",             11.0570, 77.0250, "Saravanampatti",      11.0780, 76.9990, "Medium", 1),
]


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/analyze")
def run_dmfe_analysis(db: SessionDep, current_user: CurrentUser):
    """
    Trigger a full DMFE analysis on all pending simulation requests.

    Evaluates all pairwise combinations within the configured pickup radius,
    computes 8-factor compatibility scores, applies the threshold, persists
    batch records, and returns the full structured result.
    """
    result = decision_engine.run_analysis(db)
    return result.to_dict()


@router.get("/batches")
def list_batches(
    db: SessionDep,
    current_user: CurrentUser,
    status: Optional[str] = Query(None, description="Filter by status: Pending | Rejected"),
    run_id: Optional[int] = Query(None, description="Filter by analysis run ID"),
    limit: int = Query(100, le=500),
    demo_only: bool = Query(False, description="Show only batches containing demo scenario requests"),
):
    """
    Return persisted DMFE batch records.
    Optionally filter by status or analysis run ID.
    """
    q = db.query(DMFEBatch)
    if status:
        q = q.filter(DMFEBatch.status == status)
    if run_id:
        q = q.filter(DMFEBatch.analysis_run_id == run_id)
        
    if demo_only:
        from app.db.models import SimulationRequest
        from app.core.json_utils import json_loads
        
        demo_req_ids = [
            r[0] for r in db.query(SimulationRequest.id).filter(
                SimulationRequest.pickup_address.like("[A-DMFE Demo Scenario]%")
            ).all()
        ]
        
        all_batches = q.order_by(DMFEBatch.created_at.desc()).all()
        filtered_batches = []
        for b in all_batches:
            r_ids = json_loads(b.request_ids_json, [])
            if any(rid in demo_req_ids for rid in r_ids):
                filtered_batches.append(b)
                if len(filtered_batches) >= limit:
                    break
        batches = filtered_batches
    else:
        batches = q.order_by(DMFEBatch.created_at.desc()).limit(limit).all()

    from app.db.models import SimulationRequest
    from app.core.json_utils import json_loads

    # Prefetch every referenced request in one query instead of one query
    # per batch (batch_to_dict → batch_requests_summary).
    req_ids = {
        rid
        for b in batches
        for rid in json_loads(b.request_ids_json, [])
    }
    request_by_id = {}
    if req_ids:
        request_by_id = {
            r.id: r
            for r in db.query(SimulationRequest)
            .filter(SimulationRequest.id.in_(req_ids))
            .all()
        }
    return [batch_to_dict(b, db, request_by_id) for b in batches]


@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, db: SessionDep, current_user: CurrentUser):
    """Return a single DMFE batch with full factor breakdown."""
    from fastapi import HTTPException
    b = db.query(DMFEBatch).filter(DMFEBatch.id == batch_id).first()
    if not b:
        raise HTTPException(404, "DMFE batch not found")
    return batch_to_dict(b, db)


@router.get("/history")
def list_analysis_history(
    db: SessionDep,
    current_user: CurrentUser,
    limit: int = Query(50, le=200),
):
    """Return summary records for all past DMFE analysis runs (newest first)."""
    runs = (
        db.query(DMFEAnalysisRun)
        .order_by(DMFEAnalysisRun.run_at.desc())
        .limit(limit)
        .all()
    )
    return [run_to_dict(r) for r in runs]


@router.get("/statistics")
def get_dmfe_statistics(db: SessionDep, current_user: CurrentUser):
    """
    Aggregate DMFE statistics across all analysis runs:
    - Total runs
    - Total batches created / rejected
    - Overall batch rate (%)
    - Average compatibility score across all runs
    - Most recent threshold used
    """
    total_runs = db.query(func.count(DMFEAnalysisRun.id)).scalar() or 0
    total_batches = db.query(func.sum(DMFEAnalysisRun.batches_created)).scalar() or 0
    total_rejected = db.query(func.sum(DMFEAnalysisRun.rejected_count)).scalar() or 0
    total_pairs = db.query(func.sum(DMFEAnalysisRun.total_evaluated_pairs)).scalar() or 0
    avg_score = db.query(func.avg(DMFEAnalysisRun.avg_compatibility_score)).scalar() or 0.0
    latest_run = (
        db.query(DMFEAnalysisRun)
        .order_by(DMFEAnalysisRun.run_at.desc())
        .first()
    )

    from app.db.models import SimulationRequest
    current_pending = (
        db.query(func.count(SimulationRequest.id))
        .filter(SimulationRequest.status == "Pending")
        .scalar()
    ) or 0
    from app.db.models import Trip
    current_trips = db.query(func.count(Trip.id)).scalar() or 0
    shared_trips = (
        db.query(func.count(Trip.id))
        .filter(Trip.is_shared.is_(True))
        .scalar()
    ) or 0

    # True batching rate (Step 3 formula): shared trips / total trips × 100
    batch_rate = round(
        (shared_trips / current_trips * 100), 1
    ) if current_trips and current_trips > 0 else 0.0

    # Retained under an honest name: batches created per evaluated pair
    pairs_batch_density = round(
        (total_batches / total_pairs * 100), 1
    ) if total_pairs and total_pairs > 0 else 0.0

    return {
        "total_runs": total_runs,
        "total_pairs_evaluated": int(total_pairs or 0),
        "total_batches_created": int(total_batches or 0),
        "total_rejected": int(total_rejected or 0),
        "total_pending": current_pending,
        "total_trips": current_trips,
        "total_shared_trips": int(shared_trips),
        "batch_rate_pct": batch_rate,
        "pairs_batch_density_pct": pairs_batch_density,
        "avg_compatibility_score": round(float(avg_score), 1),
        "latest_threshold": latest_run.threshold_used if latest_run else 70.0,
        "last_run_at": latest_run.run_at.strftime("%Y-%m-%d %I:%M %p") if latest_run else None,
    }


# ── Demo scenario ──────────────────────────────────────────────────────────
#
# Demo Mode in the UI filters the queue and the batch list to requests tagged
# with DEMO_TAG. Before these endpoints existed, nothing in the running
# application ever created such a row — the only producer was the standalone
# script backend/scripts/verify_demo.py — so toggling Demo Mode on always
# yielded two empty panels. These endpoints make the toggle self-sufficient.

@router.post("/demo/seed")
def seed_demo_scenario(db: SessionDep, current_user: CurrentUser):
    """
    Insert the curated demo scenario as ordinary Pending requests.

    The rows are real SimulationRequest records — the engine treats them
    exactly like any other request, so what the demo shows is genuine engine
    behaviour, not a scripted animation. They are only distinguishable by the
    DEMO_TAG prefix on pickup_address, which is what Demo Mode filters on.

    Idempotent: any still-Pending demo requests are cleared first, so repeated
    clicks re-seed rather than accumulate duplicates.
    """
    from app.db.models import SimulationRequest, Provider
    from app.engine.distance import haversine

    removed = (
        db.query(SimulationRequest)
        .filter(SimulationRequest.pickup_address.like(f"{DEMO_TAG}%"))
        .filter(SimulationRequest.status == "Pending")
        .delete(synchronize_session=False)
    )

    provider = (
        db.query(Provider).filter(Provider.status == "Active").order_by(Provider.id).first()
    )
    provider_id = provider.id if provider else None

    created_ids = []
    for (rtype, p_name, p_lat, p_lng, d_name, d_lat, d_lng, priority, demand) in DEMO_SCENARIO:
        req = SimulationRequest(
            provider_id=provider_id,
            request_type=rtype,
            pickup_lat=p_lat,
            pickup_lng=p_lng,
            drop_lat=d_lat,
            drop_lng=d_lng,
            pickup_address=f"{DEMO_TAG} {p_name}",
            drop_address=d_name,
            demand=demand,
            priority=priority,
            estimated_distance_km=round(haversine(p_lat, p_lng, d_lat, d_lng), 2),
            status="Pending",
        )
        db.add(req)
        db.flush()
        created_ids.append(req.id)

    db.commit()
    return {
        "created": len(created_ids),
        "cleared_stale": removed,
        "request_ids": created_ids,
        "provider_id": provider_id,
        "message": (
            f"{len(created_ids)} demo requests seeded. "
            "Run Analysis to see the engine batch them."
        ),
    }


@router.delete("/demo/clear")
def clear_demo_scenario(db: SessionDep, current_user: CurrentUser):
    """
    Remove demo requests that are still Pending.

    Demo requests already picked up by a run are left alone — deleting them
    would orphan the batch and trip rows that reference them, and would alter
    statistics the engine has already recorded.
    """
    from app.db.models import SimulationRequest

    pending_q = (
        db.query(SimulationRequest)
        .filter(SimulationRequest.pickup_address.like(f"{DEMO_TAG}%"))
    )
    total = pending_q.count()
    removed = pending_q.filter(SimulationRequest.status == "Pending").delete(
        synchronize_session=False
    )
    db.commit()
    return {
        "removed": removed,
        "kept_already_processed": total - removed,
        "message": (
            f"{removed} pending demo requests removed. "
            f"{total - removed} already processed and left intact."
        ),
    }
