from fastapi import APIRouter, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
import io
import csv

from app.api.deps import SessionDep, CurrentUser
from app.db.models import (
    User, DriverProfile, RideBooking, FoodBooking, ParcelBooking, BatchedTrip, BookingStatus
)

router = APIRouter()

def require_admin(user: User):
    if user.role != "Admin":
        raise HTTPException(403, "Admin access required")

@router.get("/summary", summary="Get dashboard summary KPIs")
def get_summary(db: SessionDep, current_user: CurrentUser):
    require_admin(current_user)
    
    total_users = db.query(func.count(User.id)).scalar()
    active_customers = db.query(func.count(User.id)).filter(User.role == "Customer").scalar()
    active_drivers = db.query(func.count(User.id)).filter(User.role == "Driver").scalar()
    online_drivers = db.query(func.count(DriverProfile.id)).filter(DriverProfile.is_available == True).scalar()

    # Trips breakdown
    ride_counts = db.query(RideBooking.status, func.count(RideBooking.id)).group_by(RideBooking.status).all()
    food_counts = db.query(FoodBooking.status, func.count(FoodBooking.id)).group_by(FoodBooking.status).all()
    parcel_counts = db.query(ParcelBooking.status, func.count(ParcelBooking.id)).group_by(ParcelBooking.status).all()
    
    counts_by_status = {}
    for st, count in ride_counts + food_counts + parcel_counts:
        counts_by_status[st] = counts_by_status.get(st, 0) + count
        
    total_trips = sum(counts_by_status.values())
    completed_trips = counts_by_status.get(BookingStatus.Completed, 0)
    cancelled_trips = counts_by_status.get(BookingStatus.Cancelled, 0)
    pending_trips = counts_by_status.get(BookingStatus.Pending, 0)

    # DMFE / Batches
    batches = db.query(BatchedTrip).all()
    combined_trips = sum(1 for b in batches if len(b.ride_bookings) + len(b.food_bookings) + len(b.parcel_bookings) > 1)
    single_trips = total_trips - combined_trips # simplified logic: total independent or single-batched requests

    # Fuel / CO2
    # Assuming 15km / L and 2.3kg CO2 / L
    total_distance = sum(b.total_distance_km for b in batches)
    # distance if unbatched
    unbatched_distance = 0
    for b in batches:
        for r in b.ride_bookings:
            unbatched_distance += r.distance_km or 0
        for f in b.food_bookings:
            unbatched_distance += f.distance_km or 0
        for p in b.parcel_bookings:
            unbatched_distance += p.distance_km or 0
            
    saved_distance = max(0, unbatched_distance - total_distance)
    fuel_saved = saved_distance / 15.0
    co2_reduction = fuel_saved * 2.3

    avg_rating = db.query(func.avg(DriverProfile.rating)).scalar() or 0.0

    return {
        "total_users": total_users,
        "active_customers": active_customers,
        "active_drivers": active_drivers,
        "online_drivers": online_drivers,
        "total_trips": total_trips,
        "completed_trips": completed_trips,
        "cancelled_trips": cancelled_trips,
        "pending_trips": pending_trips,
        "combined_trips": combined_trips,
        "single_trips": single_trips,
        "average_rating": round(avg_rating, 1),
        "fuel_saved_l": round(fuel_saved, 1),
        "co2_reduction_kg": round(co2_reduction, 1),
        "total_distance_km": round(total_distance, 1)
    }

@router.get("/trips", summary="Get trip analytics for charts")
def get_trips_analytics(db: SessionDep, current_user: CurrentUser):
    require_admin(current_user)
    # Time series of trips created_at by day
    # SQLite friendly query for DATE(created_at)
    rides = db.query(func.date(RideBooking.created_at).label("d"), func.count(RideBooking.id)).group_by("d").all()
    food = db.query(func.date(FoodBooking.created_at).label("d"), func.count(FoodBooking.id)).group_by("d").all()
    parcels = db.query(func.date(ParcelBooking.created_at).label("d"), func.count(ParcelBooking.id)).group_by("d").all()

    daily_map = {}
    for d, c in rides:
        daily_map[d] = daily_map.get(d, 0) + c
    for d, c in food:
        daily_map[d] = daily_map.get(d, 0) + c
    for d, c in parcels:
        daily_map[d] = daily_map.get(d, 0) + c

    # Sort by date
    trend = [{"date": d, "trips": c} for d, c in sorted(daily_map.items())]

    return {
        "trend": trend,
    }

