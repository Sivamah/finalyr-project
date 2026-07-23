from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db, get_current_user
from app.db import models
from app.schemas.scheduler import TripResponse, DriverLocationUpdate, DriverLocationResponse, DriverAssignmentResponse, AssignmentHistoryResponse
from app.services.scheduler_service import create_trips_from_batches, allocate_driver, respond_to_assignment, update_driver_location

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])

@router.post("/trips/create")
def trigger_trip_creation(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Reads pending DMFE batches and formalizes them as Scheduled Trips.
    """
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
    created = create_trips_from_batches(db)
    return {"message": f"Created {created} trips from batches", "trips_created": created}

@router.get("/trips", response_model=List[TripResponse])
def get_all_trips(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Returns all active trips.
    """
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    trips = db.query(models.Trip).order_by(models.Trip.created_at.desc()).all()
    return trips

@router.post("/trips/{trip_id}/assign")
def assign_driver_to_trip(trip_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Trigger the Driver Allocation Engine for a specific trip.
    """
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
    result = allocate_driver(db, trip_id)
    return result

@router.get("/assignments/pending", response_model=List[DriverAssignmentResponse])
def get_pending_assignments(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Driver gets their own pending assignments.
    """
    if current_user.role != "Driver":
        raise HTTPException(status_code=403, detail="Driver only")
        
    assignments = db.query(models.DriverAssignment).filter(
        models.DriverAssignment.driver_id == current_user.id,
        models.DriverAssignment.status == "Pending"
    ).all()
    
    return assignments

@router.post("/assignments/{assignment_id}/respond")
def respond_assignment(assignment_id: int, action: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Driver responds to an assignment offer.
    action query param: "Accept" or "Reject"
    """
    if current_user.role != "Driver":
        raise HTTPException(status_code=403, detail="Driver only")
    
    result = respond_to_assignment(db, assignment_id, current_user.id, action)
    return result

@router.get("/history", response_model=List[AssignmentHistoryResponse])
def get_assignment_history(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    View all assignment history (Admin only).
    """
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    history = db.query(models.AssignmentHistory).order_by(models.AssignmentHistory.created_at.desc()).all()
    return history

@router.post("/drivers/location", response_model=DriverLocationResponse)
def update_location(loc: DriverLocationUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Update driver's current coordinates.
    """
    if current_user.role != "Driver":
        raise HTTPException(status_code=403, detail="Driver only")
        
    return update_driver_location(db, current_user.id, loc.lat, loc.lng)

@router.get("/drivers/availability", response_model=List[DriverLocationResponse])
def get_available_drivers_location(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Returns locations of all available drivers.
    """
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
    locations = db.query(models.DriverLocation).join(
        models.DriverProfile, models.DriverLocation.driver_id == models.DriverProfile.user_id
    ).filter(models.DriverProfile.is_available == True).all()
    
    return locations
