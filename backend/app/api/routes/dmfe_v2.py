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

import json
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Query
from sqlalchemy import func

from app.api.deps import SessionDep, CurrentUser
from app.dmfe.models import DMFEBatch, DMFEAnalysisRun
from app.dmfe.decision_engine import decision_engine

router = APIRouter(prefix="/api/dmfe", tags=["DMFE"])


# ── Helpers ────────────────────────────────────────────────────────────────

def _batch_to_dict(b: DMFEBatch) -> Dict[str, Any]:
    return {
        "id": b.id,
        "batch_code": b.batch_code,
        "analysis_run_id": b.analysis_run_id,
        "request_ids": json.loads(b.request_ids_json or "[]"),
        "compatibility_score": b.compatibility_score,
        "decision": b.decision,
        "reasons": json.loads(b.reason_json or "[]"),
        "factor_scores": json.loads(b.factor_scores_json or "{}"),
        "status": b.status,
        "estimated_delay_min": b.estimated_delay_min,
        "created_at": b.created_at.strftime("%Y-%m-%d %I:%M %p") if b.created_at else "",
    }


def _run_to_dict(r: DMFEAnalysisRun) -> Dict[str, Any]:
    return {
        "id": r.id,
        "total_pending": r.total_pending,
        "total_evaluated_pairs": r.total_evaluated_pairs,
        "batches_created": r.batches_created,
        "rejected_count": r.rejected_count,
        "avg_compatibility_score": r.avg_compatibility_score,
        "threshold_used": r.threshold_used,
        "run_at": r.run_at.strftime("%Y-%m-%d %I:%M %p") if r.run_at else "",
    }


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
    return {
        "run_id": result.run_id,
        "total_pending": result.total_pending,
        "total_pairs_evaluated": result.total_pairs_evaluated,
        "batches_created": result.batches_created,
        "rejected_count": result.rejected_count,
        "avg_compatibility_score": result.avg_compatibility_score,
        "threshold_used": result.threshold_used,
        "compatible_batches": result.compatible_batches,
        "rejected_batches": result.rejected_batches,
        "unmatched_request_ids": result.unmatched_request_ids,
    }


@router.get("/batches")
def list_batches(
    db: SessionDep,
    current_user: CurrentUser,
    status: Optional[str] = Query(None, description="Filter by status: Pending | Rejected"),
    run_id: Optional[int] = Query(None, description="Filter by analysis run ID"),
    limit: int = Query(100, le=500),
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
    batches = q.order_by(DMFEBatch.created_at.desc()).limit(limit).all()
    return [_batch_to_dict(b) for b in batches]


@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, db: SessionDep, current_user: CurrentUser):
    """Return a single DMFE batch with full factor breakdown."""
    from fastapi import HTTPException
    b = db.query(DMFEBatch).filter(DMFEBatch.id == batch_id).first()
    if not b:
        raise HTTPException(404, "DMFE batch not found")
    return _batch_to_dict(b)


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
    return [_run_to_dict(r) for r in runs]


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

    batch_rate = round(
        (total_batches / total_pairs * 100), 1
    ) if total_pairs and total_pairs > 0 else 0.0

    return {
        "total_runs": total_runs,
        "total_pairs_evaluated": int(total_pairs or 0),
        "total_batches_created": int(total_batches or 0),
        "total_rejected": int(total_rejected or 0),
        "batch_rate_pct": batch_rate,
        "avg_compatibility_score": round(float(avg_score), 1),
        "latest_threshold": latest_run.threshold_used if latest_run else 70.0,
        "last_run_at": latest_run.run_at.strftime("%Y-%m-%d %I:%M %p") if latest_run else None,
    }
