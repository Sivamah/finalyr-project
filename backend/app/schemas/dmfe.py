from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RouteStop(BaseModel):
    action: str  # "pickup" or "drop"
    booking_type: str  # "ride", "food", "parcel"
    booking_id: int
    lat: float
    lng: float
    address: str

class BatchedTripBase(BaseModel):
    driver_id: Optional[int] = None
    status: str = "Pending"
    total_estimated_fare: float = 0.0
    total_distance_km: float = 0.0
    optimized_route_json: str  # stringified JSON of the stops

class BatchedTripResponse(BatchedTripBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DMFEEvaluateResponse(BaseModel):
    message: str
    batches_created: int

from app.db.models import BookingStatus
class BatchStatusUpdate(BaseModel):
    status: BookingStatus


class AIDecisionResponse(BaseModel):
    id: int
    batch_id: int
    decision_type: str
    feasibility_score: float
    route_similarity: float
    estimated_delay_min: float
    fuel_saved_pct: float
    co2_reduction_pct: float
    driver_available: bool
    capacity_sufficient: bool
    request_count: int
    explanation_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


