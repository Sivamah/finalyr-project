from typing import List
from fastapi import APIRouter, HTTPException
from app.api.deps import SessionDep, CurrentUser
from app.db.models import SimulationRequest, Provider
from app.schemas.generator import GenerateRequest, GenerateResponse, SimulationRequestResponse
from app.services.mock_adapters import generate_simulation_requests

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
def generate_requests(data: GenerateRequest, db: SessionDep, current_user: CurrentUser):
    """Generate random simulation requests for Coimbatore."""
    # Convert percentage distribution to fractions
    distribution = {}
    total = sum(data.distribution.values())
    if total > 0:
        for k, v in data.distribution.items():
            distribution[k] = v / total

    requests = generate_simulation_requests(
        count=data.count,
        db=db,
        request_types=distribution,
        provider_ids=data.provider_ids,
    )

    if not requests:
        raise HTTPException(400, "No active providers found. Seed or create providers first.")

    # Build response with provider names
    response_items = []
    for req in requests:
        provider = db.query(Provider).filter(Provider.id == req.provider_id).first()
        item = SimulationRequestResponse(
            id=req.id,
            provider_id=req.provider_id,
            request_type=req.request_type,
            pickup_lat=req.pickup_lat,
            pickup_lng=req.pickup_lng,
            drop_lat=req.drop_lat,
            drop_lng=req.drop_lng,
            pickup_address=req.pickup_address,
            drop_address=req.drop_address,
            demand=req.demand,
            priority=req.priority,
            weight_kg=req.weight_kg,
            vehicle_type=req.vehicle_type,
            estimated_distance_km=req.estimated_distance_km,
            request_timestamp=req.request_timestamp,
            status=req.status,
            created_at=req.created_at,
            provider_name=provider.name if provider else "Unknown",
        )
        response_items.append(item)

    return GenerateResponse(
        message=f"Generated {len(requests)} requests",
        count=len(requests),
        requests=response_items,
    )


@router.get("/requests", response_model=List[SimulationRequestResponse])
def list_simulation_requests(
    db: SessionDep,
    current_user: CurrentUser,
    limit: int = 200,
    status: str = "",
    request_type: str = "",
):
    """List simulation requests with optional filters."""
    query = db.query(SimulationRequest)
    if status:
        query = query.filter(SimulationRequest.status == status)
    if request_type:
        query = query.filter(SimulationRequest.request_type == request_type)

    reqs = query.order_by(SimulationRequest.created_at.desc()).limit(limit).all()

    results = []
    for req in reqs:
        provider = db.query(Provider).filter(Provider.id == req.provider_id).first()
        results.append(SimulationRequestResponse(
            id=req.id,
            provider_id=req.provider_id,
            request_type=req.request_type,
            pickup_lat=req.pickup_lat,
            pickup_lng=req.pickup_lng,
            drop_lat=req.drop_lat,
            drop_lng=req.drop_lng,
            pickup_address=req.pickup_address,
            drop_address=req.drop_address,
            demand=req.demand,
            priority=req.priority,
            weight_kg=req.weight_kg,
            vehicle_type=req.vehicle_type,
            estimated_distance_km=req.estimated_distance_km,
            request_timestamp=req.request_timestamp,
            status=req.status,
            created_at=req.created_at,
            provider_name=provider.name if provider else "Unknown",
        ))
    return results


@router.get("/requests/{request_id}", response_model=SimulationRequestResponse)
def get_request_detail(request_id: int, db: SessionDep, current_user: CurrentUser):
    """Get full details for a single request."""
    req = db.query(SimulationRequest).filter(SimulationRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "Request not found")
    provider = db.query(Provider).filter(Provider.id == req.provider_id).first()
    return SimulationRequestResponse(
        id=req.id,
        provider_id=req.provider_id,
        request_type=req.request_type,
        pickup_lat=req.pickup_lat,
        pickup_lng=req.pickup_lng,
        drop_lat=req.drop_lat,
        drop_lng=req.drop_lng,
        pickup_address=req.pickup_address,
        drop_address=req.drop_address,
        demand=req.demand,
        priority=req.priority,
        weight_kg=req.weight_kg,
        vehicle_type=req.vehicle_type,
        estimated_distance_km=req.estimated_distance_km,
        request_timestamp=req.request_timestamp,
        status=req.status,
        created_at=req.created_at,
        provider_name=provider.name if provider else "Unknown",
    )


@router.delete("/requests/clear")
def clear_requests(db: SessionDep, current_user: CurrentUser):
    """Delete all simulation requests."""
    count = db.query(SimulationRequest).delete()
    db.commit()
    return {"message": f"Deleted {count} requests", "deleted": count}
