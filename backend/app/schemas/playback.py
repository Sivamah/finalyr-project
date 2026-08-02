from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    traffic_multiplier: float = 1.0
    demand_multiplier: float = 1.0
    weather_condition: str = "Clear"
    is_preset: bool = False


class ScenarioResponse(BaseModel):
    id: int
    name: str
    description: str = ""
    traffic_multiplier: float = 1.0
    demand_multiplier: float = 1.0
    weather_condition: str = "Clear"
    is_preset: bool = False

    class Config:
        from_attributes = True


class SaveSimulationRequest(BaseModel):
    name: str
    scenario_name: Optional[str] = "Standard Run"


class SavedSimulationResponse(BaseModel):
    id: int
    name: str
    scenario_name: str
    duration_seconds: float
    total_requests: int
    completed_requests: int
    completion_rate: float
    avg_waiting_time_sec: float
    provider_stats: Dict[str, Any] = {}
    queue_stats: Dict[str, Any] = {}
    events_timeline: List[Dict[str, Any]] = []
    created_at: str

    class Config:
        from_attributes = True


class PlaybackDashboardOverview(BaseModel):
    total_saved: int = 0
    recent_simulations_count: int = 0
    best_performing_scenario: str = "N/A"
    worst_performing_scenario: str = "N/A"


class ComparisonMetrics(BaseModel):
    total_requests: int
    completed_requests: int
    completion_rate: float
    queue_size: int
    avg_waiting_time_sec: float
    provider_usage: Dict[str, int]


class ScenarioComparisonResponse(BaseModel):
    simulation_1: SavedSimulationResponse
    simulation_2: SavedSimulationResponse
    delta_completion_rate: float
    delta_waiting_time_sec: float
    winner_simulation_id: int
