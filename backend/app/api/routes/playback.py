from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.api.deps import SessionDep, CurrentUser
from app.schemas.playback import (
    ScenarioCreate, ScenarioResponse, SaveSimulationRequest,
    SavedSimulationResponse, PlaybackDashboardOverview, ScenarioComparisonResponse
)
from app.services.playback_service import playback_service

router = APIRouter(tags=["Simulation Playback & Scenario Testing"])


@router.get("/api/scenarios", response_model=List[ScenarioResponse])
def list_scenarios(db: SessionDep, current_user: CurrentUser):
    """List all scenario presets and custom scenarios."""
    return playback_service.get_scenarios(db)


@router.post("/api/scenarios", response_model=ScenarioResponse, status_code=201)
def create_custom_scenario(data: ScenarioCreate, db: SessionDep, current_user: CurrentUser):
    """Create a new custom simulation scenario."""
    return playback_service.create_scenario(db, data.model_dump())


@router.delete("/api/scenarios/{scenario_id}")
def delete_custom_scenario(scenario_id: int, db: SessionDep, current_user: CurrentUser):
    """Delete a custom scenario (presets cannot be deleted)."""
    success = playback_service.delete_scenario(db, scenario_id)
    if not success:
        raise HTTPException(400, "Cannot delete preset or scenario not found")
    return {"message": "Scenario deleted successfully"}


@router.get("/api/simulation/saved", response_model=List[SavedSimulationResponse])
def list_saved_simulations(
    db: SessionDep,
    current_user: CurrentUser,
    search: Optional[str] = None,
    scenario: Optional[str] = None,
    provider: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 100,
):
    """Get list of saved simulation runs with optional filtering."""
    return playback_service.get_saved_simulations(
        db,
        search=search,
        scenario=scenario,
        provider=provider,
        date=date,
        limit=limit,
    )


@router.get("/api/simulation/saved/dashboard", response_model=PlaybackDashboardOverview)
def get_playback_dashboard_overview(db: SessionDep, current_user: CurrentUser):
    """Get aggregate playback overview metrics (Saved Count, Best/Worst performing scenarios)."""
    return playback_service.get_dashboard_overview(db)


@router.post("/api/simulation/save-current", response_model=SavedSimulationResponse, status_code=201)
def save_current_simulation_run(
    data: SaveSimulationRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    """Snapshot and save current live simulation state into historical runs."""
    return playback_service.save_current_simulation_snapshot(
        db,
        name=data.name,
        scenario_name=data.scenario_name or "Standard Baseline Run",
    )


@router.get("/api/simulation/saved/{sim_id}", response_model=SavedSimulationResponse)
def get_saved_simulation(sim_id: int, db: SessionDep, current_user: CurrentUser):
    """Get detailed telemetry and replay timeline frames for a saved simulation run."""
    sim = playback_service.get_saved_simulation_by_id(db, sim_id)
    if not sim:
        raise HTTPException(404, "Saved simulation run not found")
    return sim


@router.delete("/api/simulation/saved/{sim_id}")
def delete_saved_simulation(sim_id: int, db: SessionDep, current_user: CurrentUser):
    """Delete a saved simulation run."""
    success = playback_service.delete_saved_simulation(db, sim_id)
    if not success:
        raise HTTPException(404, "Saved simulation run not found")
    return {"message": "Saved simulation run deleted"}


@router.get("/api/simulation/compare", response_model=ScenarioComparisonResponse)
def compare_simulations(
    sim_id_1: int,
    sim_id_2: int,
    db: SessionDep,
    current_user: CurrentUser,
):
    """Compare two saved simulation runs side-by-side."""
    res = playback_service.compare_simulations(db, sim_id_1, sim_id_2)
    if not res:
        raise HTTPException(400, "One or both simulation IDs to compare were not found")
    return res
