import random
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import func, String
from sqlalchemy.orm import Session

from app.db.models import Driver, Vehicle, Provider, DriverAssignmentHistory
from app.services.notification_service import log_system_notification

logger = logging.getLogger(__name__)

SAMPLE_COORDINATES = [
    (11.0168, 76.9558), # Gandhipuram
    (10.9980, 76.9660), # Ukkadam
    (11.0280, 76.9400), # R.S. Puram
    (11.0400, 76.9900), # Peelamedu
    (11.0800, 76.9950), # Saravanampatti
    (11.0000, 77.0300), # Singanallur
]

SEED_DRIVERS_DATA = [
  {"name": "Karthik Subramanian", "phone": "+91 98421 11201", "email": "karthik.s@rapido.in", "status": "Available", "license": "TN37 2021004120"},
  {"name": "Manoj Kumar", "phone": "+91 97890 22312", "email": "manoj.k@uber.com", "status": "Busy", "license": "TN38 2020003150"},
  {"name": "Senthil Nathan", "phone": "+91 94432 33423", "email": "senthil.n@swiggy.in", "status": "Available", "license": "TN37 2022005890"},
  {"name": "Praveen Raj", "phone": "+91 96291 44534", "email": "praveen.r@dtdc.com", "status": "Offline", "license": "TN66 2019001240"},
  {"name": "Gokul Prasad", "phone": "+91 98940 55645", "email": "gokul.p@zomato.com", "status": "Available", "license": "TN37 2023008910"},
  {"name": "Anand Prakash", "phone": "+91 97500 66756", "email": "anand.p@ola.in", "status": "Busy", "license": "TN38 2021009020"},
]


