from fastapi import APIRouter
from sqlalchemy import func
from app.db.models import Provider, Vehicle, SimulationRequest, OptimizationResult
from app.api.deps import SessionDep, CurrentUser
from app.schemas.orchestration import DashboardStats, DatasetResponse
from app.db.models import Dataset

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: SessionDep, current_user: CurrentUser):
    total_providers = db.query(func.count(Provider.id)).scalar()
    total_vehicles = db.query(func.count(Vehicle.id)).scalar()
    total_requests = db.query(func.count(SimulationRequest.id)).scalar()
    total_optimizations = db.query(func.count(OptimizationResult.id)).scalar()

    results = db.query(OptimizationResult).all()
    if results:
        avg_savings = sum(r.distance_saved_km for r in results) / len(results)
        total_fuel = sum(r.fuel_saved_l for r in results)
        total_co2 = sum(r.co2_saved_kg for r in results)
    else:
        avg_savings = 0.0
        total_fuel = 0.0
        total_co2 = 0.0

    return {
        "total_providers": total_providers,
        "total_vehicles": total_vehicles,
        "total_requests": total_requests,
        "total_optimizations": total_optimizations,
        "avg_route_savings": round(avg_savings, 2),
        "fuel_saved": round(total_fuel, 2),
        "co2_reduction": round(total_co2, 2),
    }


@router.get("/providers/breakdown")
def get_provider_breakdown(db: SessionDep, current_user: CurrentUser):
    types = db.query(Provider.provider_type, func.count(Provider.id)).group_by(Provider.provider_type).all()
    return [{"type": t, "count": c} for t, c in types]


@router.get("/results/recent")
def get_recent_results(db: SessionDep, current_user: CurrentUser, limit: int = 10):
    results = (
        db.query(OptimizationResult)
        .order_by(OptimizationResult.created_at.desc())
        .limit(limit)
        .all()
    )
    return results
