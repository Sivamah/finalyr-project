from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class XAIFactors(BaseModel):
    pickup_distance_score: float = 85.0
    destination_similarity: float = 88.0
    estimated_delay_score: float = 90.0
    vehicle_capacity_score: float = 95.0
    priority_score: float = 80.0
    overall_compatibility_score: float = 89.5
    pickup_distance_km: float = 0.0
    time_difference_min: float = 0.0
    route_similarity_pct: float = 0.0
    estimated_delay_min: float = 0.0


class XAITimelineItem(BaseModel):
    title: str
    timestamp: str
    status: str = "completed"  # completed / active / pending
    description: str = ""


class XAIRequestPoint(BaseModel):
    """One request point the live map should highlight (pickup + drop)."""
    request_id: int
    request_type: str = "ride"
    pickup_address: str = ""
    drop_address: str = ""
    pickup_lat: float = 0.0
    pickup_lng: float = 0.0
    drop_lat: float = 0.0
    drop_lng: float = 0.0
    priority: str = "Medium"


class XAIDriverLink(BaseModel):
    """Assigned driver snapshot for a dispatched trip."""
    id: int
    name: str = ""
    current_lat: float = 0.0
    current_lng: float = 0.0


class XAIVehicleLink(BaseModel):
    """Assigned vehicle snapshot for a dispatched trip."""
    id: int
    name: str = ""
    vehicle_type: str = ""
    current_lat: float = 0.0
    current_lng: float = 0.0


class XAIRouteStopPoint(BaseModel):
    """One ordered stop of the optimized route (map polyline vertex)."""
    request_id: int
    action: str  # "pickup" | "drop"
    lat: float = 0.0
    lng: float = 0.0
    arrival_min: float = 0.0


class XAITripLink(BaseModel):
    """Dispatched trip snapshot consumed by the live map highlight layer."""
    trip_id: int
    trip_code: str = ""
    is_shared: bool = False
    status: str = "Active"
    driver: Optional[XAIDriverLink] = None
    vehicle: Optional[XAIVehicleLink] = None
    route_stops: List[XAIRouteStopPoint] = []


class XAIExplanationItem(BaseModel):
    id: int
    request_id: int
    request_type: str            # ride / food / parcel
    provider_id: Optional[int] = None
    provider_name: str = "Unassigned"
    status: str = "Evaluated"     # Pending / Evaluated / Compatible / Incompatible
    decision: str = "Compatible for Batching"
    decision_summary: str = ""
    reason: str = ""
    confidence_score: float = 90.0
    # True when the engine did not record a real confidence at decision time
    # (historical rows / static-mode baseline) and the score-derived estimate
    # is being displayed instead.  Additive — the UI should label it
    # "(estimated)" rather than presenting it as a recorded value.
    confidence_fallback: bool = False
    pickup_address: str = ""
    drop_address: str = ""
    pickup_lat: float = 0.0
    pickup_lng: float = 0.0
    drop_lat: float = 0.0
    drop_lng: float = 0.0
    key_reasons: List[str] = []
    related_requests: List[XAIRequestPoint] = []
    trip: Optional[XAITripLink] = None
    estimated_distance_km: float = 0.0
    factors: XAIFactors
    timeline: List[XAITimelineItem] = []
    created_at: str
    batched_with_request_ids: List[int] = []
    fuel_saved_l: float = 0.0
    co2_saved_kg: float = 0.0
    distance_saved_km: float = 0.0
    driver_profit_inr: float = 0.0
    trip_code: Optional[str] = None
    # Real ₹ cost of this trip as actually dispatched (combined when shared,
    # individual otherwise), and what running the same requests as separate
    # individual trips would have cost at the same per-km rate the optimizer
    # used. Both copied straight from values already computed/stored at
    # dispatch time — see xai_service._trip_metrics.
    trip_cost_inr: float = 0.0
    separate_cost_inr: float = 0.0
    # Profit if these requests had been run as separate individual trips,
    # using the SAME revenue/fuel-cost formula as driver_profit_inr (see
    # xai_service._trip_metrics) applied to the pre-batching distance/fuel
    # instead of the actual dispatched trip's — lets the UI show a real
    # solo-vs-combined profit comparison without a second pricing model.
    solo_profit_inr: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class KeyValueCount(BaseModel):
    name: str
    count: int


class XAIOverviewResponse(BaseModel):
    total_explanations: int = 0
    avg_compatibility_score: float = 0.0
    avg_confidence_score: float = 0.0
    most_common_decision: str = "N/A"
    decision_breakdown: List[KeyValueCount] = []
    score_distribution: List[KeyValueCount] = []
    explanations: List[XAIExplanationItem] = []
    timestamp: str