class DriverService:
    """Service layer managing Drivers, Vehicles, Location tracking, and Assignment logs."""

    def seed_initial_data_if_needed(self, db: Session):
        """Ensure initial realistic drivers and vehicles exist for demo providers."""
        try:
            providers = db.query(Provider).all()
            if not providers:
                return

            driver_count = db.query(Driver).count()
            if driver_count == 0:
                coords = SAMPLE_COORDINATES
                for i, d in enumerate(SEED_DRIVERS_DATA):
                    p = providers[i % len(providers)]
                    lat, lng = coords[i % len(coords)]
                    driver = Driver(
                        provider_id=p.id,
                        name=d["name"],
                        phone=d["phone"],
                        email=d["email"],
                        status=d["status"],
                        license_number=d["license"],
                        current_lat=lat,
                        current_lng=lng,
                    )
                    db.add(driver)
                db.commit()

            # Ensure vehicles have registration numbers & statuses
            vehicles = db.query(Vehicle).all()
            for i, v in enumerate(vehicles):
                if not v.registration_number or v.registration_number == "TN-37-AB-1001":
                    v.registration_number = f"TN-37-X-{1000 + v.id}"
                if not v.status:
                    v.status = "Available" if i % 2 == 0 else "Busy"
                if not v.current_lat or v.current_lat == 11.0168:
                    coords = SAMPLE_COORDINATES
                    v.current_lat, v.current_lng = coords[i % len(coords)]
            db.commit()
        except Exception as exc:
            logger.warning("seed_initial_data_if_needed error: %s", exc)

    def get_drivers(
        self,
        db: Session,
        search: Optional[str] = None,
        provider_id: Optional[int] = None,
        status: Optional[str] = None,
        availability: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        self.seed_initial_data_if_needed(db)
        query = db.query(Driver)

        if provider_id and provider_id != 0:
            query = query.filter(Driver.provider_id == provider_id)
        if status and status.lower() != "all":
            query = query.filter(func.lower(Driver.status) == status.lower())
        if availability and availability.lower() != "all":
            query = query.filter(func.lower(Driver.status) == availability.lower())

        if search:
            s_lower = search.lower()
            query = query.filter(
                (func.lower(Driver.name).contains(s_lower)) |
                (func.lower(Driver.phone).contains(s_lower)) |
                (func.lower(Driver.email).contains(s_lower)) |
                (func.lower(Driver.license_number).contains(s_lower)) |
                (func.cast(Driver.id, String).contains(s_lower))
            )

        drivers = query.order_by(Driver.created_at.desc()).limit(limit).all()

        # Build output objects with provider & vehicle names
        providers = {p.id: p.name for p in db.query(Provider).all()}
        vehicles = {v.id: v.name for v in db.query(Vehicle).all()}

        result = []
        for d in drivers:
            result.append({
                "id": d.id,
                "name": d.name,
                "phone": d.phone or "",
                "email": d.email or "",
                "provider_id": d.provider_id,
                "provider_name": providers.get(d.provider_id, "Unassigned"),
                "status": d.status or "Available",
                "license_number": d.license_number or "",
                "current_lat": d.current_lat or 11.0168,
                "current_lng": d.current_lng or 76.9558,
                "assigned_vehicle_id": d.assigned_vehicle_id,
                "assigned_vehicle_name": vehicles.get(d.assigned_vehicle_id, "None"),
                "created_at": d.created_at,
            })
        return result

    def get_driver_stats(self, db: Session) -> Dict[str, int]:
        self.seed_initial_data_if_needed(db)
        total = db.query(Driver).count()
        available = db.query(Driver).filter(func.lower(Driver.status) == "available").count()
        busy = db.query(Driver).filter(func.lower(Driver.status) == "busy").count()
        offline = db.query(Driver).filter(func.lower(Driver.status) == "offline").count()

        return {
            "total_drivers": total,
            "available_drivers": available,
            "busy_drivers": busy,
            "offline_drivers": offline,
        }

    def get_vehicles(
        self,
        db: Session,
        search: Optional[str] = None,
        provider_id: Optional[int] = None,
        vehicle_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        self.seed_initial_data_if_needed(db)
        query = db.query(Vehicle)

        if provider_id and provider_id != 0:
            query = query.filter(Vehicle.provider_id == provider_id)
        if vehicle_type and vehicle_type.lower() != "all":
            query = query.filter(func.lower(Vehicle.vehicle_type) == vehicle_type.lower())
        if status and status.lower() != "all":
            query = query.filter(func.lower(Vehicle.status) == status.lower())

        if search:
            s_lower = search.lower()
            query = query.filter(
                (func.lower(Vehicle.name).contains(s_lower)) |
                (func.lower(Vehicle.registration_number).contains(s_lower)) |
                (func.lower(Vehicle.vehicle_type).contains(s_lower)) |
                (func.lower(Vehicle.fuel_type).contains(s_lower))
            )

        vehicles = query.order_by(Vehicle.created_at.desc()).limit(limit).all()

        providers = {p.id: p.name for p in db.query(Provider).all()}
        drivers = {d.id: d.name for d in db.query(Driver).all()}

        result = []
        for v in vehicles:
            result.append({
                "id": v.id,
                "name": v.name,
                "vehicle_type": v.vehicle_type,
                "registration_number": v.registration_number or f"TN-37-AB-{v.id + 1000}",
                "capacity": v.capacity or 1,
                "fuel_type": v.fuel_type or "Petrol",
                "provider_id": v.provider_id,
                "provider_name": providers.get(v.provider_id, "Unassigned"),
                "status": v.status or "Available",
                "cost_per_km": v.cost_per_km or 10.0,
                "mileage_kmpl": v.mileage_kmpl or 15.0,
                "current_lat": v.current_lat or 11.0168,
                "current_lng": v.current_lng or 76.9558,
                "current_driver_id": v.current_driver_id,
                "current_driver_name": drivers.get(v.current_driver_id, "Unassigned"),
                "is_active": bool(v.is_active),
            })
        return result

    def get_vehicle_stats(self, db: Session) -> Dict[str, int]:
        self.seed_initial_data_if_needed(db)
        total = db.query(Vehicle).count()
        available = db.query(Vehicle).filter(func.lower(Vehicle.status) == "available").count()
        busy = db.query(Vehicle).filter(func.lower(Vehicle.status) == "busy").count()
        maint = db.query(Vehicle).filter(func.lower(Vehicle.status) == "maintenance").count()

        return {
            "total_vehicles": total,
            "available_vehicles": available,
            "vehicles_in_service": busy,
            "maintenance_vehicles": maint,
        }

    def get_vehicle_locations(self, db: Session) -> List[Dict[str, Any]]:
        self.seed_initial_data_if_needed(db)
        vehicles = db.query(Vehicle).all()
        providers = {p.id: p.name for p in db.query(Provider).all()}
        drivers = {d.id: d.name for d in db.query(Driver).all()}

        coords = SAMPLE_COORDINATES
        result = []
        for i, v in enumerate(vehicles):
            lat = v.current_lat or coords[i % len(coords)][0]
            lng = v.current_lng or coords[i % len(coords)][1]
            result.append({
                "vehicle_id": v.id,
                "vehicle_name": v.name,
                "vehicle_type": v.vehicle_type,
                "registration_number": v.registration_number or f"TN-37-{v.id}",
                "provider_name": providers.get(v.provider_id, "Unassigned"),
                "driver_name": drivers.get(v.current_driver_id, "Unassigned"),
                "status": v.status or "Available",
                "lat": lat,
                "lng": lng,
            })
        return result

    def get_assignment_history(self, db: Session, limit: int = 100) -> List[Dict[str, Any]]:
        self.seed_initial_data_if_needed(db)
        items = db.query(DriverAssignmentHistory).order_by(DriverAssignmentHistory.assignment_time.desc()).limit(limit).all()

        if not items:
            # Seed synthetic history logs if empty
            drivers = db.query(Driver).limit(5).all()
            vehicles = db.query(Vehicle).limit(5).all()
            if drivers and vehicles:
                for i in range(min(len(drivers), len(vehicles))):
                    hist = DriverAssignmentHistory(
                        driver_id=drivers[i].id,
                        vehicle_id=vehicles[i].id,
                        driver_name=drivers[i].name,
                        vehicle_name=vehicles[i].name,
                        status="Active" if i == 0 else "Completed",
                    )
                    db.add(hist)
                db.commit()
                items = db.query(DriverAssignmentHistory).order_by(DriverAssignmentHistory.assignment_time.desc()).limit(limit).all()

        result = []
        for h in items:
            a_time = h.assignment_time or datetime.now(timezone.utc)
            if a_time.tzinfo is None:
                a_time = a_time.replace(tzinfo=timezone.utc)

            c_time_str = None
            if h.completion_time:
                c_t = h.completion_time
                if c_t.tzinfo is None:
                    c_t = c_t.replace(tzinfo=timezone.utc)
                c_time_str = c_t.strftime("%Y-%m-%d %I:%M %p")

            result.append({
                "id": h.id,
                "driver_id": h.driver_id,
                "driver_name": h.driver_name or f"Driver #{h.driver_id}",
                "vehicle_id": h.vehicle_id,
                "vehicle_name": h.vehicle_name or f"Vehicle #{h.vehicle_id}",
                "assignment_time": a_time.strftime("%Y-%m-%d %I:%M %p"),
                "completion_time": c_time_str,
                "status": h.status or "Active",
            })
        return result


driver_service = DriverService()
