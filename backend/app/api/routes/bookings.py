from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.models import RideBooking, FoodBooking, ParcelBooking, BookingStatus, User
from app.schemas.booking import (
    RideBookingCreate, RideBookingUpdate, RideBookingResponse,
    FoodBookingCreate, FoodBookingUpdate, FoodBookingResponse,
    ParcelBookingCreate, ParcelBookingUpdate, ParcelBookingResponse,
    StatusUpdate,
)
from app.api.deps import SessionDep, CurrentUser

router = APIRouter()

# ─────────────────────────────────────────────
# Allowed status transitions for customers
# ─────────────────────────────────────────────
CUSTOMER_CANCELLABLE = {BookingStatus.Pending, BookingStatus.Accepted}


# ══════════════════════════════════════════════
# RIDE BOOKINGS
# ══════════════════════════════════════════════

@router.post("/ride", response_model=RideBookingResponse, status_code=201,
             summary="Create a ride booking")
def create_ride(data: RideBookingCreate, db: SessionDep, current_user: CurrentUser):
    booking = RideBooking(**data.model_dump(), customer_id=current_user.id)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/ride", response_model=List[RideBookingResponse],
            summary="List my ride bookings")
def list_rides(
    db: SessionDep,
    current_user: CurrentUser,
    status: Optional[BookingStatus] = Query(None),
    skip: int = 0,
    limit: int = 20,
):
    q = db.query(RideBooking).filter(RideBooking.customer_id == current_user.id)
    if status:
        q = q.filter(RideBooking.status == status)
    return q.order_by(RideBooking.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/ride/{booking_id}", response_model=RideBookingResponse,
            summary="Get a ride booking by ID")
