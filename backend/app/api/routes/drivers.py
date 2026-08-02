from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.api.deps import SessionDep, CurrentUser
from app.db.models import Driver, Vehicle, DriverAssignmentHistory
from app.schemas.driver import (
    DriverCreate, DriverUpdate, DriverResponse, DriverStats,
    FullVehicleCreate, FullVehicleUpdate, FullVehicleResponse, VehicleStats,
    AssignmentHistoryItem, VehicleLocationItem
)
from app.services.driver_service import driver_service
from app.services.notification_service import log_system_notification

router = APIRouter(tags=["Driver & Vehicle Management"])


# ─────────────────────────────────────────────────────────────
# Driver Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/api/drivers", response_model=List[DriverResponse])
def list_drivers(
    db: SessionDep,
    current_user: CurrentUser,
    search: Optional[str] = None,
    provider_id: Optional[int] = None,
    status: Optional[str] = None,
    availability: Optional[str] = None,
    limit: int = 100,
):
    """List drivers with filtering by Provider, Status, Availability, or Search string."""
    return driver_service.get_drivers(
        db,
        search=search,
        provider_id=provider_id,
        status=status,
        availability=availability,
        limit=limit,
    )


@router.get("/api/drivers/stats", response_model=DriverStats)
def get_driver_stats(db: SessionDep, current_user: CurrentUser):
    """Get aggregate driver metrics (Total, Available, Busy, Offline)."""
    return driver_service.get_driver_stats(db)


@router.post("/api/drivers", response_model=DriverResponse, status_code=201)
def create_driver(data: DriverCreate, db: SessionDep, current_user: CurrentUser):
    """Add a new Driver to the platform."""
    driver = Driver(**data.model_dump())
    db.add(driver)
    db.commit()
    db.refresh(driver)
    log_system_notification(
        db,
        title="Driver Added",
        description=f"New driver '{driver.name}' added to platform",
        category="Success",
        event_type="provider_mgmt",
    )
    return driver_service.get_drivers(db, search=str(driver.id), limit=1)[0]


@router.get("/api/drivers/{driver_id}", response_model=DriverResponse)
def get_driver(driver_id: int, db: SessionDep, current_user: CurrentUser):
    """Get single driver details."""
    drivers = driver_service.get_drivers(db, search=str(driver_id), limit=1)
    if not drivers:
        raise HTTPException(404, "Driver not found")
    return drivers[0]


@router.patch("/api/drivers/{driver_id}", response_model=DriverResponse)
def update_driver(driver_id: int, data: DriverUpdate, db: SessionDep, current_user: CurrentUser):
    """Edit driver status, assigned vehicle, contact, or location."""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(404, "Driver not found")

    old_vehicle = driver.assigned_vehicle_id
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(driver, k, v)

    db.commit()
    db.refresh(driver)

    # Log assignment history if assigned_vehicle changed
    if data.assigned_vehicle_id is not None and data.assigned_vehicle_id != old_vehicle:
        vehicle = db.query(Vehicle).filter(Vehicle.id == data.assigned_vehicle_id).first()
        v_name = vehicle.name if vehicle else f"Vehicle #{data.assigned_vehicle_id}"
        hist = DriverAssignmentHistory(
            driver_id=driver.id,
            vehicle_id=data.assigned_vehicle_id,
            driver_name=driver.name,
            vehicle_name=v_name,
            status="Active",
        )
        db.add(hist)
        db.commit()

    return driver_service.get_drivers(db, search=str(driver_id), limit=1)[0]


@router.delete("/api/drivers/{driver_id}")
def delete_driver(driver_id: int, db: SessionDep, current_user: CurrentUser):
    """Delete a driver."""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(404, "Driver not found")
    d_name = driver.name
    db.delete(driver)
    db.commit()
    log_system_notification(
        db,
        title="Driver Removed",
        description=f"Driver '{d_name}' removed from platform",
        category="Warning",
        event_type="provider_mgmt",
    )
    return {"message": "Driver deleted successfully"}


# ─────────────────────────────────────────────────────────────
# Vehicle Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/api/vehicles", response_model=List[FullVehicleResponse])
def list_vehicles(
    db: SessionDep,
    current_user: CurrentUser,
    search: Optional[str] = None,
    provider_id: Optional[int] = None,
    vehicle_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
):
    """List vehicles across all providers with filtering."""
    return driver_service.get_vehicles(
        db,
        search=search,
        provider_id=provider_id,
        vehicle_type=vehicle_type,
        status=status,
        limit=limit,
    )


@router.get("/api/vehicles/stats", response_model=VehicleStats)
def get_vehicle_stats(db: SessionDep, current_user: CurrentUser):
    """Get aggregate vehicle metrics (Total, Available, In Service, Maintenance)."""
    return driver_service.get_vehicle_stats(db)


@router.get("/api/vehicles/locations", response_model=List[VehicleLocationItem])
def get_vehicle_locations(db: SessionDep, current_user: CurrentUser):
    """Get current vehicle positions for Google Maps visualization."""
    return driver_service.get_vehicle_locations(db)


@router.post("/api/vehicles", response_model=FullVehicleResponse, status_code=201)
def create_vehicle(data: FullVehicleCreate, db: SessionDep, current_user: CurrentUser):
    """Add a new Vehicle."""
    vehicle = Vehicle(**data.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    log_system_notification(
        db,
        title="Vehicle Added",
        description=f"New vehicle '{vehicle.name}' registered",
        category="Success",
        event_type="provider_mgmt",
    )
    return driver_service.get_vehicles(db, search=str(vehicle.name), limit=1)[0]


@router.patch("/api/vehicles/{vehicle_id}", response_model=FullVehicleResponse)
def update_vehicle(vehicle_id: int, data: FullVehicleUpdate, db: SessionDep, current_user: CurrentUser):
    """Edit vehicle status, capacity, current driver, or location."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(vehicle, k, v)

    db.commit()
    db.refresh(vehicle)
    return driver_service.get_vehicles(db, search=str(vehicle.name), limit=1)[0]


@router.delete("/api/vehicles/{vehicle_id}")
def delete_vehicle(vehicle_id: int, db: SessionDep, current_user: CurrentUser):
    """Delete a vehicle."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    v_name = vehicle.name
    db.delete(vehicle)
    db.commit()
    log_system_notification(
        db,
        title="Vehicle Removed",
        description=f"Vehicle '{v_name}' removed from platform",
        category="Warning",
        event_type="provider_mgmt",
    )
    return {"message": "Vehicle deleted successfully"}


# ─────────────────────────────────────────────────────────────
# Assignment History Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/api/drivers/assignments/history", response_model=List[AssignmentHistoryItem])
def get_assignment_history(db: SessionDep, current_user: CurrentUser, limit: int = 100):
    """Get chronological driver-vehicle assignment history log."""
    return driver_service.get_assignment_history(db, limit=limit)
