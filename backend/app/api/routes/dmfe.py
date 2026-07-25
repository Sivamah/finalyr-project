from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db, get_current_user, CurrentUser, SessionDep
from app.db import models
from app.schemas.dmfe import DMFEEvaluateResponse, BatchedTripResponse, BatchStatusUpdate
from app.services.dmfe_service import evaluate_and_batch_requests
from app.services import notification_service
from app.db.models import BatchedTrip, BookingStatus, DriverProfile
import json

router = APIRouter(prefix="/api/dmfe", tags=["DMFE"])

@router.post("/evaluate", response_model=DMFEEvaluateResponse)
def trigger_dmfe(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Manually triggers the DMFE to evaluate all pending requests and batch them.
    Restricted to Admins in a production setting, but for this academic project,
    any authenticated user can trigger it for demo purposes.
    """
    batches_created = evaluate_and_batch_requests(db)
    return {"message": "DMFE Optimization completed", "batches_created": batches_created}

@router.get("/batches", response_model=List[BatchedTripResponse])
def get_available_batches(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns pending batches for drivers to view and accept.
    """
    batches = db.query(models.BatchedTrip).filter(models.BatchedTrip.status == "Pending").all()
    return batches

@router.patch("/batches/{batch_id}/accept", summary="Driver accepts a batched trip")
async def accept_batch(
    batch_id: int, db: SessionDep, current_user: CurrentUser
):
    if current_user.role != "Driver":
        raise HTTPException(403, "Not authorized")

    batch = db.query(BatchedTrip).filter(BatchedTrip.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    if batch.status != BookingStatus.Pending:
        raise HTTPException(400, "Only Pending batches can be accepted")

    if batch.driver_id is not None:
        raise HTTPException(409, "Already accepted by another driver")

    batch.driver_id = current_user.id
    batch.status = BookingStatus.Accepted

    # Also update child bookings
    customer_ids = set()
    for b in batch.ride_bookings:
        b.status = BookingStatus.Accepted
        b.driver_id = current_user.id
        customer_ids.add(b.customer_id)
    for b in batch.food_bookings:
        b.status = BookingStatus.Accepted
        b.driver_id = current_user.id
        customer_ids.add(b.customer_id)
    for b in batch.parcel_bookings:
        b.status = BookingStatus.Accepted
        b.driver_id = current_user.id
        customer_ids.add(b.customer_id)

    db.commit()
    
    # Notify customers
    for cid in customer_ids:
        await notification_service.notify_user(
            db, cid,
            title="Driver Assigned (Batched)",
            message=f"{current_user.full_name} has accepted your trip as part of an optimized batch.",
            notification_type="SUCCESS"
        )

    return {"message": "Batch accepted"}

@router.patch("/batches/{batch_id}/status", summary="Update batch status")
async def update_batch_status(
    batch_id: int, data: BatchStatusUpdate, db: SessionDep, current_user: CurrentUser
):
    if current_user.role != "Driver":
        raise HTTPException(403, "Not authorized")

    batch = db.query(BatchedTrip).filter(BatchedTrip.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    if batch.driver_id != current_user.id:
        raise HTTPException(403, "Not assigned to this batch")

    batch.status = data.status

    customer_ids = set()
    for b in batch.ride_bookings:
        b.status = data.status
        customer_ids.add(b.customer_id)
    for b in batch.food_bookings:
        b.status = data.status
        customer_ids.add(b.customer_id)
    for b in batch.parcel_bookings:
        b.status = data.status
        customer_ids.add(b.customer_id)

    # Commit status changes first to ensure data integrity
    db.commit()

    if data.status == BookingStatus.Completed:
        profile = db.query(DriverProfile).filter(DriverProfile.user_id == current_user.id).first()
        if profile:
            profile.total_trips += 1
            db.commit()
            
        for cid in customer_ids:
            await notification_service.notify_user(
                db, cid,
                title="Trip Completed",
                message=f"Your batched trip has been completed.",
                notification_type="SUCCESS"
            )
    elif data.status == BookingStatus.In_Progress:
        for cid in customer_ids:
            await notification_service.notify_user(
                db, cid,
                title="Driver En Route",
                message=f"Your driver is now en route.",
                notification_type="INFO"
            )

    return {"message": f"Batch status updated to {data.status}"}


# ══════════════════════════════════════════════
# Phase 8 — AI Decision History Endpoints
# ══════════════════════════════════════════════

from app.schemas.dmfe import AIDecisionResponse
from app.db.models import AIDecision

@router.get("/decisions", response_model=List[AIDecisionResponse],
            summary="List all AI decisions (paginated)")
def list_decisions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    decisions = (
        db.query(AIDecision)
        .order_by(AIDecision.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return decisions


@router.get("/decisions/{decision_id}", response_model=AIDecisionResponse,
            summary="Get a single AI decision with full explanation")
def get_decision(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    decision = db.query(AIDecision).filter(AIDecision.id == decision_id).first()
    if not decision:
        raise HTTPException(404, "AI Decision not found")
    return decision

