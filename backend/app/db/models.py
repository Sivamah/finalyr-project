from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum


# ──────────────────────────────────────────────
# Python Enums (used for validation only)
# ──────────────────────────────────────────────

class BookingStatus(str, enum.Enum):
    Pending     = "Pending"
    Accepted    = "Accepted"
    In_Progress = "In_Progress"
    Completed   = "Completed"
    Cancelled   = "Cancelled"


class VehicleType(str, enum.Enum):
    Bike  = "Bike"
    Auto  = "Auto"
    Car   = "Car"
    Van   = "Van"
    Truck = "Truck"


class ParcelSize(str, enum.Enum):
    Small  = "Small"
    Medium = "Medium"
    Large  = "Large"


# ──────────────────────────────────────────────
# User
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    full_name     = Column(String, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    phone         = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role          = Column(String, default="Customer")   # Admin | Driver | Customer
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    driver_profile  = relationship("DriverProfile", back_populates="user", uselist=False)
    ride_bookings   = relationship("RideBooking",   back_populates="customer", foreign_keys="RideBooking.customer_id")
    food_bookings   = relationship("FoodBooking",   back_populates="customer", foreign_keys="FoodBooking.customer_id")
    parcel_bookings = relationship("ParcelBooking", back_populates="customer", foreign_keys="ParcelBooking.customer_id")


# ──────────────────────────────────────────────
# Driver Profile
# ──────────────────────────────────────────────

class DriverProfile(Base):
    __tablename__ = "driver_profiles"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    vehicle_type   = Column(String, nullable=False, default="Bike")   # VehicleType values
    vehicle_number = Column(String, nullable=False)
    vehicle_model  = Column(String)
    is_available   = Column(Boolean, default=True)
    rating         = Column(Float, default=5.0)
    total_trips    = Column(Integer, default=0)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="driver_profile")


# ──────────────────────────────────────────────
# Batched Trip (DMFE Optimization)
# ──────────────────────────────────────────────

class BatchedTrip(Base):
    __tablename__ = "batched_trips"

    id                   = Column(Integer, primary_key=True, index=True)
    driver_id            = Column(Integer, ForeignKey("users.id"), nullable=True)
    status               = Column(String, default="Pending", nullable=False)
    total_estimated_fare = Column(Float, default=0.0)
    total_distance_km    = Column(Float, default=0.0)
    optimized_route_json = Column(Text)  # Stores the ordered waypoints
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())

    driver          = relationship("User", foreign_keys=[driver_id])
    ride_bookings   = relationship("RideBooking", back_populates="batch")
    food_bookings   = relationship("FoodBooking", back_populates="batch")
    parcel_bookings = relationship("ParcelBooking", back_populates="batch")


# ──────────────────────────────────────────────
# Ride Booking (Passenger)
# ──────────────────────────────────────────────

class RideBooking(Base):
    __tablename__ = "ride_bookings"

    id             = Column(Integer, primary_key=True, index=True)
    customer_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id      = Column(Integer, ForeignKey("users.id"), nullable=True)
    batch_id       = Column(Integer, ForeignKey("batched_trips.id"), nullable=True)

    pickup_address = Column(String, nullable=False)
    pickup_lat     = Column(Float, nullable=False)
    pickup_lng     = Column(Float, nullable=False)

    drop_address   = Column(String, nullable=False)
    drop_lat       = Column(Float, nullable=False)
    drop_lng       = Column(Float, nullable=False)

    vehicle_type   = Column(String, nullable=False, default="Bike")  # VehicleType values
    distance_km    = Column(Float)
    estimated_fare = Column(Float)
    notes          = Column(Text)
    status         = Column(String, default="Pending", nullable=False)  # BookingStatus values

    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("User", back_populates="ride_bookings",   foreign_keys=[customer_id])
    driver   = relationship("User", foreign_keys=[driver_id])
    batch    = relationship("BatchedTrip", back_populates="ride_bookings")


# ──────────────────────────────────────────────
# Food Booking
# ──────────────────────────────────────────────

class FoodBooking(Base):
    __tablename__ = "food_bookings"

    id                   = Column(Integer, primary_key=True, index=True)
    customer_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id            = Column(Integer, ForeignKey("users.id"), nullable=True)
    batch_id             = Column(Integer, ForeignKey("batched_trips.id"), nullable=True)

    restaurant_name      = Column(String, nullable=False)
    restaurant_address   = Column(String, nullable=False)
    restaurant_lat       = Column(Float)
    restaurant_lng       = Column(Float)

    delivery_address     = Column(String, nullable=False)
    delivery_lat         = Column(Float)
    delivery_lng         = Column(Float)

    order_description    = Column(Text, nullable=False)
    special_instructions = Column(Text)
    distance_km          = Column(Float)
    estimated_fare       = Column(Float)
    status               = Column(String, default="Pending", nullable=False)

    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("User", back_populates="food_bookings",   foreign_keys=[customer_id])
    driver   = relationship("User", foreign_keys=[driver_id])
    batch    = relationship("BatchedTrip", back_populates="food_bookings")


# ──────────────────────────────────────────────
# Parcel Booking
# ──────────────────────────────────────────────