@router.get("/drivers", summary="Get driver analytics for charts")
def get_driver_analytics(db: SessionDep, current_user: CurrentUser):
    require_admin(current_user)
    available = db.query(func.count(DriverProfile.id)).filter(DriverProfile.is_available == True).scalar()
    unavailable = db.query(func.count(DriverProfile.id)).filter(DriverProfile.is_available == False).scalar()
    
    # Types
    vehicle_types = db.query(DriverProfile.vehicle_type, func.count(DriverProfile.id)).group_by(DriverProfile.vehicle_type).all()
    vehicle_breakdown = [{"name": v[0], "value": v[1]} for v in vehicle_types]
    
    return {
        "status": [
            {"name": "Online", "value": available},
            {"name": "Offline", "value": unavailable}
        ],
        "vehicles": vehicle_breakdown
    }

@router.get("/export", summary="Export analytics data")
def export_analytics(type: str, report: str, db: SessionDep, current_user: CurrentUser):
    require_admin(current_user)
    if type != "csv":
        raise HTTPException(400, "Only CSV export is supported right now")
        
    output = io.StringIO()
    writer = csv.writer(output)

    if report == "trips":
        writer.writerow(["ID", "Type", "Status", "Created At", "Customer ID"])
        rides = db.query(RideBooking).all()
        for r in rides: writer.writerow([r.id, "Ride", r.status, r.created_at, r.customer_id])
        foods = db.query(FoodBooking).all()
        for f in foods: writer.writerow([f.id, "Food", f.status, f.created_at, f.customer_id])
        parcels = db.query(ParcelBooking).all()
        for p in parcels: writer.writerow([p.id, "Parcel", p.status, p.created_at, p.customer_id])
        filename = "trips_export.csv"
        
    elif report == "drivers":
        writer.writerow(["ID", "Name", "Vehicle", "Rating", "Total Trips", "Available"])
        drivers = db.query(DriverProfile).all()
        for d in drivers:
            name = d.user.full_name if d.user else "Unknown"
            writer.writerow([d.id, name, d.vehicle_type, d.rating, d.total_trips, d.is_available])
        filename = "drivers_export.csv"
    else:
        raise HTTPException(400, "Unknown report type")

    response = Response(content=output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "text/csv"
    return response


# ══════════════════════════════════════════════
# Phase 8 — DMFE Analytics
# ══════════════════════════════════════════════

from app.db.models import AIDecision

@router.get("/dmfe", summary="Get DMFE performance analytics")
def get_dmfe_analytics(db: SessionDep, current_user: CurrentUser):
    require_admin(current_user)

    decisions = db.query(AIDecision).all()
    if not decisions:
        return {
            "total_decisions": 0,
            "combined_count": 0,
            "single_count": 0,
            "avg_feasibility": 0,
            "avg_route_similarity": 0,
            "avg_delay_min": 0,
            "avg_fuel_saved_pct": 0,
            "avg_co2_reduction_pct": 0,
            "score_distribution": [],
        }

    combined = [d for d in decisions if d.decision_type == "combined"]
    single   = [d for d in decisions if d.decision_type == "single"]

    avg_f = sum(d.feasibility_score for d in decisions) / len(decisions)
    avg_r = sum(d.route_similarity   for d in decisions) / len(decisions)
    avg_d = sum(d.estimated_delay_min for d in decisions) / len(decisions)
    avg_fuel = sum(d.fuel_saved_pct    for d in decisions) / len(decisions)
    avg_co2  = sum(d.co2_reduction_pct for d in decisions) / len(decisions)

    # Score distribution buckets: 0-20, 20-40, 40-60, 60-80, 80-100
    buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for d in decisions:
        s = d.feasibility_score
        if s < 20:   buckets["0-20"]   += 1
        elif s < 40: buckets["20-40"]  += 1
        elif s < 60: buckets["40-60"]  += 1
        elif s < 80: buckets["60-80"]  += 1
        else:        buckets["80-100"] += 1

    score_dist = [{"range": k, "count": v} for k, v in buckets.items()]

    return {
        "total_decisions": len(decisions),
        "combined_count": len(combined),
        "single_count": len(single),
        "avg_feasibility": round(avg_f, 1),
        "avg_route_similarity": round(avg_r, 1),
        "avg_delay_min": round(avg_d, 1),
        "avg_fuel_saved_pct": round(avg_fuel, 1),
        "avg_co2_reduction_pct": round(avg_co2, 1),
        "score_distribution": score_dist,
    }

