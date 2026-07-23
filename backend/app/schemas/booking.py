from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.db.models import BookingStatus, VehicleType, ParcelSize


# ══════════════════════════════════════════════
# Shared
# ══════════════════════════════════════════════

class StatusUpdate(BaseModel):
    status: BookingStatus


# ══════════════════════════════════════════════
# Ride Booking
# ══════════════════════════════════════════════

class RideBookingCreate(BaseModel):
    pickup_address : str
    pickup_lat     : float
    pickup_lng     : float
    drop_address   : str
    drop_lat       : float
    drop_lng       : float
    vehicle_type   : VehicleType = VehicleType.Bike
    distance_km    : Optional[float] = None
    estimated_fare : Optional[float] = None
    notes          : Optional[str]   = None


class RideBookingUpdate(BaseModel):
    status         : Optional[BookingStatus] = None
    notes          : Optional[str]           = None


class DriverInfo(BaseModel):
    id        : int
    full_name : str
    phone     : Optional[str] = None

    class Config:
        from_attributes = True


class RideBookingResponse(BaseModel):
    id             : int
    customer_id    : int
    driver_id      : Optional[int] = None
    pickup_address : str
    pickup_lat     : float
    pickup_lng     : float
    drop_address   : str
    drop_lat       : float
    drop_lng       : float
    vehicle_type   : VehicleType
    distance_km    : Optional[float] = None
    estimated_fare : Optional[float] = None
    notes          : Optional[str]   = None
    status         : BookingStatus
    created_at     : Optional[datetime] = None
    updated_at     : Optional[datetime] = None
    driver         : Optional[DriverInfo] = None

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
# Food Booking
# ══════════════════════════════════════════════

class FoodBookingCreate(BaseModel):
    restaurant_name      : str
    restaurant_address   : str
    restaurant_lat       : Optional[float] = None
    restaurant_lng       : Optional[float] = None
    delivery_address     : str
    delivery_lat         : Optional[float] = None
    delivery_lng         : Optional[float] = None
    order_description    : str
    special_instructions : Optional[str]   = None
    distance_km          : Optional[float] = None
    estimated_fare       : Optional[float] = None


class FoodBookingUpdate(BaseModel):
    status               : Optional[BookingStatus] = None
    special_instructions : Optional[str]           = None


class FoodBookingResponse(BaseModel):
    id                   : int
    customer_id          : int
    driver_id            : Optional[int]   = None
    restaurant_name      : str
    restaurant_address   : str
    restaurant_lat       : Optional[float] = None
    restaurant_lng       : Optional[float] = None
    delivery_address     : str
    delivery_lat         : Optional[float] = None
    delivery_lng         : Optional[float] = None
    order_description    : str
    special_instructions : Optional[str]   = None
    distance_km          : Optional[float] = None
    estimated_fare       : Optional[float] = None
    status               : BookingStatus
    created_at           : Optional[datetime] = None
    updated_at           : Optional[datetime] = None
    driver               : Optional[DriverInfo] = None

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
# Parcel Booking
# ══════════════════════════════════════════════

class ParcelBookingCreate(BaseModel):
    sender_name      : str
    sender_phone     : str
    pickup_address   : str
    pickup_lat       : Optional[float] = None
    pickup_lng       : Optional[float] = None
    recipient_name   : str
    recipient_phone  : str
    drop_address     : str
    drop_lat         : Optional[float] = None
    drop_lng         : Optional[float] = None
    parcel_size      : ParcelSize = ParcelSize.Small
    weight_kg        : Optional[float] = None
    description      : Optional[str]  = None
    is_fragile       : bool = False
    distance_km      : Optional[float] = None
    estimated_fare   : Optional[float] = None


class ParcelBookingUpdate(BaseModel):
    status           : Optional[BookingStatus] = None
    description      : Optional[str]           = None


class ParcelBookingResponse(BaseModel):
    id               : int
    customer_id      : int
    driver_id        : Optional[int]   = None
    sender_name      : str
    sender_phone     : str
    pickup_address   : str
    pickup_lat       : Optional[float] = None
    pickup_lng       : Optional[float] = None
    recipient_name   : str
    recipient_phone  : str
    drop_address     : str
    drop_lat         : Optional[float] = None
    drop_lng         : Optional[float] = None
    parcel_size      : ParcelSize
    weight_kg        : Optional[float] = None
    description      : Optional[str]  = None
    is_fragile       : bool
    distance_km      : Optional[float] = None
    estimated_fare   : Optional[float] = None
    status           : BookingStatus
    created_at       : Optional[datetime] = None
    updated_at       : Optional[datetime] = None
    driver           : Optional[DriverInfo] = None

    class Config:
        from_attributes = True
