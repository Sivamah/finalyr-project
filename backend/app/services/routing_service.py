from sqlalchemy.orm import Session
from fastapi import HTTPException
import json
from app.db import models
from app.engine.route_optimizer import RouteOptimizer

def generate_optimized_route(db: Session, trip_id: int):
    trip = db.query(models.Trip).filter(models.Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    batch = trip.batch
    if not batch:
        raise HTTPException(status_code=400, detail="Batch data missing")

    # Get driver location if assigned
    driver_location = (0.0, 0.0) # Default
    if trip.assignments:
        # Get accepted assignment driver location
        accepted = next((a for a in trip.assignments if a.status == "Accepted"), None)
        if accepted:
            loc = db.query(models.DriverLocation).filter(models.DriverLocation.driver_id == accepted.driver_id).first()
            if loc:
                driver_location = (loc.lat, loc.lng)

    try:
        route_stops = json.loads(batch.optimized_route_json)
    except:
        route_stops = []

    if not route_stops:
        raise HTTPException(status_code=400, detail="Invalid route data in batch")

    # Optimize route
    optimizer = RouteOptimizer(driver_location=driver_location, route_stops=route_stops)
    result = optimizer.optimize()

    if not result:
        raise HTTPException(status_code=500, detail="Failed to optimize route")

    # Save to DB
    # Remove old route detail if exists
    old_route = db.query(models.RouteDetail).filter(models.RouteDetail.trip_id == trip_id).first()
    if old_route:
        db.delete(old_route)
        db.commit()

    route_detail = models.RouteDetail(
        trip_id=trip_id,
        total_distance_km=result["total_distance_km"],
        total_duration_mins=result["total_duration_mins"],
        estimated_fuel_liters=result["estimated_fuel_liters"],
        polyline="" # Mocking polyline or could generate from stops
    )
    db.add(route_detail)
    db.commit()
    db.refresh(route_detail)

    # Save stops
    sequence = 1
    cumulative_time = 0.0
    for stop in result["optimized_stops"]:
        # simple mock eta accumulation
        cumulative_time += (result["total_duration_mins"] / len(result["optimized_stops"]))
        
        db_stop = models.OptimizedStop(
            route_id=route_detail.id,
            stop_sequence=sequence,
            lat=stop["lat"],
            lng=stop["lng"],
            address=stop.get("address", ""),
            action=stop.get("action", "pickup"),
            eta_mins=cumulative_time
        )
        db.add(db_stop)
        sequence += 1

    db.commit()
    db.refresh(route_detail)
    return route_detail

def get_route_details(db: Session, trip_id: int):
    route = db.query(models.RouteDetail).filter(models.RouteDetail.trip_id == trip_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found for this trip")
    return route
