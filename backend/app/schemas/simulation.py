from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class SimulationStatus(BaseModel):
    """Current state and metrics of the live simulation engine."""
    running: bool
    paused: bool = False
    status_text: str = "Stopped"  # Running / Paused / Stopped
    total_generated: int = 0
    queue_size: int = 0
    history_size: int = 0
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    runtime_seconds: float = 0.0
    requests_per_minute: float = 0.0

    # Category breakdown statistics
    pending_ride: int = 0
    pending_food: int = 0
    pending_parcel: int = 0
    completed_ride: int = 0
    completed_food: int = 0
    completed_parcel: int = 0


class SimulationQueueItem(BaseModel):
    """Slim view of a single queued simulation request for the live panel."""
    id: int
    request_type: str          # ride / food / parcel
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    pickup_address: str = ""
    drop_address: str = ""
    pickup_lat: float = 0.0
    pickup_lng: float = 0.0
    drop_lat: float = 0.0
    drop_lng: float = 0.0
    demand: int = 1
    weight_kg: float = 0.0
    priority: str = "Medium"
    estimated_distance_km: float = 0.0
    estimated_time_min: float = 0.0
    status: str = "Pending"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SimulationHistoryItem(BaseModel):
    """Slim view of a completed simulation request."""
    id: int
    request_type: str
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    pickup_address: str = ""
    drop_address: str = ""
    priority: str = "Medium"
    estimated_distance_km: float = 0.0
    status: str = "Completed"
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    processing_duration_sec: float = 0.0

    class Config:
        from_attributes = True


class SimulationQueueResponse(BaseModel):
    """Response wrapper for the live queue endpoint."""
    total: int
    items: List[SimulationQueueItem] = []


class SimulationHistoryResponse(BaseModel):
    """Response wrapper for the history endpoint."""
    total: int
    items: List[SimulationHistoryItem] = []


class TimeSeriesPoint(BaseModel):
    time: str
    count: int


class KeyValueCount(BaseModel):
    name: str
    count: int


class SimulationAnalyticsResponse(BaseModel):
    """Analytics dataset for charts."""
    requests_over_time: List[TimeSeriesPoint] = []
    type_distribution: List[KeyValueCount] = []
    provider_distribution: List[KeyValueCount] = []
    queue_trend: List[TimeSeriesPoint] = []


class KPICardsData(BaseModel):
    total_requests: int = 0
    active_requests: int = 0
    pending_requests: int = 0
    completed_requests: int = 0
    requests_per_minute: float = 0.0
    avg_processing_time_sec: float = 0.0
    total_providers: int = 0
    active_providers: int = 0


class AnalyticsChartsData(BaseModel):
    request_generation_trend: List[TimeSeriesPoint] = []
    request_type_distribution: List[KeyValueCount] = []
    provider_distribution: List[KeyValueCount] = []
    queue_size_trend: List[TimeSeriesPoint] = []
    completed_requests_trend: List[TimeSeriesPoint] = []


class RequestAnalyticsData(BaseModel):
    total_ride_requests: int = 0
    total_food_requests: int = 0
    total_parcel_requests: int = 0
    avg_estimated_distance_km: float = 0.0
    avg_estimated_travel_time_min: float = 0.0
    completion_rate_pct: float = 0.0
    pending_rate_pct: float = 0.0


class ProviderStatItem(BaseModel):
    provider_id: Optional[int] = None
    provider_name: str
    total_requests: int = 0
    completed_requests: int = 0
    pending_requests: int = 0
    utilization_pct: float = 0.0
    avg_distance_km: float = 0.0


class ProviderAnalyticsData(BaseModel):
    provider_stats: List[ProviderStatItem] = []
    most_active_provider: Optional[str] = "None"
    least_active_provider: Optional[str] = "None"


class TimeAnalyticsData(BaseModel):
    avg_queue_waiting_time_sec: float = 0.0
    avg_completion_time_sec: float = 0.0
    peak_request_hour: str = "N/A"
    hourly_distribution: List[KeyValueCount] = []
    daily_distribution: List[KeyValueCount] = []


class AdvancedAnalyticsResponse(BaseModel):
    kpi: KPICardsData
    charts: AnalyticsChartsData
    request_analytics: RequestAnalyticsData
    provider_analytics: ProviderAnalyticsData
    time_analytics: TimeAnalyticsData
    timestamp: str

