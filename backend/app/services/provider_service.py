from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models import Provider, Vehicle
from app.schemas.provider import ProviderCreate, ProviderUpdate, VehicleCreate


def create_provider(db: Session, data: ProviderCreate) -> Provider:
    provider = Provider(**data.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def update_provider(db: Session, provider_id: int, data: ProviderUpdate) -> Optional[Provider]:
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return None
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(provider, k, v)
    db.commit()
    db.refresh(provider)
    return provider


def delete_provider(db: Session, provider_id: int) -> bool:
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return False
    db.delete(provider)
    db.commit()
    return True


def add_vehicle(db: Session, provider_id: int, data: VehicleCreate) -> Optional[Vehicle]:
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return None
    vehicle = Vehicle(provider_id=provider_id, **data.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle
