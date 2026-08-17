"""
DMFE Engine REST API — Phase 9 Pipeline Endpoints
==================================================
Exposes the full DMFE pipeline over HTTP.  All routes are ADDITIVE:
the existing dmfe_v2 endpoints (/analyze, /batches, /history,
/statistics) keep their URLs and response formats untouched.

Endpoints:
  POST /api/dmfe/compatibility-score   — compute the 5-factor CS for N requests
  POST /api/dmfe/batch/create          — run Compatibility + Batching
  POST /api/dmfe/optimize/route        — OR-Tools route for a batch / trip
  POST /api/dmfe/assign/driver         — driver selection + trip assignment
  POST /api/dmfe/run                   — full pipeline (one-click dispatch)
  GET  /api/dmfe/queue                 — pending request queue
  GET  /api/dmfe/trips                 — dispatched trips
  GET  /api/dmfe/trips/{trip_id}       — one trip
  GET  /api/dmfe/assignments           — driver-vehicle-trip assignments

All routes require an Admin bearer token (same as the rest of the API).
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import joinedload

from app.api.deps import SessionDep, CurrentUser
from app.core.json_utils import json_loads
from app.db.models import DriverAssignment, SimulationRequest, Trip
from app.dmfe.batch_generator import BatchGenerator
from app.dmfe.compatibility import CompatibilityCalculator, _get_threshold
from app.dmfe.driver_selection import complete_trip, complete_stale_trips, dispatch_trip
from app.dmfe.models import DMFEBatch
from app.dmfe.optimizer import route_optimizer
from app.dmfe.pipeline import pipeline_runner
from app.dmfe.serializers import (
    assignment_to_dict,
    candidate_batch_dict,
    compatibility_score_response,
    request_to_dict,
    trip_to_dict,
)

router = APIRouter(prefix="/api/dmfe", tags=["DMFE Engine"])

calculator = CompatibilityCalculator()
generator = BatchGenerator()


# ── Request bodies ──────────────────────────────────────────────────────────

class CompatibilityScoreRequest(BaseModel):
    request_ids: List[int] = Field(min_length=2, description="2+ request IDs")


class BatchCreateRequest(BaseModel):
    limit: int = Field(200, ge=1, le=500)


class RouteOptimizeRequest(BaseModel):
    request_ids: Optional[List[int]] = None
    batch_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    driver_id: Optional[int] = None


class DriverAssignRequest(BaseModel):
    request_ids: Optional[List[int]] = None
    batch_id: Optional[int] = None


class DMFERunRequest(BaseModel):
    limit: int = Field(200, ge=1, le=500)


# ── Serializers ─────────────────────────────────────────────────────────────
# Shared payload shapes live in app.dmfe.serializers (single source of truth).


def _load_requests(db, request_ids: List[int]) -> List[SimulationRequest]:
    """Load requests by ID, raising 400 when any is missing."""
    rows = (
        db.query(SimulationRequest)
        .filter(SimulationRequest.id.in_(request_ids))
        .all()
    )
    found = {r.id for r in rows}
    missing = set(request_ids) - found
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Request(s) not found: {sorted(missing)}",
        )
    return sorted(rows, key=lambda r: request_ids.index(r.id))


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/compatibility-score")
def compatibility_score(
    body: CompatibilityScoreRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    Compute the Phase 9 weighted Compatibility Score (5 factors) for a
    group of 2+ requests, with the full factor breakdown.

    A-DMFE (adaptive mode): the response additionally carries the context
    profile, adaptive weights, Batch Quality Score, decision confidence
    and factor attribution.  All original keys are unchanged.
    """
    requests = _load_requests(db, body.request_ids)
    result = calculator.compute(requests, db)
    threshold = _get_threshold(db)
    return compatibility_score_response(result, threshold)


