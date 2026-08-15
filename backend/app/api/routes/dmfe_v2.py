"""
DMFE REST API — dmfe_v2
========================
Exposes four endpoints for the Dynamic Multi-Service Feasibility Engine.

Endpoints:
  POST /api/dmfe/analyze      — run DMFE on all pending requests
  GET  /api/dmfe/batches      — list persisted DMFE batches
  GET  /api/dmfe/history      — list analysis run summaries
  GET  /api/dmfe/statistics   — aggregate statistics

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
        
    return [batch_to_dict(b, db) for b in batches]


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
