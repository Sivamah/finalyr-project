from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import (
    DriverProfile, RideBooking, FoodBooking, ParcelBooking, BatchedTrip,
    BookingStatus, User
)
from app.schemas.driver_profile import (
    DriverProfileCreate, DriverProfileUpdate, DriverProfileResponse
)
from app.schemas.booking import (
    RideBookingResponse, FoodBookingResponse, ParcelBookingResponse, StatusUpdate
)
from app.api.deps import SessionDep, CurrentUser
from app.services import notification_service

router = APIRouter()

# ─────────────────────────────────────────────
# Guard helper
# ─────────────────────────────────────────────
def require_driver(current_user: User):
    if current_user.role != "Driver":
        raise HTTPException(403, "Driver access required")


# ══════════════════════════════════════════════
# DRIVER PROFILE
# ══════════════════════════════════════════════

@router.get("/profile", response_model=DriverProfileResponse,
            summary="Get own driver profile")
def get_profile(db: SessionDep, current_user: CurrentUser):
    require_driver(current_user)
    profile = db.query(DriverProfile).filter(DriverProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(404, "Driver profile not found. Please create one first.")
    return profile


@router.post("/profile", response_model=DriverProfileResponse, status_code=201,
             summary="Create driver profile")
def create_profile(data: DriverProfileCreate, db: SessionDep, current_user: CurrentUser):
    require_driver(current_user)
    existing = db.query(DriverProfile).filter(DriverProfile.user_id == current_user.id).first()
    if existing:
        raise HTTPException(400, "Driver profile already exists. Use PATCH to update.")
    profile = DriverProfile(**data.model_dump(), user_id=current_user.id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/profile", response_model=DriverProfileResponse,
              summary="Update driver profile")
def update_profile(data: DriverProfileUpdate, db: SessionDep, current_user: CurrentUser):
    require_driver(current_user)
    profile = db.query(DriverProfile).filter(DriverProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(404, "Driver profile not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/availability", summary="Toggle driver availability")
def toggle_availability(db: SessionDep, current_user: CurrentUser):
    require_driver(current_user)
    profile = db.query(DriverProfile).filter(DriverProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(404, "Driver profile not found")
    profile.is_available = not profile.is_available
    db.commit()
    return {"is_available": profile.is_available}


# ══════════════════════════════════════════════
# DRIVER — VIEW PENDING REQUESTS
# ══════════════════════════════════════════════

@router.get("/requests", summary="Get all pending requests visible to driver")
def get_pending_requests(db: SessionDep, current_user: CurrentUser):
    require_driver(current_user)

    rides = (
        db.query(RideBooking)
        .filter(RideBooking.status == BookingStatus.Pending)
        .order_by(RideBooking.created_at.desc())
        .limit(20)
        .all()
    )
    food = (
        db.query(FoodBooking)
        .filter(FoodBooking.status == BookingStatus.Pending)
        .order_by(FoodBooking.created_at.desc())
        .limit(20)
        .all()
    )
    parcels = (
        db.query(ParcelBooking)
        .filter(ParcelBooking.status == BookingStatus.Pending)
        .order_by(ParcelBooking.created_at.desc())
        .limit(20)
        .all()
    )

    def fmt_ride(b):
        return {
            "type": "ride", "id": b.id,
            "pickup_address": b.pickup_address, "drop_address": b.drop_address,
            "vehicle_type": b.vehicle_type, "distance_km": b.distance_km,
            "estimated_fare": b.estimated_fare, "notes": b.notes,
            "status": b.status, "created_at": b.created_at,
            "customer_id": b.customer_id,
        }

    def fmt_food(b):
        return {
            "type": "food", "id": b.id,
            "pickup_address": b.restaurant_address, "drop_address": b.delivery_address,
            "restaurant_name": b.restaurant_name, "order_description": b.order_description,
            "distance_km": b.distance_km, "estimated_fare": b.estimated_fare,
            "status": b.status, "created_at": b.created_at,
            "customer_id": b.customer_id,
        }

    def fmt_parcel(b):
        return {
            "type": "parcel", "id": b.id,
            "pickup_address": b.pickup_address, "drop_address": b.drop_address,
            "recipient_name": b.recipient_name, "parcel_size": b.parcel_size,
            "distance_km": b.distance_km, "estimated_fare": b.estimated_fare,
            "is_fragile": b.is_fragile, "status": b.status, "created_at": b.created_at,
            "customer_id": b.customer_id,
        }

    all_requests = (
        [fmt_ride(b) for b in rides]
        + [fmt_food(b) for b in food]
        + [fmt_parcel(b) for b in parcels]
    )
    all_requests.sort(key=lambda x: x["created_at"] or 0, reverse=True)
    return all_requests


@router.get("/active", summary="Get driver's currently active booking")
def get_active_booking(db: SessionDep, current_user: CurrentUser):
    """Returns the first In_Progress or Accepted booking assigned to this driver."""
    require_driver(current_user)
    active_statuses = [BookingStatus.Accepted, BookingStatus.In_Progress]

    batch = db.query(BatchedTrip).filter(
        BatchedTrip.driver_id == current_user.id,
        BatchedTrip.status.in_(active_statuses)
    ).first()
    if batch:
        return {"type": "batch", "id": batch.id, "is_batch": True,
                "pickup_address": "Batched Trip (Multiple Stops)",
                "drop_address": "Various Destinations", "status": batch.status,
                "estimated_fare": batch.total_estimated_fare, "customer_id": None}

    ride = db.query(RideBooking).filter(
        RideBooking.driver_id == current_user.id,
        RideBooking.status.in_(active_statuses)
    ).first()
    if ride:
        return {"type": "ride", "id": ride.id, "pickup_address": ride.pickup_address,
                "drop_address": ride.drop_address, "status": ride.status,
                "estimated_fare": ride.estimated_fare, "customer_id": ride.customer_id}

    food = db.query(FoodBooking).filter(
        FoodBooking.driver_id == current_user.id,
        FoodBooking.status.in_(active_statuses)
    ).first()
    if food:
        return {"type": "food", "id": food.id, "pickup_address": food.restaurant_address,
                "drop_address": food.delivery_address, "status": food.status,
                "estimated_fare": food.estimated_fare, "customer_id": food.customer_id}

    parcel = db.query(ParcelBooking).filter(
        ParcelBooking.driver_id == current_user.id,
        ParcelBooking.status.in_(active_statuses)
    ).first()
    if parcel:
        return {"type": "parcel", "id": parcel.id, "pickup_address": parcel.pickup_address,
                "drop_address": parcel.drop_address, "status": parcel.status,
                "estimated_fare": parcel.estimated_fare, "customer_id": parcel.customer_id}

    return None


@router.get("/completed", summary="Get driver's completed bookings")
def get_completed_bookings(db: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 20):
    require_driver(current_user)
    rides   = db.query(RideBooking  ).filter(RideBooking.driver_id   == current_user.id, RideBooking.status   == BookingStatus.Completed).all()
    food    = db.query(FoodBooking  ).filter(FoodBooking.driver_id   == current_user.id, FoodBooking.status   == BookingStatus.Completed).all()
    parcels = db.query(ParcelBooking).filter(ParcelBooking.driver_id == current_user.id, ParcelBooking.status == BookingStatus.Completed).all()
    all_done = (
        [{"type": "ride", "id": b.id, "from": b.pickup_address, "to": b.drop_address, "fare": b.estimated_fare, "completed_at": b.updated_at} for b in rides]
        + [{"type": "food", "id": b.id, "from": b.restaurant_address, "to": b.delivery_address, "fare": b.estimated_fare, "completed_at": b.updated_at} for b in food]
        + [{"type": "parcel", "id": b.id, "from": b.pickup_address, "to": b.drop_address, "fare": b.estimated_fare, "completed_at": b.updated_at} for b in parcels]
    )
    all_done.sort(key=lambda x: x["completed_at"] or 0, reverse=True)
    return all_done[skip: skip + limit]


# ══════════════════════════════════════════════
# DRIVER — ACCEPT / UPDATE STATUS
# ══════════════════════════════════════════════

BOOKING_MODELS = {
    "ride":   RideBooking,
    "food":   FoodBooking,
    "parcel": ParcelBooking,
}

DRIVER_ALLOWED_TRANSITIONS = {
    BookingStatus.Pending:     BookingStatus.Accepted,
    BookingStatus.Accepted:    BookingStatus.In_Progress,
    BookingStatus.In_Progress: BookingStatus.Completed,
}


def _get_booking_or_404(db, booking_type: str, booking_id: int):
    model = BOOKING_MODELS.get(booking_type)
    if not model:
        raise HTTPException(400, "Invalid booking type. Use ride | food | parcel")
    booking = db.query(model).filter(model.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking


@router.patch("/requests/{booking_type}/{booking_id}/accept",
              summary="Accept a pending booking request")
async def accept_request(
    booking_type: str,
    booking_id: int,
    db: SessionDep,
    current_user: CurrentUser,
):
    require_driver(current_user)
    booking = _get_booking_or_404(db, booking_type, booking_id)

    if booking.status != BookingStatus.Pending:
        raise HTTPException(400, "Only Pending bookings can be accepted")
    if booking.driver_id is not None:
        raise HTTPException(409, "This booking has already been accepted by another driver")

    booking.driver_id = current_user.id
    booking.status = BookingStatus.Accepted
    db.commit()
    db.refresh(booking)

    # Trigger Notification for Customer
    await notification_service.notify_user(
        db, booking.customer_id,
        title="Driver Assigned!",
        message=f"{current_user.full_name} has accepted your {booking_type} request.",
        notification_type="SUCCESS"
    )

    return {"message": "Booking accepted", "booking_id": booking_id, "type": booking_type}


@router.patch("/requests/{booking_type}/{booking_id}/status",
              summary="Update booking status (In_Progress / Completed)")
async def update_booking_status(
    booking_type: str,
    booking_id: int,
    data: StatusUpdate,
    db: SessionDep,
    current_user: CurrentUser,
):
    require_driver(current_user)
    booking = _get_booking_or_404(db, booking_type, booking_id)

    if booking.driver_id != current_user.id:
        raise HTTPException(403, "You are not assigned to this booking")

    expected_next = DRIVER_ALLOWED_TRANSITIONS.get(booking.status)
    if data.status != expected_next:
        raise HTTPException(
            400,
            f"Invalid transition: '{booking.status}' → '{data.status}'. "
            f"Expected next status: '{expected_next}'"
        )

    booking.status = data.status
    if data.status == BookingStatus.Completed:
        # Increment driver total trips
        profile = db.query(DriverProfile).filter(DriverProfile.user_id == current_user.id).first()
        if profile:
            profile.total_trips += 1
            
        await notification_service.notify_user(
            db, booking.customer_id,
            title="Trip Completed",
            message=f"Your {booking_type} has been completed successfully.",
            notification_type="SUCCESS"
        )
    elif data.status == BookingStatus.In_Progress:
        await notification_service.notify_user(
            db, booking.customer_id,
            title="Driver Arriving / In Progress",
            message=f"Your driver is now en route to fulfill your {booking_type}.",
            notification_type="INFO"
        )

    db.commit()
    return {"message": f"Status updated to {data.status}", "booking_id": booking_id}
