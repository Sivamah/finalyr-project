from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class OptimizedStopBase(BaseModel):
    stop_sequence: int
    lat: float
    lng: float
    address: Optional[str] = None
    action: Optional[str] = None
    eta_mins: float = 0.0

class OptimizedStopResponse(OptimizedStopBase):
    id: int
    route_id: int

    class Config:
        from_attributes = True

class RouteDetailBase(BaseModel):
    trip_id: int
    total_distance_km: float = 0.0
    total_duration_mins: float = 0.0
    estimated_fuel_liters: float = 0.0
    polyline: Optional[str] = None

class RouteDetailResponse(RouteDetailBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    stops: List[OptimizedStopResponse] = []

    class Config:
        from_attributes = True
