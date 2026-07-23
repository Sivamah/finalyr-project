import math
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
import json
from app.db import models
from app.schemas.scheduler import TripCreate

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    if None in (lat1, lon1, lat2, lon2):
        return float('inf')

    # convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r

def create_trips_from_batches(db: Session):
    """
    Finds all Pending BatchedTrips without a Trip record and creates Trips for them.
    Returns the number of trips created.
    """
    # Find batches that are Pending and don't have a Trip associated
    pending_batches = db.query(models.BatchedTrip).outerjoin(models.Trip).filter(
        models.BatchedTrip.status == "Pending",
        models.Trip.id == None
    ).all()

    created_count = 0
    for batch in pending_batches:
        try:
            route = json.loads(batch.optimized_route_json)
            # Determine priority (could be based on service type or deadline, simplifying to Medium)
            priority = "Medium"
            # Determine type
            trip_type = "Combined" if len(route) > 2 else "Single" # More than 1 pickup+drop

            new_trip = models.Trip(
                batch_id=batch.id,
                trip_type=trip_type,
                priority=priority,
                status="Pending"
            )
            db.add(new_trip)
            created_count += 1
        except Exception as e:
            continue
            
    db.commit()
    return created_count

def allocate_driver(db: Session, trip_id: int):
    """
    Executes Driver Allocation Engine for a specific trip.
    """
    trip = db.query(models.Trip).filter(models.Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
        
    if trip.status not in ["Pending", "Queued"]:
        raise HTTPException(status_code=400, detail=f"Trip cannot be allocated in status {trip.status}")

    batch = trip.batch
    if not batch:
        raise HTTPException(status_code=400, detail="Batch data missing")

    try:
        route = json.loads(batch.optimized_route_json)
        first_stop = route[0] if route else None
    except:
        first_stop = None

    if not first_stop:
        raise HTTPException(status_code=400, detail="Invalid route data")

    pickup_lat = first_stop.get("lat")
    pickup_lng = first_stop.get("lng")

    # Determine required vehicle type (simple logic based on first booking)
    required_vehicle = "Bike"
    booking_type = first_stop.get("booking_type")
    
    # 1. Fetch available drivers (online, not currently busy)
    # Busy drivers have an active trip (Assigned, Accepted, In_Progress)
    busy_driver_ids = db.query(models.Trip.id).join(models.BatchedTrip, models.Trip.batch_id == models.BatchedTrip.id).filter(
        models.Trip.status.in_(["Assigned", "Accepted", "In_Progress"])
    ).subquery()
    
    # Also drivers with pending assignments
    pending_assignment_driver_ids = db.query(models.DriverAssignment.driver_id).filter(
        models.DriverAssignment.status == "Pending",
        models.DriverAssignment.expires_at > datetime.utcnow()
    ).subquery()

    available_drivers = db.query(models.DriverProfile, models.DriverLocation).join(
        models.DriverLocation, models.DriverProfile.user_id == models.DriverLocation.driver_id
    ).filter(
        models.DriverProfile.is_available == True,
        ~models.DriverProfile.user_id.in_(pending_assignment_driver_ids)
        # Assuming we allow multiple trips if DMFE batsched them, but DMFE already groups bookings.
        # If the driver already has an active trip, we probably shouldn't assign another unless it's a queued batched trip for them.
        # For simplicity, we exclude drivers who have an active assignment.
    ).all()

    best_driver = None
    best_score = -float('inf')

    for profile, location in available_drivers:
        # Distance calculation
        distance_km = haversine_distance(pickup_lat, pickup_lng, location.lat, location.lng)
        
        # Scoring Weights
        # Base score starts at 100
        # -10 points per km
        # +5 points per rating star
        # -2 points per total trip (prefer to balance workload, optional)
        score = 100 - (distance_km * 10) + (profile.rating * 5) - (profile.total_trips * 0.1)

        # Check vehicle capability (simplified: if Car needed, driver must have Car. If Bike needed, Bike is fine)
        if booking_type == "ride":
            # Just matching what they have, normally we check actual request type
            pass

        if score > best_score:
            best_score = score
            best_driver = profile

    if not best_driver:
        trip.status = "Queued"
        db.commit()
        return {"message": "No driver available. Trip queued.", "assigned": False}

    # Create Assignment
    assignment = models.DriverAssignment(
        trip_id=trip.id,
        driver_id=best_driver.user_id,
        status="Pending",
        score=best_score,
        expires_at=datetime.utcnow() + timedelta(minutes=1) # 1 min to accept
    )
    db.add(assignment)
    
    # Log History
    history = models.AssignmentHistory(
        trip_id=trip.id,
        driver_id=best_driver.user_id,
        status="Offered",
        reason="System Auto-Assignment"
    )
    db.add(history)

    trip.status = "Assigned"
    db.commit()

    return {
        "message": "Driver allocated successfully",
        "assigned": True,
        "driver_id": best_driver.user_id,
        "score": best_score
    }

def respond_to_assignment(db: Session, assignment_id: int, driver_id: int, action: str):
    """
    Driver accepts or rejects an assignment.
    action: "Accept" or "Reject"
    """
    assignment = db.query(models.DriverAssignment).filter(
        models.DriverAssignment.id == assignment_id,
        models.DriverAssignment.driver_id == driver_id
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.status != "Pending":
        raise HTTPException(status_code=400, detail=f"Assignment already processed: {assignment.status}")

    if assignment.expires_at < datetime.utcnow():
        assignment.status = "Expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Assignment offer expired")

    trip = assignment.trip

    if action == "Accept":
        assignment.status = "Accepted"
        trip.status = "Accepted"
        trip.batch.status = "Accepted"
        trip.batch.driver_id = driver_id
        
        # Link to bookings
        for rb in trip.batch.ride_bookings:
            rb.driver_id = driver_id
            rb.status = "Accepted"
        for fb in trip.batch.food_bookings:
            fb.driver_id = driver_id
            fb.status = "Accepted"
        for pb in trip.batch.parcel_bookings:
            pb.driver_id = driver_id
            pb.status = "Accepted"

        history = models.AssignmentHistory(
            trip_id=trip.id,
            driver_id=driver_id,
            status="Accepted",
            reason="Driver accepted offer"
        )
        db.add(history)

    elif action == "Reject":
        assignment.status = "Rejected"
        trip.status = "Queued" # Send back to queue for next allocation cycle

        history = models.AssignmentHistory(
            trip_id=trip.id,
            driver_id=driver_id,
            status="Rejected",
            reason="Driver rejected offer"
        )
        db.add(history)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    db.commit()
    return {"message": f"Assignment {action.lower()}ed successfully"}

def update_driver_location(db: Session, driver_id: int, lat: float, lng: float):
    location = db.query(models.DriverLocation).filter(models.DriverLocation.driver_id == driver_id).first()
    if not location:
        location = models.DriverLocation(driver_id=driver_id, lat=lat, lng=lng)
        db.add(location)
    else:
        location.lat = lat
        location.lng = lng
        location.last_updated = datetime.utcnow()
    db.commit()
    return location
