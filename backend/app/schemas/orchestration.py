from typing import Optional, List, Any
from pydantic import BaseModel
from datetime import datetime


class OptimizationTrigger(BaseModel):
    provider_ids: Optional[List[int]] = None
    request_count: int = 10


class OptimizationResultResponse(BaseModel):
    id: int
    batch_id: Optional[str] = None
    request_count: int
    provider_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    best_route_json: Optional[Any] = None
    chosen_provider: Optional[str] = None
    chosen_vehicle: Optional[str] = None
    estimated_cost: float
    eta_mins: float
    fuel_saved_l: float
    distance_saved_km: float
    co2_saved_kg: float
    optimization_score: float
    explanation_json: Optional[Any] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_providers: int
    total_vehicles: int
    total_requests: int
    total_optimizations: int
    avg_route_savings: float
    fuel_saved: float
    co2_reduction: float
    batch_rate: float = 0.0


class DatasetUpload(BaseModel):
    name: str
    file_type: str
    data_type: str
    description: Optional[str] = None


class DatasetResponse(BaseModel):
    id: int
    name: str
    file_type: str
    data_type: str
    file_path: Optional[str] = None
    row_count: int
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