@router.get("/context")
def get_adaptive_context(
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    A-DMFE context snapshot: current ContextProfile, adaptive weights,
    effective thresholds and the learning-state summary.  Additive endpoint
    — no existing route is modified.
    """
    from app.dmfe.adaptive.context import ContextAwarenessEngine
    from app.dmfe.adaptive.weights import AdaptiveWeightGenerator
    from app.dmfe.adaptive.decision import (
        effective_threshold,
        bqs_threshold,
    )
    from app.dmfe.adaptive.learning import LearningEngine
    from app.dmfe.compatibility import resolve_mode

    pending: List[SimulationRequest] = (
        db.query(SimulationRequest)
        .filter(SimulationRequest.status == "Pending")
        .limit(500)
        .all()
    )
    mode = resolve_mode(db)
    context = ContextAwarenessEngine().build(db, pending)
    weights = AdaptiveWeightGenerator(mode=mode).generate(
        db, context, LearningEngine.weight_corrections(db)
    )
    base_threshold = _get_threshold(db)

    return {
        "mode": mode,
        "context_profile": context.to_dict(),
        "adaptive_weights": {k: round(v, 4) for k, v in weights.items()},
        "effective_threshold": effective_threshold(base_threshold, context),
        "base_threshold": base_threshold,
        "bqs_threshold": bqs_threshold(context),
        "learning": LearningEngine.summary(db),
        "pending_count": len(pending),
    }


@router.post("/batch/create")
def create_batches(
    body: BatchCreateRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    Compatibility + Batching stage: returns all feasible batches (CS >=
    threshold, capacity & time gates) plus the request IDs that must be
    dispatched individually.
    """
    pending: List[SimulationRequest] = (
        db.query(SimulationRequest)
        .filter(SimulationRequest.status == "Pending")
        .order_by(SimulationRequest.created_at.asc())
        .limit(body.limit)
        .all()
    )
    threshold = _get_threshold(db)
    feasible = generator.create_feasible_batches(pending, db)

    covered: set = set()
    batches = []
    for cg in feasible:
        ids = [r.id for r in cg.requests]
        covered.update(ids)
        batch_code = f"BATCH-{ids[0]:04d}-{ids[-1]:04d}"
        batches.append(candidate_batch_dict(cg, batch_code))

    return {
        "threshold": threshold,
        "batches": batches,
        "individual_request_ids": [
            r.id for r in pending if r.id not in covered
        ],
        "total_pending": len(pending),
    }


@router.post("/optimize/route")
def optimize_route(
    body: RouteOptimizeRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    Route optimization stage: solve the OR-Tools PDP for a batch
    (batch_id) or an explicit request group.  Returns the
    AIOrchestrator-compatible route dict.
    """
    try:
        if body.batch_id is not None:
            batch = db.query(DMFEBatch).filter(DMFEBatch.id == body.batch_id).first()
            if batch is None:
                raise HTTPException(status_code=404, detail="DMFE batch not found")
            route = route_optimizer.optimize_batch(
                db, batch,
                vehicle_id=body.vehicle_id,
                driver_id=body.driver_id,
            )
        elif body.request_ids:
            requests = _load_requests(db, body.request_ids)
            route = route_optimizer.optimize_trip(
                db, requests,
                vehicle_id=body.vehicle_id,
                driver_id=body.driver_id,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide request_ids or batch_id",
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return route.to_dict()


@router.post("/assign/driver")
def assign_driver(
    body: DriverAssignRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    Driver selection + assignment stage: selects the best available
    driver/vehicle, optimizes the route from the driver depot, and
    persists Trip + DriverAssignment (requests → Assigned).
    """
    if body.batch_id is not None:
        batch = db.query(DMFEBatch).filter(DMFEBatch.id == body.batch_id).first()
        if batch is None:
            raise HTTPException(status_code=404, detail="DMFE batch not found")
        request_ids = json_loads(batch.request_ids_json, [])
        requests = _load_requests(db, request_ids)
        trip_key = batch.batch_code
    elif body.request_ids:
        requests = _load_requests(db, body.request_ids)
        batch = None
        trip_key = None
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide request_ids or batch_id",
        )

    try:
        outcome = dispatch_trip(
            db, requests, batch=batch, trip_key=trip_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    trip = outcome["trip"]
    assignment = outcome["assignment"]
    return {
        "trip": trip_to_dict(trip),
        "assignment": assignment_to_dict(assignment)
                      if assignment else None,
        "driver": {
            "id": outcome["driver"].id,
            "name": outcome["driver"].name,
            "phone": outcome["driver"].phone,
            "status": outcome["driver"].status,
        },
        "vehicle": {
            "id": outcome["vehicle"].id,
            "name": outcome["vehicle"].name,
            "vehicle_type": outcome["vehicle"].vehicle_type,
            "capacity": outcome["vehicle"].capacity,
            "mileage_kmpl": outcome["vehicle"].mileage_kmpl,
        },
        "candidate": outcome["candidate"].to_dict(),
        "requests": [request_to_dict(r) for r in outcome["requests"]],
        "route": outcome["route_dict"],
    }


@router.post("/run")
def run_pipeline(
    body: DMFERunRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    Full Phase 9 pipeline on the pending queue:

        Compatibility → Batching → Decision → Route Optimizer
        → Driver Selection → Trip Assignment

    Returns dispatch summaries; unassignable requests keep status
    'Pending' and are reported in `unassigned`.
    """
    result = pipeline_runner.run(db, limit=body.limit)
    return result.to_dict()


@router.get("/queue")
def get_queue(
    db: SessionDep,
    current_user: CurrentUser,
    limit: int = 100,
):
    """Pending requests waiting for dispatch (newest first)."""
    pending = (
        db.query(SimulationRequest)
        .filter(SimulationRequest.status == "Pending")
        .order_by(SimulationRequest.created_at.desc())
        .limit(limit)
        .all()
    )
    return [request_to_dict(r) for r in pending]


@router.get("/trips")
def list_trips(
    db: SessionDep,
    current_user: CurrentUser,
    status: Optional[str] = None,
    limit: int = 100,
):
    """Dispatched trips (optionally filtered by status)."""
    q = db.query(Trip).options(
        joinedload(Trip.driver), joinedload(Trip.vehicle)
    )
    if status:
        q = q.filter(Trip.status == status)
    trips = q.order_by(Trip.created_at.desc()).limit(limit).all()
    return [trip_to_dict(t) for t in trips]


@router.get("/trips/{trip_id}")
def get_trip(trip_id: int, db: SessionDep, current_user: CurrentUser):
    """Single trip with full details."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip_to_dict(trip)


@router.post("/trips/{trip_id}/complete")
def complete_trip_endpoint(
    trip_id: int,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    Complete a dispatched trip and release its driver/vehicle.

    This is the lifecycle transition that returns capacity to the fleet —
    without it, completed trips permanently hold drivers/vehicles Busy and
    the DMFE driver-availability gate rejects every subsequent batch.
    """
    try:
        trip = complete_trip(db, trip_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"trip": trip_to_dict(trip)}


@router.post("/trips/complete-stale")
def complete_stale_trips_endpoint(
    db: SessionDep,
    current_user: CurrentUser,
    max_age_min: int = 45,
):
    """Release trips stuck in Planned/Active for more than max_age_min."""
    released = complete_stale_trips(db, max_age_min=float(max_age_min))
    return {"released": released}


@router.get("/assignments")
def list_assignments(
    db: SessionDep,
    current_user: CurrentUser,
    status: Optional[str] = None,
    limit: int = 100,
):
    """Driver → vehicle → trip assignments (optionally by status)."""
    q = db.query(DriverAssignment).options(joinedload(DriverAssignment.trip))
    if status:
        q = q.filter(DriverAssignment.status == status)
    rows = q.order_by(DriverAssignment.assigned_at.desc()).limit(limit).all()
    return [assignment_to_dict(a) for a in rows]
