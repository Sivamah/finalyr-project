from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.models import Provider, Driver, Vehicle, Trip, DriverAssignment, DriverAssignmentHistory, SimulationRequest, OptimizationResult

def _safe_delete_vehicle(vehicle: Vehicle, db: Session):
    """
    Deletes a vehicle safely. Checks for active workflows and nullifies
    safe operational history before deletion.
    Assumes running within a transaction (caller must db.commit()).
    """
    # 1. Check for active/planned trips
    active_trips = db.query(Trip).filter(
        Trip.vehicle_id == vehicle.id,
        Trip.status.in_(["Planned", "Active"])
    ).first()
    if active_trips:
        raise HTTPException(409, f"Vehicle '{vehicle.name}' cannot be deleted because it is assigned to an active/planned trip.")

    # 2. Check for active assignments
    active_assignment = db.query(DriverAssignment).filter(
        DriverAssignment.vehicle_id == vehicle.id,
        DriverAssignment.status == "Active"
    ).first()
    if active_assignment:
        raise HTTPException(409, f"Vehicle '{vehicle.name}' cannot be deleted because it has an active driver assignment.")

    # 3. Safe to delete. Nullify dependencies to preserve history without dangling references
    db.query(Driver).filter(Driver.assigned_vehicle_id == vehicle.id).update({"assigned_vehicle_id": None})
    db.query(Trip).filter(Trip.vehicle_id == vehicle.id).update({"vehicle_id": None})
    db.query(DriverAssignment).filter(DriverAssignment.vehicle_id == vehicle.id).update({"vehicle_id": None})
    db.query(DriverAssignmentHistory).filter(DriverAssignmentHistory.vehicle_id == vehicle.id).update({"vehicle_id": None})
    db.query(OptimizationResult).filter(OptimizationResult.vehicle_id == vehicle.id).update({"vehicle_id": None})
    
    db.delete(vehicle)


def _safe_delete_driver(driver: Driver, db: Session):
    """
    Deletes a driver safely.
    """
    # 1. Check active/planned trips
    active_trips = db.query(Trip).filter(
        Trip.driver_id == driver.id,
        Trip.status.in_(["Planned", "Active"])
    ).first()
    if active_trips:
        raise HTTPException(409, f"Driver '{driver.name}' cannot be deleted because they are assigned to an active/planned trip.")
        
    # 2. Check active assignments
    active_assignment = db.query(DriverAssignment).filter(
        DriverAssignment.driver_id == driver.id,
        DriverAssignment.status == "Active"
    ).first()
    if active_assignment:
        raise HTTPException(409, f"Driver '{driver.name}' cannot be deleted because they have an active vehicle assignment.")

    # 3. Safe cleanup
    db.query(Vehicle).filter(Vehicle.current_driver_id == driver.id).update({"current_driver_id": None})
    db.query(Trip).filter(Trip.driver_id == driver.id).update({"driver_id": None})
    db.query(DriverAssignment).filter(DriverAssignment.driver_id == driver.id).update({"driver_id": None})
    db.query(DriverAssignmentHistory).filter(DriverAssignmentHistory.driver_id == driver.id).update({"driver_id": None})
    
    db.delete(driver)


def safe_delete_provider(provider_id: int, db: Session) -> str:
    """
    Safely deletes a provider and its dependents (vehicles, drivers).
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
        
    # Check SimulationRequests
    active_sims = db.query(SimulationRequest).filter(
        SimulationRequest.provider_id == provider.id,
        SimulationRequest.status.in_(["Pending", "Assigned", "Active"])
    ).first()
    if active_sims:
        raise HTTPException(409, f"Provider '{provider.name}' cannot be deleted because it has active simulation requests.")
        
    p_name = provider.name

    try:
        # Check and delete all drivers safely
        drivers = db.query(Driver).filter(Driver.provider_id == provider.id).all()
        for driver in drivers:
            _safe_delete_driver(driver, db)
            
        # Check and delete all vehicles safely
        vehicles = db.query(Vehicle).filter(Vehicle.provider_id == provider.id).all()
        for vehicle in vehicles:
            _safe_delete_vehicle(vehicle, db)
            
        # Nullify dependencies
        db.query(SimulationRequest).filter(SimulationRequest.provider_id == provider.id).update({"provider_id": None})
        db.query(OptimizationResult).filter(OptimizationResult.provider_id == provider.id).update({"provider_id": None})
        
        db.delete(provider)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
        
    return p_name


def safe_delete_driver(driver_id: int, db: Session) -> str:
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(404, "Driver not found")
    
    d_name = driver.name
    try:
        _safe_delete_driver(driver, db)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
        
    return d_name


def safe_delete_vehicle(vehicle_id: int, db: Session) -> str:
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
        
    v_name = vehicle.name
    try:
        _safe_delete_vehicle(vehicle, db)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
        
    return v_name
