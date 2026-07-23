import json
from sqlalchemy.orm import Session
from app.db import models
from app.engine.dmfe import DMFE_Optimizer
from app.services.explainability import generate_decision


def evaluate_and_batch_requests(db: Session):
    """
    Fetches all pending requests that are not yet batched,
    and runs the DMFE optimizer to group them.
    Now also generates AI Decision records with explainability (Phase 8).
    """
    # 1. Fetch available drivers (vehicles)
    drivers = db.query(models.DriverProfile).filter(models.DriverProfile.is_available.is_(True)).all()
    vehicles = []
    for d in drivers:
        capacity = 4 if d.vehicle_type in ["Car", "Van", "Truck"] else 2
        vehicles.append({
            "id": d.user_id,
            "type": d.vehicle_type,
            "capacity": capacity
        })
    
    driver_available = len(vehicles) > 0

    # If no drivers, we can still form batches to be accepted later by any driver
    if not vehicles:
        vehicles = [{"id": None, "type": "Generic", "capacity": 4} for _ in range(5)]

    # 2. Fetch pending requests
    pending_rides = db.query(models.RideBooking).filter(
        models.RideBooking.status == "Pending", 
        models.RideBooking.batch_id.is_(None)
    ).all()
    
    pending_foods = db.query(models.FoodBooking).filter(
        models.FoodBooking.status == "Pending", 
        models.FoodBooking.batch_id.is_(None)
    ).all()
    
    pending_parcels = db.query(models.ParcelBooking).filter(
        models.ParcelBooking.status == "Pending", 
        models.ParcelBooking.batch_id.is_(None)
    ).all()

    requests = []
    for r in pending_rides:
        requests.append({
            "id": r.id,
            "type": "ride",
            "pickup_lat": r.pickup_lat,
            "pickup_lng": r.pickup_lng,
            "drop_lat": r.drop_lat,
            "drop_lng": r.drop_lng,
            "pickup_address": r.pickup_address,
            "drop_address": r.drop_address,
            "demand": 1,
            "fare": r.estimated_fare or 0.0
        })
        
    for f in pending_foods:
        requests.append({
            "id": f.id,
            "type": "food",
            "pickup_lat": f.restaurant_lat,
            "pickup_lng": f.restaurant_lng,
            "drop_lat": f.delivery_lat,
            "drop_lng": f.delivery_lng,
            "pickup_address": f.restaurant_address,
            "drop_address": f.delivery_address,
            "demand": 1,
            "fare": f.estimated_fare or 0.0
        })
        
    for p in pending_parcels:
        requests.append({
            "id": p.id,
            "type": "parcel",
            "pickup_lat": p.pickup_lat,
            "pickup_lng": p.pickup_lng,
            "drop_lat": p.drop_lat,
            "drop_lng": p.drop_lng,
            "pickup_address": p.pickup_address,
            "drop_address": p.drop_address,
            "demand": 1,
            "fare": p.estimated_fare or 0.0
        })

    if not requests:
        return 0  # No requests to batch

    # 3. Optimize
    optimizer = DMFE_Optimizer(vehicles=vehicles, requests=requests)
    batches = optimizer.solve()

    batches_created = 0

    # 4. Save batches to DB + generate AI decisions
    for b in batches:
        route = b["route"]
        if len(route) < 2:
            continue  # Needs at least one pickup and one drop
        
        total_fare = 0.0
        stops = []
        for stop in route:
            req = stop["req"]
            action = stop["action"]
            
            if action == "pickup":
                total_fare += req["fare"]
                
            stops.append({
                "action": action,
                "booking_type": req["type"],
                "booking_id": req["id"],
                "lat": req["pickup_lat"] if action == "pickup" else req["drop_lat"],
                "lng": req["pickup_lng"] if action == "pickup" else req["drop_lng"],
                "address": req["pickup_address"] if action == "pickup" else req["drop_address"]
            })

        batch_distance_km = b["distance_m"] / 1000.0

        new_batch = models.BatchedTrip(
            driver_id=None,
            status="Pending",
            total_estimated_fare=total_fare,
            total_distance_km=batch_distance_km,
            optimized_route_json=json.dumps(stops)
        )
        db.add(new_batch)
        db.commit()
        db.refresh(new_batch)
        batches_created += 1
        
        # Link original bookings to this batch
        req_ids = set((stop["req"]["type"], stop["req"]["id"]) for stop in route)
        batch_requests = []
        for r_type, r_id in req_ids:
            if r_type == "ride":
                obj = db.query(models.RideBooking).get(r_id)
            elif r_type == "food":
                obj = db.query(models.FoodBooking).get(r_id)
            else:
                obj = db.query(models.ParcelBooking).get(r_id)
                
            if obj:
                obj.batch_id = new_batch.id
            
            # Collect request data for explainability
            for orig_req in requests:
                if orig_req["type"] == r_type and orig_req["id"] == r_id:
                    batch_requests.append(orig_req)
                    break

        db.commit()

        # ── Phase 8: Generate AI Decision with Explainability ──
        generate_decision(
            db=db,
            batch=new_batch,
            requests=batch_requests,
            batch_distance_km=batch_distance_km,
            driver_available=driver_available,
        )
        
    return batches_created

