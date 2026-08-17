from fastapi import APIRouter
from sqlalchemy import func
from app.db.models import Provider, Vehicle, SimulationRequest, Driver
from app.dmfe.models import DMFEBatch
from app.api.deps import SessionDep, CurrentUser
from app.schemas.orchestration import DashboardStats

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: SessionDep, current_user: CurrentUser):
    total_providers = db.query(func.count(Provider.id)).scalar()
    total_vehicles = db.query(func.count(Vehicle.id)).scalar()
    total_requests = db.query(func.count(SimulationRequest.id)).scalar()
    total_batches = db.query(func.count(DMFEBatch.id)).scalar()

    # Active = currently available or in service (i.e. not offline/maintenance),
    # mirroring the definitions used by /api/drivers/stats and /api/vehicles/stats.
    active_drivers = db.query(func.count(Driver.id)).filter(
        func.lower(Driver.status).in_(["available", "busy"])
    ).scalar()
    active_vehicles = db.query(func.count(Vehicle.id)).filter(
        func.lower(Vehicle.status).in_(["available", "busy"])
    ).scalar()

    from app.db.models import Trip
    total_optimizations = db.query(func.count(Trip.id)).scalar()

    avg_savings, total_fuel, total_co2, trip_count = db.query(
        func.avg(Trip.distance_saved_km),
        func.coalesce(func.sum(Trip.fuel_saved_l), 0.0),
        func.coalesce(func.sum(Trip.co2_saved_kg), 0.0),
        func.count(Trip.id),
    ).one()
    shared_trips = (
        db.query(func.count(Trip.id)).filter(Trip.is_shared.is_(True)).scalar()
    )
    batch_rate = (shared_trips / trip_count) * 100.0 if trip_count else 0.0

    return {
        "total_providers": total_providers,
        "total_vehicles": total_vehicles,
        "total_requests": total_requests,
        "total_optimizations": total_optimizations,
        "avg_route_savings": round((avg_savings or 0.0), 2),
        "fuel_saved": round((total_fuel or 0.0), 2),
        "co2_reduction": round((total_co2 or 0.0), 2),
        "batch_rate": round(batch_rate, 2),
        "active_drivers": active_drivers,
        "active_vehicles": active_vehicles,
        "total_batches": total_batches,
    }


@router.get("/providers/breakdown")
def get_provider_breakdown(db: SessionDep, current_user: CurrentUser):
    types = db.query(Provider.provider_type, func.count(Provider.id)).group_by(Provider.provider_type).all()
    return [{"type": t, "count": c} for t, c in types]


@router.get("/results/recent")
def get_recent_results(db: SessionDep, current_user: CurrentUser, limit: int = 10):
    from app.db.models import Trip
    results = (
        db.query(Trip)
        .order_by(Trip.created_at.desc())
        .limit(limit)
        .all()
    )
    return results
