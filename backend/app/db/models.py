from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# Register DMFE models so Base.metadata.create_all() creates their tables
from app.dmfe.models import DMFEBatch, DMFEAnalysisRun  # noqa: F401


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    full_name     = Column(String, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role          = Column(String, default="Admin")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())


class Provider(Base):
    __tablename__ = "providers"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String, nullable=False)
    provider_type   = Column(String, nullable=False)
    category        = Column(String, default="Ride")          # Ride / Food / Parcel
    status          = Column(String, default="Active")
    operating_area  = Column(String, default="Coimbatore")
    api_status      = Column(String, default="Simulated")
    simulation_mode = Column(Boolean, default=True)
    logo            = Column(String)
    description     = Column(Text)
    pricing_model   = Column(Text)           # JSON: {"base_fare":30,"per_km":12,...}
    service_constraints = Column(Text)       # JSON: {"max_detour_pct":5,"max_weight_kg":20,...}
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    vehicles = relationship("Vehicle", back_populates="provider", cascade="all, delete")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id                  = Column(Integer, primary_key=True, index=True)
    provider_id         = Column(Integer, ForeignKey("providers.id"), nullable=False)
    name                = Column(String, nullable=False)
    vehicle_type        = Column(String, nullable=False)
    registration_number = Column(String, default="TN-37-AB-1001")
    capacity            = Column(Integer, default=1)
    fuel_type           = Column(String, default="Petrol")
    mileage_kmpl        = Column(Float, default=15.0)
    cost_per_km         = Column(Float, default=10.0)
    status              = Column(String, default="Available")  # Available / Busy / Offline / Maintenance
    current_lat         = Column(Float, default=11.0168)
    current_lng         = Column(Float, default=76.9558)
    current_driver_id   = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    is_active           = Column(Boolean, default=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    provider       = relationship("Provider", back_populates="vehicles")
    current_driver = relationship("Driver", foreign_keys=[current_driver_id])


class Driver(Base):
    __tablename__ = "drivers"

    id                  = Column(Integer, primary_key=True, index=True)
    provider_id         = Column(Integer, ForeignKey("providers.id"), nullable=True)
    name                = Column(String, nullable=False)
    phone               = Column(String, default="+91 98765 43210")
    email               = Column(String, nullable=True)
    status              = Column(String, default="Available")  # Available / Busy / Offline
    license_number      = Column(String, default="TN37 2024001001")
    current_lat         = Column(Float, default=11.0168)
    current_lng         = Column(Float, default=76.9558)
    assigned_vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    provider         = relationship("Provider")
    assigned_vehicle = relationship("Vehicle", foreign_keys=[assigned_vehicle_id])


class DriverAssignmentHistory(Base):
    __tablename__ = "driver_assignment_history"

    id              = Column(Integer, primary_key=True, index=True)
    driver_id       = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    vehicle_id      = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    driver_name     = Column(String, nullable=True)
    vehicle_name    = Column(String, nullable=True)
    assignment_time = Column(DateTime(timezone=True), server_default=func.now())
    completion_time = Column(DateTime(timezone=True), nullable=True)
    status          = Column(String, default="Active")  # Active / Completed / Cancelled

    driver  = relationship("Driver")
    vehicle = relationship("Vehicle")


class Trip(Base):
    """
    A dispatched trip created by the Phase 9 DMFE pipeline.

    Covers both Shared Trips (multiple requests, is_shared=True) and
    Individual Trips (single request).  Route metrics come from the
    OR-Tools RouteOptimizer output.
    """
    __tablename__ = "trips"

    id                  = Column(Integer, primary_key=True, index=True)
    trip_code           = Column(String, nullable=False, index=True)
    batch_id            = Column(Integer, ForeignKey("dmfe_batches.id"), nullable=True)
    driver_id           = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    vehicle_id          = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    request_ids_json    = Column(Text, default="[]")
    is_shared           = Column(Boolean, default=False)
    status              = Column(String, default="Planned")  # Planned / Active / Completed / Cancelled
    stop_order_json     = Column(Text, default="[]")
    total_distance_km   = Column(Float, default=0.0)
    total_duration_min  = Column(Float, default=0.0)
    eta_min             = Column(Float, default=0.0)
    fuel_l              = Column(Float, default=0.0)
    utilization_pct     = Column(Float, default=0.0)
    max_delay_min       = Column(Float, default=0.0)
    matrix_source       = Column(String, default="haversine_fallback")
    estimated_cost      = Column(Float, default=0.0)
    distance_saved_km   = Column(Float, default=0.0)
    fuel_saved_l        = Column(Float, default=0.0)
    co2_saved_kg        = Column(Float, default=0.0)
    optimization_score  = Column(Float, default=0.0)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    completed_at        = Column(DateTime(timezone=True), nullable=True)

    driver  = relationship("Driver")
    vehicle = relationship("Vehicle")
    batch   = relationship("DMFEBatch")


class DriverAssignment(Base):
    """Driver → vehicle → trip assignment record (Phase 9)."""
    __tablename__ = "assignments"

    id              = Column(Integer, primary_key=True, index=True)
    trip_id         = Column(Integer, ForeignKey("trips.id"), nullable=False)
    driver_id       = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    vehicle_id      = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    driver_name     = Column(String, default="")
    vehicle_name    = Column(String, default="")
    assignment_type = Column(String, default="AUTO")  # AUTO / MANUAL
    status          = Column(String, default="Active")  # Active / Completed / Cancelled
    assigned_at     = Column(DateTime(timezone=True), server_default=func.now())
    completed_at    = Column(DateTime(timezone=True), nullable=True)

    trip   = relationship("Trip")
    driver = relationship("Driver")
    vehicle = relationship("Vehicle")



class Dataset(Base):
    __tablename__ = "datasets"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    file_type   = Column(String, nullable=False)
    data_type   = Column(String, nullable=False)
    file_path   = Column(String)
    row_count   = Column(Integer, default=0)
    description = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class SimulationRequest(Base):
    __tablename__ = "simulation_requests"

    id                  = Column(Integer, primary_key=True, index=True)
    provider_id         = Column(Integer, ForeignKey("providers.id"), nullable=True)
    request_type        = Column(String, nullable=False)           # ride / food / parcel
    pickup_lat          = Column(Float, nullable=False)
    pickup_lng          = Column(Float, nullable=False)
    drop_lat            = Column(Float, nullable=False)
    drop_lng            = Column(Float, nullable=False)
    pickup_address      = Column(String, default="")
    drop_address        = Column(String, default="")
    demand              = Column(Integer, default=1)
    priority            = Column(String, default="Medium")         # Low / Medium / High
    weight_kg           = Column(Float, default=0.0)
    vehicle_type        = Column(String, default="Auto")
    estimated_distance_km = Column(Float, default=0.0)
    request_timestamp   = Column(DateTime(timezone=True), server_default=func.now())
    status              = Column(String, default="Pending")
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    provider = relationship("Provider")


class OptimizationResult(Base):
    __tablename__ = "optimization_results"

    id                  = Column(Integer, primary_key=True, index=True)
    batch_id            = Column(String, nullable=True)
    request_count       = Column(Integer, default=0)
    provider_id         = Column(Integer, ForeignKey("providers.id"), nullable=True)
    vehicle_id          = Column(Integer, ForeignKey("vehicles.id"), nullable=True)

    best_route_json     = Column(Text)
    chosen_provider     = Column(String)
    chosen_vehicle      = Column(String)
    estimated_cost      = Column(Float)
    eta_mins            = Column(Float)
    fuel_saved_l        = Column(Float)
    distance_saved_km   = Column(Float)
    co2_saved_kg        = Column(Float)
    optimization_score  = Column(Float)
    explanation_json    = Column(Text)

    # DMFE fields
    is_batched          = Column(Boolean, default=True)
    rejection_reason    = Column(Text)
    feasibility_score   = Column(Float, default=0.0)
    natural_explanation = Column(Text)

    # Baseline comparison (without AI)
    baseline_distance_km = Column(Float, default=0.0)
    baseline_fuel_l      = Column(Float, default=0.0)
    baseline_co2_kg      = Column(Float, default=0.0)
    baseline_vehicles    = Column(Integer, default=0)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    provider = relationship("Provider")
    vehicle  = relationship("Vehicle")


class SystemNotification(Base):
    __tablename__ = "system_notifications"

    id            = Column(Integer, primary_key=True, index=True)
    title         = Column(String, nullable=False)
    description   = Column(Text, default="")
    category      = Column(String, default="Information")  # Information / Success / Warning / Error
    event_type    = Column(String, default="simulation_state")  # simulation_state / request_lifecycle / provider_mgmt / dataset_import / system_error
    request_id    = Column(Integer, nullable=True)
    provider_name = Column(String, nullable=True)
    is_read       = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id         = Column(Integer, primary_key=True, index=True)
    category   = Column(String, index=True)  # simulation / provider / vehicle / ai_rules / preferences
    key        = Column(String, unique=True, index=True, nullable=False)
    value      = Column(Text, nullable=False)  # JSON string
    data_type  = Column(String, default="string")  # string / int / float / bool / json
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConfigAuditLog(Base):
    __tablename__ = "config_audit_logs"

    id             = Column(Integer, primary_key=True, index=True)
    config_key     = Column(String, nullable=False)
    category       = Column(String, nullable=False)
    user_email     = Column(String, default="admin@antigravity.ai")
    previous_value = Column(Text, nullable=True)
    new_value      = Column(Text, nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())


class SimulationScenario(Base):
    __tablename__ = "simulation_scenarios"

    id                 = Column(Integer, primary_key=True, index=True)
    name               = Column(String, nullable=False, unique=True)
    description        = Column(Text, default="")
    traffic_multiplier = Column(Float, default=1.0)
    demand_multiplier  = Column(Float, default=1.0)
    weather_condition  = Column(String, default="Clear")  # Clear / Rain / Heavy Traffic
    is_preset          = Column(Boolean, default=False)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())


class SavedSimulation(Base):
    __tablename__ = "saved_simulations"

    id                   = Column(Integer, primary_key=True, index=True)
    name                 = Column(String, nullable=False)
    scenario_name        = Column(String, default="Standard Run")
    duration_seconds     = Column(Float, default=0.0)
    total_requests       = Column(Integer, default=0)
    completed_requests   = Column(Integer, default=0)
    completion_rate      = Column(Float, default=0.0)
    avg_waiting_time_sec = Column(Float, default=0.0)
    provider_stats_json  = Column(Text)  # JSON string
    queue_stats_json     = Column(Text)  # JSON string
    events_timeline_json = Column(Text)  # JSON string
    created_at           = Column(DateTime(timezone=True), server_default=func.now())



