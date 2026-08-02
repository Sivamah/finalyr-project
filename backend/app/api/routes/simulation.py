"""
Simulation API Routes — Phase 2: Live Simulation & Monitoring Dashboard
========================================================================
Endpoints:
    POST  /start          — Start or resume request generator
    POST  /pause          — Pause request generator
    POST  /resume         — Resume request generator
    POST  /stop           — Stop request generator
    POST  /clear          — Wipe all requests from DB (pending + history)
    POST  /clear-queue    — Wipe only pending requests from DB
    POST  /clear-history  — Wipe only completed requests from DB
    GET   /status         — Engine state, runtime, RPM, category statistics
    GET   /queue          — Pending requests list (live queue)
    GET   /history        — Completed requests list
    GET   /analytics      — Real-time chart series data
"""

from fastapi import APIRouter
from app.api.deps import SessionDep, CurrentUser
from app.db.database import SessionLocal
from app.db.models import Provider
from typing import Optional
from app.schemas.simulation import (
    SimulationStatus,
    SimulationQueueItem,
    SimulationQueueResponse,
    SimulationHistoryItem,
    SimulationHistoryResponse,
    SimulationAnalyticsResponse,
    AdvancedAnalyticsResponse,
)
from app.services.simulation_service import simulation_engine

router = APIRouter()


def _provider_name_map(db, req_list) -> dict:
    ids = {r.provider_id for r in req_list if r.provider_id}
    if not ids:
        return {}
    rows = db.query(Provider.id, Provider.name).filter(Provider.id.in_(ids)).all()
    return {row.id: row.name for row in rows}


def _to_queue_item(req, provider_names: dict) -> SimulationQueueItem:
    speed_kmh = 25.0
    est_time = round((req.estimated_distance_km / speed_kmh) * 60, 1) if req.estimated_distance_km else 0.0
    return SimulationQueueItem(
        id=req.id,
        request_type=req.request_type,
        provider_id=req.provider_id,
        provider_name=provider_names.get(req.provider_id, "Unknown"),
        pickup_address=req.pickup_address or "",
        drop_address=req.drop_address or "",
        priority=req.priority or "Medium",
        estimated_distance_km=req.estimated_distance_km or 0.0,
        estimated_time_min=est_time,
        status=req.status or "Pending",
        created_at=req.created_at,
    )


def _to_history_item(req, provider_names: dict) -> SimulationHistoryItem:
    duration_sec = 0.0
    if req.request_timestamp and req.created_at:
        duration_sec = max(0.0, (req.created_at - req.request_timestamp).total_seconds())

    return SimulationHistoryItem(
        id=req.id,
        request_type=req.request_type,
        provider_id=req.provider_id,
        provider_name=provider_names.get(req.provider_id, "Unknown"),
        pickup_address=req.pickup_address or "",
        drop_address=req.drop_address or "",
        priority=req.priority or "Medium",
        estimated_distance_km=req.estimated_distance_km or 0.0,
        status=req.status or "Completed",
        completed_at=req.created_at,
        created_at=req.request_timestamp or req.created_at,
        processing_duration_sec=round(duration_sec, 1),
    )


def _build_status_response(db) -> SimulationStatus:
    snapshot = simulation_engine.get_status_snapshot()
    queue_size = simulation_engine.queue_manager.count_pending(db)
    history_size = simulation_engine.queue_manager.count_completed(db)
    breakdowns = simulation_engine.queue_manager.get_breakdown_metrics(db)

    return SimulationStatus(
        running=snapshot["running"],
        paused=snapshot["paused"],
        status_text=snapshot["status_text"],
        total_generated=snapshot["total_generated"],
        queue_size=queue_size,
        history_size=history_size,
        started_at=snapshot["started_at"],
        stopped_at=snapshot["stopped_at"],
        runtime_seconds=snapshot["runtime_seconds"],
        requests_per_minute=snapshot["requests_per_minute"],
        **breakdowns,
    )


@router.post("/start", response_model=SimulationStatus)
def start_simulation(db: SessionDep, current_user: CurrentUser):
    simulation_engine.start(db_factory=SessionLocal)
    return _build_status_response(db)


@router.post("/pause", response_model=SimulationStatus)
def pause_simulation(db: SessionDep, current_user: CurrentUser):
    simulation_engine.pause()
    return _build_status_response(db)


@router.post("/resume", response_model=SimulationStatus)
def resume_simulation(db: SessionDep, current_user: CurrentUser):
    simulation_engine.resume(db_factory=SessionLocal)
    return _build_status_response(db)


@router.post("/stop", response_model=SimulationStatus)
def stop_simulation(db: SessionDep, current_user: CurrentUser):
    simulation_engine.stop()
    return _build_status_response(db)


@router.post("/clear", response_model=SimulationStatus)
def clear_simulation(db: SessionDep, current_user: CurrentUser):
    simulation_engine.clear(db)
    return _build_status_response(db)


@router.post("/clear-queue", response_model=SimulationStatus)
def clear_simulation_queue(db: SessionDep, current_user: CurrentUser):
    simulation_engine.clear_queue_only(db)
    return _build_status_response(db)


@router.post("/clear-history", response_model=SimulationStatus)
def clear_simulation_history(db: SessionDep, current_user: CurrentUser):
    simulation_engine.clear_history_only(db)
    return _build_status_response(db)


@router.get("/status", response_model=SimulationStatus)
def get_simulation_status(db: SessionDep, current_user: CurrentUser):
    return _build_status_response(db)


@router.get("/queue", response_model=SimulationQueueResponse)
def get_simulation_queue(db: SessionDep, current_user: CurrentUser, limit: int = 200):
    reqs = simulation_engine.queue_manager.get_pending(db, limit=limit)
    provider_names = _provider_name_map(db, reqs)
    items = [_to_queue_item(r, provider_names) for r in reqs]
    return SimulationQueueResponse(total=len(items), items=items)


@router.get("/history", response_model=SimulationHistoryResponse)
def get_simulation_history(db: SessionDep, current_user: CurrentUser, limit: int = 200):
    reqs = simulation_engine.queue_manager.get_completed(db, limit=limit)
    provider_names = _provider_name_map(db, reqs)
    items = [_to_history_item(r, provider_names) for r in reqs]
    return SimulationHistoryResponse(total=len(items), items=items)


@router.get("/analytics", response_model=SimulationAnalyticsResponse)
def get_simulation_analytics(db: SessionDep, current_user: CurrentUser):
    data = simulation_engine.queue_manager.get_analytics(db)
    return SimulationAnalyticsResponse(**data)


@router.get("/advanced-analytics", response_model=AdvancedAnalyticsResponse)
def get_advanced_simulation_analytics(
    db: SessionDep,
    current_user: CurrentUser,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    request_type: Optional[str] = None,
    provider_id: Optional[int] = None,
    status: Optional[str] = None,
):
    data = simulation_engine.queue_manager.get_advanced_analytics(
        db,
        start_date=start_date,
        end_date=end_date,
        request_type=request_type,
        provider_id=provider_id,
        status=status,
    )
    return AdvancedAnalyticsResponse(**data)

