from typing import Optional, List
from pydantic import BaseModel


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
    pickup_address: str = ""
    drop_address: str = ""
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

    class Config:
        from_attributes = True


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
