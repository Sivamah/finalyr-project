from typing import List
import json
from fastapi import APIRouter, HTTPException
from app.db.models import Provider, Vehicle
from app.schemas.provider import ProviderCreate, ProviderUpdate, ProviderResponse, VehicleCreate, VehicleResponse
from app.api.deps import SessionDep, CurrentUser
from app.services.notification_service import log_system_notification

router = APIRouter()


@router.get("/", response_model=List[ProviderResponse])
def list_providers(db: SessionDep, current_user: CurrentUser):
    return db.query(Provider).order_by(Provider.created_at.desc()).all()


@router.post("/", response_model=ProviderResponse, status_code=201)
def create_provider(data: ProviderCreate, db: SessionDep, current_user: CurrentUser):
    provider = Provider(**data.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    log_system_notification(
        db,
        title="Provider Added",
        description=f"New provider '{provider.name}' ({provider.provider_type}) registered",
        category="Success",
        event_type="provider_mgmt",
        provider_name=provider.name,
    )
    return provider


@router.get("/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: int, db: SessionDep, current_user: CurrentUser):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    return provider


@router.patch("/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: int, data: ProviderUpdate, db: SessionDep, current_user: CurrentUser):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(provider, k, v)
    db.commit()
    db.refresh(provider)
    return provider


@router.delete("/{provider_id}")
def delete_provider(provider_id: int, db: SessionDep, current_user: CurrentUser):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    p_name = provider.name
    db.delete(provider)
    db.commit()
    log_system_notification(
        db,
        title="Provider Removed",
        description=f"Provider '{p_name}' removed from platform",
        category="Warning",
        event_type="provider_mgmt",
        provider_name=p_name,
    )
    return {"message": "Provider deleted successfully"}


@router.post("/{provider_id}/vehicles", response_model=VehicleResponse, status_code=201)
def create_vehicle(provider_id: int, data: VehicleCreate, db: SessionDep, current_user: CurrentUser):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    vehicle = Vehicle(provider_id=provider_id, **data.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/{provider_id}/vehicles", response_model=List[VehicleResponse])
def list_vehicles(provider_id: int, db: SessionDep, current_user: CurrentUser):
    return db.query(Vehicle).filter(Vehicle.provider_id == provider_id).all()


@router.delete("/vehicles/{vehicle_id}")
def delete_vehicle(vehicle_id: int, db: SessionDep, current_user: CurrentUser):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    db.delete(vehicle)
    db.commit()
    return {"message": "Vehicle deleted"}


# ─────────────────────────────────────────────
# Seed Default Providers
# ─────────────────────────────────────────────

SEED_PROVIDERS = [
    {
        "name": "Rapido",
        "provider_type": "Ride",
        "category": "Ride",
        "description": "Bike taxi and auto-rickshaw ride-hailing service",
        "pricing_model": json.dumps({"base_fare": 25, "per_km": 8, "per_min": 1}),
        "service_constraints": json.dumps({"max_detour_pct": 5, "max_passengers": 2}),
        "vehicles": [
            {"name": "Rapido Bike", "vehicle_type": "Bike", "capacity": 1, "fuel_type": "Petrol", "mileage_kmpl": 40.0, "cost_per_km": 8.0},
            {"name": "Rapido Auto", "vehicle_type": "Auto", "capacity": 3, "fuel_type": "CNG", "mileage_kmpl": 25.0, "cost_per_km": 12.0},
        ],
    },
    {
        "name": "Uber",
        "provider_type": "Ride",
        "category": "Ride",
        "description": "Premium ride-hailing with cars and autos",
        "pricing_model": json.dumps({"base_fare": 40, "per_km": 14, "per_min": 2, "surge_multiplier": 1.0}),
        "service_constraints": json.dumps({"max_detour_pct": 5, "max_passengers": 4}),
        "vehicles": [
            {"name": "UberGo", "vehicle_type": "Car", "capacity": 4, "fuel_type": "Petrol", "mileage_kmpl": 15.0, "cost_per_km": 14.0},
            {"name": "Uber Auto", "vehicle_type": "Auto", "capacity": 3, "fuel_type": "CNG", "mileage_kmpl": 25.0, "cost_per_km": 11.0},
        ],
    },
    {
        "name": "Ola",
        "provider_type": "Ride",
        "category": "Ride",
        "description": "Multi-modal ride-hailing with bikes, autos, and cabs",
        "pricing_model": json.dumps({"base_fare": 35, "per_km": 12, "per_min": 1.5}),
        "service_constraints": json.dumps({"max_detour_pct": 5, "max_passengers": 4}),
        "vehicles": [
            {"name": "Ola Mini", "vehicle_type": "Car", "capacity": 4, "fuel_type": "Petrol", "mileage_kmpl": 16.0, "cost_per_km": 12.0},
            {"name": "Ola Bike", "vehicle_type": "Bike", "capacity": 1, "fuel_type": "Petrol", "mileage_kmpl": 45.0, "cost_per_km": 7.0},
        ],
    },
    {
        "name": "Swiggy",
        "provider_type": "Food",
        "category": "Food",
        "description": "Food delivery platform with restaurant partners",
        "pricing_model": json.dumps({"delivery_fee": 30, "per_km": 5, "packaging_fee": 10}),
        "service_constraints": json.dumps({"max_delivery_time_min": 45, "max_food_transit_min": 15}),
        "vehicles": [
            {"name": "Swiggy Bike", "vehicle_type": "Bike", "capacity": 2, "fuel_type": "Petrol", "mileage_kmpl": 40.0, "cost_per_km": 5.0},
        ],
    },
    {
        "name": "Zomato",
        "provider_type": "Food",
        "category": "Food",
        "description": "Food delivery and restaurant discovery platform",
        "pricing_model": json.dumps({"delivery_fee": 25, "per_km": 6, "platform_fee": 5}),
        "service_constraints": json.dumps({"max_delivery_time_min": 40, "max_food_transit_min": 15}),
        "vehicles": [
            {"name": "Zomato Bike", "vehicle_type": "Bike", "capacity": 2, "fuel_type": "Petrol", "mileage_kmpl": 40.0, "cost_per_km": 6.0},
        ],
    },
    {
        "name": "Porter",
        "provider_type": "Parcel",
        "category": "Parcel",
        "description": "Intra-city logistics and parcel delivery",
        "pricing_model": json.dumps({"base_fare": 150, "per_km": 15, "loading_charge": 50}),
        "service_constraints": json.dumps({"max_weight_kg": 500, "max_dimensions_cm": "200x150x150"}),
        "vehicles": [
            {"name": "Porter Mini Truck", "vehicle_type": "Van", "capacity": 8, "fuel_type": "Diesel", "mileage_kmpl": 12.0, "cost_per_km": 15.0},
            {"name": "Porter Truck", "vehicle_type": "Truck", "capacity": 15, "fuel_type": "Diesel", "mileage_kmpl": 8.0, "cost_per_km": 20.0},
        ],
    },
    {
        "name": "DTDC",
        "provider_type": "Parcel",
        "category": "Parcel",
        "description": "Express parcel and courier delivery service",
        "pricing_model": json.dumps({"base_fare": 50, "per_kg": 20, "per_km": 8}),
        "service_constraints": json.dumps({"max_weight_kg": 50, "max_dimensions_cm": "100x80x80"}),
        "vehicles": [
            {"name": "DTDC Van", "vehicle_type": "Van", "capacity": 10, "fuel_type": "Diesel", "mileage_kmpl": 14.0, "cost_per_km": 10.0},
        ],
    },
    {
        "name": "Blue Dart",
        "provider_type": "Parcel",
        "category": "Parcel",
        "description": "Premium express logistics and parcel delivery",
        "pricing_model": json.dumps({"base_fare": 80, "per_kg": 30, "per_km": 10}),
        "service_constraints": json.dumps({"max_weight_kg": 30, "max_dimensions_cm": "80x60x60"}),
        "vehicles": [
            {"name": "Blue Dart Bike", "vehicle_type": "Bike", "capacity": 2, "fuel_type": "Petrol", "mileage_kmpl": 35.0, "cost_per_km": 8.0},
            {"name": "Blue Dart Van", "vehicle_type": "Van", "capacity": 12, "fuel_type": "Diesel", "mileage_kmpl": 13.0, "cost_per_km": 12.0},
        ],
    },
]


@router.post("/seed")
def seed_providers(db: SessionDep, current_user: CurrentUser):
    """Auto-create default simulated providers with vehicles."""
    existing = db.query(Provider).count()
    if existing > 0:
        return {"message": f"Providers already exist ({existing}). Delete them first to re-seed.", "created": 0}

    created = 0
    for seed in SEED_PROVIDERS:
        vehicles_data = seed.get("vehicles", [])
        provider_data = {k: v for k, v in seed.items() if k != "vehicles"}
        provider = Provider(
            **provider_data,
            operating_area="Coimbatore",
            api_status="Simulated",
            simulation_mode=True,
        )
        db.add(provider)
        db.flush()

        for vdata in vehicles_data:
            vehicle = Vehicle(provider_id=provider.id, **vdata)
            db.add(vehicle)

        created += 1

    db.commit()
    return {"message": f"Seeded {created} providers with vehicles", "created": created}

