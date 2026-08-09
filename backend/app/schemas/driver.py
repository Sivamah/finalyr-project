from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class DriverCreate(BaseModel):
    name: str
    phone: Optional[str] = "+91 98765 43210"
    email: Optional[str] = None
    provider_id: Optional[int] = None
    status: Optional[str] = "Available"
    license_number: Optional[str] = "TN37 2024001001"
    current_lat: Optional[float] = 11.0168
    current_lng: Optional[float] = 76.9558
    assigned_vehicle_id: Optional[int] = None


class DriverUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    provider_id: Optional[int] = None
    status: Optional[str] = None
    license_number: Optional[str] = None
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    assigned_vehicle_id: Optional[int] = None


class DriverResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    provider_id: Optional[int] = None
    provider_name: Optional[str] = "Unassigned"
    status: str = "Available"
    license_number: Optional[str] = None
    current_lat: Optional[float] = 11.0168
    current_lng: Optional[float] = 76.9558
    assigned_vehicle_id: Optional[int] = None
    assigned_vehicle_name: Optional[str] = "None"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FullVehicleCreate(BaseModel):
    name: str
    vehicle_type: str            # Bike / Auto / Car / Van / Truck
    registration_number: Optional[str] = "TN-37-AB-1001"
    capacity: int = 1
    fuel_type: str = "Petrol"     # Petrol / EV / CNG / Diesel
    provider_id: int
    status: Optional[str] = "Available"  # Available / Busy / Offline / Maintenance
    cost_per_km: Optional[float] = 10.0
    mileage_kmpl: Optional[float] = 15.0
    current_lat: Optional[float] = 11.0168
    current_lng: Optional[float] = 76.9558
    current_driver_id: Optional[int] = None


class FullVehicleUpdate(BaseModel):
    name: Optional[str] = None
    vehicle_type: Optional[str] = None
    registration_number: Optional[str] = None
    capacity: Optional[int] = None
    fuel_type: Optional[str] = None
    provider_id: Optional[int] = None
    status: Optional[str] = None
    cost_per_km: Optional[float] = None
    mileage_kmpl: Optional[float] = None
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    current_driver_id: Optional[int] = None


class FullVehicleResponse(BaseModel):
    id: int
    name: str
    vehicle_type: str
    registration_number: Optional[str] = "TN-37-AB-1001"
    capacity: int = 1
    fuel_type: str = "Petrol"
    provider_id: int
    provider_name: Optional[str] = "Unassigned"
    status: str = "Available"
    cost_per_km: float = 10.0
    mileage_kmpl: float = 15.0
    current_lat: Optional[float] = 11.0168
    current_lng: Optional[float] = 76.9558
    current_driver_id: Optional[int] = None
    current_driver_name: Optional[str] = "Unassigned"
    is_active: bool = True

    class Config:
        from_attributes = True


class DriverStats(BaseModel):
    total_drivers: int = 0
    available_drivers: int = 0
    busy_drivers: int = 0
    offline_drivers: int = 0


class VehicleStats(BaseModel):
    total_vehicles: int = 0
    available_vehicles: int = 0
    vehicles_in_service: int = 0
    maintenance_vehicles: int = 0


class AssignmentHistoryItem(BaseModel):
    id: int
    driver_id: int
    driver_name: str
    vehicle_id: int
    vehicle_name: str
    assignment_time: str
    completion_time: Optional[str] = None
    status: str = "Active"

    class Config:
        from_attributes = True


class VehicleLocationItem(BaseModel):
    vehicle_id: int
    vehicle_name: str
    vehicle_type: str
    registration_number: str
    provider_name: str
    driver_name: str
    status: str
    lat: float
    lng: float
