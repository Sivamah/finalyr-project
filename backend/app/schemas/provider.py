from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class VehicleCreate(BaseModel):
    name: str
    vehicle_type: str
    capacity: int = 1
    fuel_type: str = "Petrol"
    mileage_kmpl: float = 15.0
    cost_per_km: float = 10.0
    is_active: bool = True

class VehicleResponse(BaseModel):
    id: int
    provider_id: int
    name: str
    vehicle_type: str
    capacity: int
    fuel_type: str
    mileage_kmpl: float
    cost_per_km: float
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProviderCreate(BaseModel):
    name: str
    provider_type: str
    category: str = "Ride"
    status: str = "Active"
    operating_area: str = "Coimbatore"
    api_status: str = "Simulated"
    simulation_mode: bool = True
    logo: Optional[str] = None
    description: Optional[str] = None
    pricing_model: Optional[str] = None
    service_constraints: Optional[str] = None

class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    operating_area: Optional[str] = None
    api_status: Optional[str] = None
    simulation_mode: Optional[bool] = None
    logo: Optional[str] = None
    description: Optional[str] = None
    pricing_model: Optional[str] = None
    service_constraints: Optional[str] = None

class ProviderResponse(BaseModel):
    id: int
    name: str
    provider_type: str
    category: str = "Ride"
    status: str
    operating_area: str
    api_status: str
    simulation_mode: bool
    logo: Optional[str] = None
    description: Optional[str] = None
    pricing_model: Optional[str] = None
    service_constraints: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    vehicles: List[VehicleResponse] = []

    class Config:
        from_attributes = True