class ParcelBooking(Base):
    __tablename__ = "parcel_bookings"

    id              = Column(Integer, primary_key=True, index=True)
    customer_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id       = Column(Integer, ForeignKey("users.id"), nullable=True)
    batch_id        = Column(Integer, ForeignKey("batched_trips.id"), nullable=True)

    sender_name     = Column(String, nullable=False)
    sender_phone    = Column(String, nullable=False)
    pickup_address  = Column(String, nullable=False)
    pickup_lat      = Column(Float)
    pickup_lng      = Column(Float)

    recipient_name  = Column(String, nullable=False)
    recipient_phone = Column(String, nullable=False)
    drop_address    = Column(String, nullable=False)
    drop_lat        = Column(Float)
    drop_lng        = Column(Float)

    parcel_size     = Column(String, nullable=False, default="Small")  # ParcelSize values
    weight_kg       = Column(Float)
    description     = Column(Text)
    is_fragile      = Column(Boolean, default=False)
    distance_km     = Column(Float)
    estimated_fare  = Column(Float)
    status          = Column(String, default="Pending", nullable=False)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("User", back_populates="parcel_bookings", foreign_keys=[customer_id])
    driver   = relationship("User", foreign_keys=[driver_id])
    batch    = relationship("BatchedTrip", back_populates="parcel_bookings")


# ──────────────────────────────────────────────
# Phase 4 - Trip Scheduler & Driver Allocation Engine
# ──────────────────────────────────────────────

class Trip(Base):
    __tablename__ = "trips"

    id         = Column(Integer, primary_key=True, index=True)
    batch_id   = Column(Integer, ForeignKey("batched_trips.id"), unique=True, nullable=False)
    trip_type  = Column(String, default="Single")  # Single, Combined
    priority   = Column(String, default="Medium")  # High, Medium, Low
    status     = Column(String, default="Pending") # Pending, Queued, Assigned, Accepted, In_Progress, Completed, Cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    batch       = relationship("BatchedTrip")
    assignments = relationship("DriverAssignment", back_populates="trip")
    history     = relationship("AssignmentHistory", back_populates="trip")


class DriverLocation(Base):
    __tablename__ = "driver_locations"

    id           = Column(Integer, primary_key=True, index=True)
    driver_id    = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    lat          = Column(Float, nullable=False)
    lng          = Column(Float, nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    driver = relationship("User", foreign_keys=[driver_id])


class DriverAssignment(Base):
    __tablename__ = "driver_assignments"

    id          = Column(Integer, primary_key=True, index=True)
    trip_id     = Column(Integer, ForeignKey("trips.id"), nullable=False)
    driver_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    status      = Column(String, default="Pending") # Pending, Accepted, Rejected, Expired
    score       = Column(Float, default=0.0)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at  = Column(DateTime(timezone=True))

    trip   = relationship("Trip", back_populates="assignments")
    driver = relationship("User", foreign_keys=[driver_id])


class AssignmentHistory(Base):
    __tablename__ = "assignment_history"

    id         = Column(Integer, primary_key=True, index=True)
    trip_id    = Column(Integer, ForeignKey("trips.id"), nullable=False)
    driver_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    status     = Column(String, nullable=False)
    reason     = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trip   = relationship("Trip", back_populates="history")
    driver = relationship("User", foreign_keys=[driver_id])


# ──────────────────────────────────────────────
# Phase 5 - Route Optimization & Google Maps
# ──────────────────────────────────────────────

class RouteDetail(Base):
    __tablename__ = "route_details"

    id                    = Column(Integer, primary_key=True, index=True)
    trip_id               = Column(Integer, ForeignKey("trips.id"), unique=True, nullable=False)
    total_distance_km     = Column(Float, default=0.0)
    total_duration_mins   = Column(Float, default=0.0)
    estimated_fuel_liters = Column(Float, default=0.0)
    polyline              = Column(Text)
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), onupdate=func.now())

    trip  = relationship("Trip", backref="route_detail")
    stops = relationship("OptimizedStop", back_populates="route_detail", cascade="all, delete")


class OptimizedStop(Base):
    __tablename__ = "optimized_stops"

    id            = Column(Integer, primary_key=True, index=True)
    route_id      = Column(Integer, ForeignKey("route_details.id"), nullable=False)
    stop_sequence = Column(Integer, nullable=False)
    lat           = Column(Float, nullable=False)
    lng           = Column(Float, nullable=False)
    address       = Column(String)
    action        = Column(String)  # Pickup / Drop
    eta_mins      = Column(Float, default=0.0)

    route_detail = relationship("RouteDetail", back_populates="stops")

# ──────────────────────────────────────────────
# Phase 6 - Live Tracking & Notifications
# ──────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    title      = Column(String, nullable=False)
    message    = Column(String, nullable=False)
    type       = Column(String, default="INFO") # INFO, SUCCESS, WARNING, ERROR
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="notifications")


# ──────────────────────────────────────────────
# Phase 8 - AI Decision History & Explainability
# ──────────────────────────────────────────────

class AIDecision(Base):
    __tablename__ = "ai_decisions"

    id                  = Column(Integer, primary_key=True, index=True)
    batch_id            = Column(Integer, ForeignKey("batched_trips.id"), nullable=False)
    decision_type       = Column(String, nullable=False)       # "combined" | "single"
    feasibility_score   = Column(Float, default=0.0)           # 0–100
    route_similarity    = Column(Float, default=0.0)           # 0–100
    estimated_delay_min = Column(Float, default=0.0)
    fuel_saved_pct      = Column(Float, default=0.0)
    co2_reduction_pct   = Column(Float, default=0.0)
    driver_available    = Column(Boolean, default=False)
    capacity_sufficient = Column(Boolean, default=True)
    request_count       = Column(Integer, default=1)
    explanation_json    = Column(Text)                          # Full structured JSON
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    batch = relationship("BatchedTrip", backref="ai_decisions")

