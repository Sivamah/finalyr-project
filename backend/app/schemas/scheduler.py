from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TripBase(BaseModel):
    batch_id: int
    trip_type: str = "Single"
    priority: str = "Medium"
    status: str = "Pending"

class TripCreate(TripBase):
    pass

class TripResponse(TripBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DriverLocationBase(BaseModel):
    lat: float
    lng: float

class DriverLocationUpdate(DriverLocationBase):
    pass

class DriverLocationResponse(DriverLocationBase):
    id: int
    driver_id: int
    last_updated: datetime

    class Config:
        from_attributes = True

class DriverAssignmentBase(BaseModel):
    trip_id: int
    driver_id: int
    status: str = "Pending"
    score: float = 0.0

class DriverAssignmentResponse(DriverAssignmentBase):
    id: int
    assigned_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AssignmentHistoryBase(BaseModel):
    trip_id: int
    driver_id: int
    status: str
    reason: Optional[str] = None

class AssignmentHistoryResponse(AssignmentHistoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
