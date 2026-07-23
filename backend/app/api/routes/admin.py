from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from app.db.models import User, RideBooking, FoodBooking, ParcelBooking, BookingStatus, DriverProfile
from app.schemas.user import UserResponse
from app.schemas.booking import StatusUpdate
from app.api.deps import SessionDep, CurrentUser

router = APIRouter()

BOOKING_MODELS = {
    "ride":   RideBooking,
    "food":   FoodBooking,
    "parcel": ParcelBooking,
}


def require_admin(current_user: User):
    if current_user.role != "Admin":
        raise HTTPException(403, "Admin access required")


# ══════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════

@router.get("/users", summary="List all users")
def list_users(
    db: SessionDep,
    current_user: CurrentUser,
    role: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
):
    require_admin(current_user)
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    users = q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": u.id, "full_name": u.full_name, "email": u.email,
            "phone": u.phone, "role": u.role, "created_at": u.created_at,
        }
        for u in users
    ]


@router.get("/users/{user_id}", summary="Get a specific user")
def get_user(user_id: int, db: SessionDep, current_user: CurrentUser):
    require_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "id": user.id, "full_name": user.full_name, "email": user.email,
        "phone": user.phone, "role": user.role, "created_at": user.created_at,
    }


@router.patch("/users/{user_id}/role", summary="Change a user's role")
def change_role(user_id: int, payload: dict, db: SessionDep, current_user: CurrentUser):
    require_admin(current_user)
    new_role = payload.get("role")
    if new_role not in ("Admin", "Driver", "Customer"):
        raise HTTPException(400, "Role must be Admin | Driver | Customer")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.role = new_role
    db.commit()
    return {"message": f"Role updated to {new_role}", "user_id": user_id}


# ══════════════════════════════════════════════
# BOOKINGS — VIEW ALL
# ══════════════════════════════════════════════

@router.get("/bookings", summary="List all bookings across all types")
def list_all_bookings(
    db: SessionDep,
    current_user: CurrentUser,
    booking_type: Optional[str] = Query(None, description="ride | food | parcel"),
    status: Optional[BookingStatus] = Query(None),
    skip: int = 0,
    limit: int = 50,
):
    require_admin(current_user)

    def fetch(model, serializer, type_name):
        q = db.query(model)
        if status:
            q = q.filter(model.status == status)
        return [serializer(b, type_name) for b in q.order_by(model.created_at.desc()).all()]

    def ride_ser(b, t):
        return {"type": t, "id": b.id, "customer_id": b.customer_id, "driver_id": b.driver_id,
                "from": b.pickup_address, "to": b.drop_address, "vehicle_type": b.vehicle_type,
                "fare": b.estimated_fare, "status": b.status, "created_at": b.created_at}

    def food_ser(b, t):
        return {"type": t, "id": b.id, "customer_id": b.customer_id, "driver_id": b.driver_id,
                "from": b.restaurant_address, "to": b.delivery_address,
                "restaurant": b.restaurant_name, "fare": b.estimated_fare,
                "status": b.status, "created_at": b.created_at}

    def parcel_ser(b, t):
        return {"type": t, "id": b.id, "customer_id": b.customer_id, "driver_id": b.driver_id,
                "from": b.pickup_address, "to": b.drop_address,
                "recipient": b.recipient_name, "size": b.parcel_size,
                "fare": b.estimated_fare, "status": b.status, "created_at": b.created_at}

    all_bookings = []
    if not booking_type or booking_type == "ride":
        all_bookings += fetch(RideBooking, ride_ser, "ride")
    if not booking_type or booking_type == "food":
        all_bookings += fetch(FoodBooking, food_ser, "food")
    if not booking_type or booking_type == "parcel":
        all_bookings += fetch(ParcelBooking, parcel_ser, "parcel")

    all_bookings.sort(key=lambda x: x["created_at"] or 0, reverse=True)
    return all_bookings[skip: skip + limit]


@router.patch("/bookings/{booking_type}/{booking_id}/status",
              summary="Force-change booking status (admin override)")
def force_status(
    booking_type: str,
    booking_id: int,
    data: StatusUpdate,
    db: SessionDep,
    current_user: CurrentUser,
):
    require_admin(current_user)
    model = BOOKING_MODELS.get(booking_type)
    if not model:
        raise HTTPException(400, "Invalid booking type. Use ride | food | parcel")
    booking = db.query(model).filter(model.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    booking.status = data.status
    db.commit()
    return {"message": f"Status forced to {data.status}", "booking_id": booking_id}


# ══════════════════════════════════════════════
# STATS
# ══════════════════════════════════════════════

@router.get("/stats", summary="Dashboard summary statistics")
def get_stats(db: SessionDep, current_user: CurrentUser):
    require_admin(current_user)
    total_users    = db.query(func.count(User.id)).scalar()
    total_drivers  = db.query(func.count(User.id)).filter(User.role == "Driver").scalar()
    total_customers = db.query(func.count(User.id)).filter(User.role == "Customer").scalar()

    total_rides    = db.query(func.count(RideBooking.id)).scalar()
    total_food     = db.query(func.count(FoodBooking.id)).scalar()
    total_parcels  = db.query(func.count(ParcelBooking.id)).scalar()

    active_rides   = db.query(func.count(RideBooking.id)).filter(RideBooking.status.in_([BookingStatus.Pending, BookingStatus.Accepted, BookingStatus.In_Progress])).scalar()
    active_food    = db.query(func.count(FoodBooking.id)).filter(FoodBooking.status.in_([BookingStatus.Pending, BookingStatus.Accepted, BookingStatus.In_Progress])).scalar()
    active_parcels = db.query(func.count(ParcelBooking.id)).filter(ParcelBooking.status.in_([BookingStatus.Pending, BookingStatus.Accepted, BookingStatus.In_Progress])).scalar()

    return {
        "total_users":     total_users,
        "total_drivers":   total_drivers,
        "total_customers": total_customers,
        "total_bookings":  total_rides + total_food + total_parcels,
        "active_bookings": active_rides + active_food + active_parcels,
        "by_type": {
            "ride":   {"total": total_rides,   "active": active_rides},
            "food":   {"total": total_food,    "active": active_food},
            "parcel": {"total": total_parcels, "active": active_parcels},
        }
    }
