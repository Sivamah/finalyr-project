from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user
from app.db import models
from app.schemas import routing as routing_schemas
from app.services import routing_service

router = APIRouter()

@router.post("/optimize/{trip_id}", response_model=routing_schemas.RouteDetailResponse)
def optimize_route(trip_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Generate or regenerate optimized route details for a trip.
    """
    route_detail = routing_service.generate_optimized_route(db, trip_id)
    return route_detail

@router.get("/{trip_id}", response_model=routing_schemas.RouteDetailResponse)
def get_optimized_route(trip_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Get the pre-calculated route details and sequence of stops for a trip.
    """
    route_detail = routing_service.get_route_details(db, trip_id)
    return route_detail
