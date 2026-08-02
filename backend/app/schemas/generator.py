from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class GenerateRequest(BaseModel):
    area: str = "Coimbatore"
    count: int = Field(default=25, ge=1, le=1000)
    distribution: Dict[str, float] = Field(
        default={"ride": 40, "food": 40, "parcel": 20},
        description="Percentage distribution for ride/food/parcel"
    )
    provider_ids: Optional[List[int]] = None


class SimulationRequestResponse(BaseModel):
    id: int
    provider_id: Optional[int] = None
    request_type: str
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    pickup_address: str = ""
    drop_address: str = ""
    demand: int = 1
    priority: str = "Medium"
    weight_kg: float = 0.0
    vehicle_type: str = "Auto"
    estimated_distance_km: float = 0.0
    request_timestamp: Optional[datetime] = None
    status: str = "Pending"
    created_at: Optional[datetime] = None

    # Joined fields from provider
    provider_name: Optional[str] = None

    class Config:
        from_attributes = True


class GenerateResponse(BaseModel):
    message: str
    count: int
    requests: List[SimulationRequestResponse] = []
