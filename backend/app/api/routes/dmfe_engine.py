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

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import SessionDep, CurrentUser
from app.db.models import DriverAssignment, SimulationRequest, Trip
from app.dmfe.batch_generator import BatchGenerator
from app.dmfe.compatibility import CompatibilityCalculator
from app.dmfe.decision_engine import _get_threshold
from app.dmfe.driver_selection import dispatch_trip
from app.dmfe.models import DMFEBatch
from app.dmfe.optimizer import route_optimizer
from app.dmfe.pipeline import PipelineRunner, pipeline_runner

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

def _request_to_dict(r: SimulationRequest) -> Dict[str, Any]:
    return {
        "id": r.id,
        "request_type": r.request_type,
        "pickup_address": r.pickup_address,
        "drop_address": r.drop_address,
        "pickup_lat": r.pickup_lat,
        "pickup_lng": r.pickup_lng,
        "drop_lat": r.drop_lat,
        "drop_lng": r.drop_lng,
        "demand": r.demand,
        "weight_kg": r.weight_kg,
        "priority": r.priority,
        "vehicle_type": r.vehicle_type,
        "estimated_distance_km": r.estimated_distance_km,
        "status": r.status,
        "created_at": r.created_at.strftime("%Y-%m-%d %I:%M %p")
                     if r.created_at else "",
    }


def _trip_to_dict(t: Trip) -> Dict[str, Any]:
    return {
        "id": t.id,
        "trip_code": t.trip_code,
        "batch_id": t.batch_id,
        "driver_id": t.driver_id,
        "vehicle_id": t.vehicle_id,
        "request_ids": json.loads(t.request_ids_json or "[]"),
        "is_shared": t.is_shared,
        "status": t.status,
        "stop_order": json.loads(t.stop_order_json or "[]"),
        "total_distance_km": t.total_distance_km,
        "total_duration_min": t.total_duration_min,
        "eta_min": t.eta_min,
        "fuel_l": t.fuel_l,
        "utilization_pct": t.utilization_pct,
        "max_delay_min": t.max_delay_min,
        "matrix_source": t.matrix_source,
        "estimated_cost": t.estimated_cost,
        "distance_saved_km": t.distance_saved_km,
        "fuel_saved_l": t.fuel_saved_l,
        "co2_saved_kg": t.co2_saved_kg,
        "optimization_score": t.optimization_score,
        "driver_name": t.driver.name if t.driver else None,
        "vehicle_name": t.vehicle.name if t.vehicle else None,
        "created_at": t.created_at.strftime("%Y-%m-%d %I:%M %p")
                     if t.created_at else "",
    }


def _assignment_to_dict(a: DriverAssignment) -> Dict[str, Any]:
    return {
        "id": a.id,
        "trip_id": a.trip_id,
        "trip_code": a.trip.trip_code if a.trip else None,
        "driver_id": a.driver_id,
        "vehicle_id": a.vehicle_id,
        "driver_name": a.driver_name,
        "vehicle_name": a.vehicle_name,
        "assignment_type": a.assignment_type,
        "status": a.status,
        "assigned_at": a.assigned_at.strftime("%Y-%m-%d %I:%M %p")
                       if a.assigned_at else "",
    }


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
    """
    requests = _load_requests(db, body.request_ids)
    result = calculator.compute(requests, db)
    threshold = _get_threshold(db)
    return {
        "request_ids": body.request_ids,
        "compatibility_score": result.compatibility_score,
        "factor_scores": result.factor_scores,
        "factor_details": result.factor_details,
        "reasons": result.reasons,
        "estimated_delay_min": result.estimated_delay_min,
        "weights_used": result.weights_used,
        "threshold": threshold,
        "decision": "Compatible" if result.compatibility_score >= threshold
                    else "Individual",
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
        batches.append({
            "batch_code": f"BATCH-{ids[0]:04d}-{ids[-1]:04d}",
            "request_ids": ids,
            "requests_summary": [
                {
                    "id": r.id,
                    "request_type": r.request_type,
                    "pickup_address": r.pickup_address,
                    "drop_address": r.drop_address,
                    "priority": r.priority,
                    "demand": r.demand,
                }
                for r in cg.requests
            ],
            "compatibility_score": cg.result.compatibility_score,
            "factor_scores": cg.result.factor_scores,
            "factor_details": cg.result.factor_details,
            "reasons": cg.result.reasons,
            "estimated_delay_min": cg.result.estimated_delay_min,
            "weights_used": cg.result.weights_used,
        })

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
        request_ids = json.loads(batch.request_ids_json or "[]")
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
        "trip": _trip_to_dict(trip),
        "assignment": _assignment_to_dict(assignment)
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
        "requests": [_request_to_dict(r) for r in outcome["requests"]],
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
    return [_request_to_dict(r) for r in pending]


@router.get("/trips")
def list_trips(
    db: SessionDep,
    current_user: CurrentUser,
    status: Optional[str] = None,
    limit: int = 100,
):
    """Dispatched trips (optionally filtered by status)."""
    q = db.query(Trip)
    if status:
        q = q.filter(Trip.status == status)
    trips = q.order_by(Trip.created_at.desc()).limit(limit).all()
    return [_trip_to_dict(t) for t in trips]


@router.get("/trips/{trip_id}")
def get_trip(trip_id: int, db: SessionDep, current_user: CurrentUser):
    """Single trip with full details."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return _trip_to_dict(trip)


@router.get("/assignments")
def list_assignments(
    db: SessionDep,
    current_user: CurrentUser,
    status: Optional[str] = None,
    limit: int = 100,
):
    """Driver → vehicle → trip assignments (optionally by status)."""
    q = db.query(DriverAssignment)
    if status:
        q = q.filter(DriverAssignment.status == status)
    rows = q.order_by(DriverAssignment.assigned_at.desc()).limit(limit).all()
    return [_assignment_to_dict(a) for a in rows]