def get_ride(booking_id: int, db: SessionDep, current_user: CurrentUser):
    booking = db.query(RideBooking).filter(RideBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.customer_id != current_user.id and current_user.role not in ("Admin", "Driver"):
        raise HTTPException(403, "Not authorised")
    return booking


@router.patch("/ride/{booking_id}", response_model=RideBookingResponse,
              summary="Update or cancel a ride booking")
def update_ride(booking_id: int, data: RideBookingUpdate, db: SessionDep, current_user: CurrentUser):
    booking = db.query(RideBooking).filter(RideBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.customer_id != current_user.id and current_user.role != "Admin":
        raise HTTPException(403, "Not authorised")
    if data.status == BookingStatus.Cancelled and booking.status not in CUSTOMER_CANCELLABLE:
        raise HTTPException(400, f"Cannot cancel a booking in '{booking.status}' state")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(booking, field, value)
    db.commit()
    db.refresh(booking)
    return booking


# ══════════════════════════════════════════════
# FOOD BOOKINGS
# ══════════════════════════════════════════════

@router.post("/food", response_model=FoodBookingResponse, status_code=201,
             summary="Create a food delivery booking")
def create_food(data: FoodBookingCreate, db: SessionDep, current_user: CurrentUser):
    booking = FoodBooking(**data.model_dump(), customer_id=current_user.id)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/food", response_model=List[FoodBookingResponse],
            summary="List my food bookings")
def list_food(
    db: SessionDep,
    current_user: CurrentUser,
    status: Optional[BookingStatus] = Query(None),
    skip: int = 0,
    limit: int = 20,
):
    q = db.query(FoodBooking).filter(FoodBooking.customer_id == current_user.id)
    if status:
        q = q.filter(FoodBooking.status == status)
    return q.order_by(FoodBooking.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/food/{booking_id}", response_model=FoodBookingResponse,
            summary="Get a food booking by ID")
def get_food(booking_id: int, db: SessionDep, current_user: CurrentUser):
    booking = db.query(FoodBooking).filter(FoodBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.customer_id != current_user.id and current_user.role not in ("Admin", "Driver"):
        raise HTTPException(403, "Not authorised")
    return booking


@router.patch("/food/{booking_id}", response_model=FoodBookingResponse,
              summary="Update or cancel a food booking")
def update_food(booking_id: int, data: FoodBookingUpdate, db: SessionDep, current_user: CurrentUser):
    booking = db.query(FoodBooking).filter(FoodBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.customer_id != current_user.id and current_user.role != "Admin":
        raise HTTPException(403, "Not authorised")
    if data.status == BookingStatus.Cancelled and booking.status not in CUSTOMER_CANCELLABLE:
        raise HTTPException(400, f"Cannot cancel a booking in '{booking.status}' state")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(booking, field, value)
    db.commit()
    db.refresh(booking)
    return booking


# ══════════════════════════════════════════════
# PARCEL BOOKINGS
# ══════════════════════════════════════════════

@router.post("/parcel", response_model=ParcelBookingResponse, status_code=201,
             summary="Create a parcel delivery booking")
def create_parcel(data: ParcelBookingCreate, db: SessionDep, current_user: CurrentUser):
    booking = ParcelBooking(**data.model_dump(), customer_id=current_user.id)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/parcel", response_model=List[ParcelBookingResponse],
            summary="List my parcel bookings")
def list_parcel(
    db: SessionDep,
    current_user: CurrentUser,
    status: Optional[BookingStatus] = Query(None),
    skip: int = 0,
    limit: int = 20,
):
    q = db.query(ParcelBooking).filter(ParcelBooking.customer_id == current_user.id)
    if status:
        q = q.filter(ParcelBooking.status == status)
    return q.order_by(ParcelBooking.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/parcel/{booking_id}", response_model=ParcelBookingResponse,
            summary="Get a parcel booking by ID")
def get_parcel(booking_id: int, db: SessionDep, current_user: CurrentUser):
    booking = db.query(ParcelBooking).filter(ParcelBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.customer_id != current_user.id and current_user.role not in ("Admin", "Driver"):
        raise HTTPException(403, "Not authorised")
    return booking


@router.patch("/parcel/{booking_id}", response_model=ParcelBookingResponse,
              summary="Update or cancel a parcel booking")
def update_parcel(booking_id: int, data: ParcelBookingUpdate, db: SessionDep, current_user: CurrentUser):
    booking = db.query(ParcelBooking).filter(ParcelBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.customer_id != current_user.id and current_user.role != "Admin":
        raise HTTPException(403, "Not authorised")
    if data.status == BookingStatus.Cancelled and booking.status not in CUSTOMER_CANCELLABLE:
        raise HTTPException(400, f"Cannot cancel a booking in '{booking.status}' state")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(booking, field, value)
    db.commit()
    db.refresh(booking)
    return booking


# ══════════════════════════════════════════════
# UNIFIED HISTORY
# ══════════════════════════════════════════════

@router.get("/history", summary="Get unified booking history (all types)")
def booking_history(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 50,
):
    rides   = db.query(RideBooking  ).filter(RideBooking.customer_id   == current_user.id).all()
    food    = db.query(FoodBooking  ).filter(FoodBooking.customer_id   == current_user.id).all()
    parcels = db.query(ParcelBooking).filter(ParcelBooking.customer_id == current_user.id).all()

    def serialize_ride(b: RideBooking):
        return {
            "type": "ride", "id": b.id, "trip_id": getattr(b, "trip_id", None),
            "pickup_address": b.pickup_address, "drop_address": b.drop_address,
            "pickup_lat": b.pickup_lat, "pickup_lng": b.pickup_lng,
            "drop_lat": b.drop_lat, "drop_lng": b.drop_lng,
            "status": b.status, "estimated_fare": b.estimated_fare,
            "created_at": b.created_at, "vehicle_type": b.vehicle_type,
        }

    def serialize_food(b: FoodBooking):
        return {
            "type": "food", "id": b.id, "trip_id": getattr(b, "trip_id", None),
            "pickup_address": b.restaurant_address, "drop_address": b.delivery_address,
            "pickup_lat": b.restaurant_lat, "pickup_lng": b.restaurant_lng,
            "drop_lat": b.delivery_lat, "drop_lng": b.delivery_lng,
            "restaurant_name": b.restaurant_name, "order_description": b.order_description,
            "status": b.status, "estimated_fare": b.estimated_fare,
            "created_at": b.created_at,
        }

    def serialize_parcel(b: ParcelBooking):
        return {
            "type": "parcel", "id": b.id, "trip_id": getattr(b, "trip_id", None),
            "pickup_address": b.pickup_address, "drop_address": b.drop_address,
            "pickup_lat": b.pickup_lat, "pickup_lng": b.pickup_lng,
            "drop_lat": b.drop_lat, "drop_lng": b.drop_lng,
            "recipient_name": b.recipient_name, "parcel_size": b.parcel_size,
            "status": b.status, "estimated_fare": b.estimated_fare,
            "created_at": b.created_at,
        }

    all_bookings = (
        [serialize_ride(b) for b in rides]
        + [serialize_food(b) for b in food]
        + [serialize_parcel(b) for b in parcels]
    )
    all_bookings.sort(key=lambda x: x["created_at"] or 0, reverse=True)
    return all_bookings[skip: skip + limit]
