from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.db.models import VehicleType


class DriverProfileCreate(BaseModel):
    vehicle_type   : VehicleType = VehicleType.Bike
    vehicle_number : str
    vehicle_model  : Optional[str] = None


class DriverProfileUpdate(BaseModel):
    vehicle_type   : Optional[VehicleType] = None
    vehicle_number : Optional[str]         = None
    vehicle_model  : Optional[str]         = None
    is_available   : Optional[bool]        = None


class DriverProfileResponse(BaseModel):
    id             : int
    user_id        : int
    vehicle_type   : VehicleType
    vehicle_number : str
    vehicle_model  : Optional[str] = None
    is_available   : bool
    rating         : float
    total_trips    : int
    created_at     : Optional[datetime] = None
    updated_at     : Optional[datetime] = None

    class Config:
        from_attributes = True
