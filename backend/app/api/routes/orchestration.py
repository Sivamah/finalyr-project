import json
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.core.json_utils import json_loads
from app.core.config import BACKEND_DIR
from app.db.models import Dataset, SimulationRequest, Trip
from app.schemas.orchestration import DatasetResponse
from app.api.deps import SessionDep, CurrentUser

# Provider, Vehicle, OptimizationResult, OptimizationResultResponse and
# AIOrchestrator were imported here for the legacy /optimize path. That path is
# retired (see run_optimization below) and the OptimizationResult table is no
# longer written or read, so the imports are dropped rather than left implying
# the path is still wired up.

router = APIRouter()


@router.get("/datasets", response_model=List[DatasetResponse])
def list_datasets(db: SessionDep, current_user: CurrentUser):
    return db.query(Dataset).order_by(Dataset.created_at.desc()).all()


@router.post("/datasets/upload", response_model=DatasetResponse)
def upload_dataset(
    name: str = Form(...),
    file_type: str = Form(...),
    data_type: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(None),
    db: SessionDep = None,
    current_user: CurrentUser = None,
):
    import tempfile, os
    row_count = 0
    file_path = None

    if file:
        ext = os.path.splitext(file.filename)[1] if file.filename else ""
        dataset_dir = os.path.join(BACKEND_DIR, "datasets")
        os.makedirs(dataset_dir, exist_ok=True)
        fd, file_path = tempfile.mkstemp(suffix=ext, dir=dataset_dir)
        os.close(fd)
        content = file.file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        if file_type == "csv":
            try:
                row_count = len(content.decode().splitlines()) - 1
            except UnicodeDecodeError:
                raise HTTPException(400, "CSV file must be UTF-8 text")
        elif file_type == "json":
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise HTTPException(400, "Invalid JSON file")
            row_count = len(data) if isinstance(data, list) else 1

    dataset = Dataset(
        name=name,
        file_type=file_type,
        data_type=data_type,
        file_path=file_path,
        row_count=row_count,
        description=description,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, db: SessionDep, current_user: CurrentUser):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    db.delete(dataset)
    db.commit()
    return {"message": "Dataset deleted"}


@router.post("/optimize")
def run_optimization(db: SessionDep, current_user: CurrentUser):
    """
    RETIRED — this endpoint ran the legacy AIOrchestrator (app/engine/optimizer.py),
    a second optimizer independent of A-DMFE.

    It was actively harmful, for two reasons:

      1. It selected EVERY request with status == "Pending" — not just the ones
         the caller had just simulated — and set them to status = "Optimized"
         (app/engine/optimizer.py::_mark_optimized). No other code in this
         codebase reads the value "Optimized", and the A-DMFE pipeline filters
         on status == "Pending", so each call silently and permanently removed
         the entire A-DMFE queue from the engine's reach.

      2. It wrote OptimizationResult rows, while GET /api/orchestration/results
         reads Trip rows. The page therefore displayed one entity type after
         Run and a different one after Refresh.

    The application now runs a single engine. Route optimisation is performed
    by POST /api/dmfe/analyze, whose output this page reads via
    GET /api/orchestration/results.

    The AIOrchestrator class is left in the tree unmodified for reference; it
    simply has no caller.
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "The legacy orchestrator has been retired — it consumed the A-DMFE "
            "pending queue. Use POST /api/dmfe/analyze instead; its results are "
            "served by GET /api/orchestration/results."
        ),
    )


def _trip_to_result(t: Trip) -> dict:
    """
    Serialize one A-DMFE Trip into the shape this page renders.

    Both GET /results and GET /results/{id} go through here. They used to read
    different tables — the list returned Trip rows while the detail route
    queried OptimizationResult by the SAME id — so opening any row looked up a
    trip id in an unrelated table.
    """
    request_ids = json_loads(t.request_ids_json, [])
    stop_order = json_loads(t.stop_order_json, [])
    return {
        "id": t.id,
        "batch_id": t.trip_code,
        "request_count": len(request_ids) if isinstance(request_ids, list) else 0,
        "provider_id": t.driver.provider_id if t.driver else None,
        "vehicle_id": t.vehicle_id,
        "best_route_json": {
            "distance_km": t.total_distance_km or 0.0,
            "duration_min": t.total_duration_min or 0.0,
            "stops": stop_order,
        },
        # Was hardcoded to the string "DMFE". Report the driver's actual
        # provider; fall back to the engine name only when unknown.
        "chosen_provider": (
            t.driver.provider.name
            if t.driver is not None and t.driver.provider is not None
            else "A-DMFE"
        ),
        "chosen_vehicle": t.vehicle.name if t.vehicle else "Unknown",
        "estimated_cost": t.estimated_cost or 0.0,
        "eta_mins": t.eta_min or 0.0,
        "fuel_saved_l": t.fuel_saved_l or 0.0,
        "distance_saved_km": t.distance_saved_km or 0.0,
        "co2_saved_kg": t.co2_saved_kg or 0.0,
        "optimization_score": t.optimization_score or 0.0,
        "explanation_json": {
            "status": t.status,
            "type": "shared" if t.is_shared else "individual",
            "trip_code": t.trip_code,
        },
        "created_at": t.created_at,
    }


@router.get("/results")
def list_results(db: SessionDep, current_user: CurrentUser, limit: int = 50):
    """Most recent A-DMFE trips, newest first."""
    trips = (
        db.query(Trip)
        .order_by(Trip.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_trip_to_result(t) for t in trips]


@router.get("/results/{result_id}")
def get_result(result_id: int, db: SessionDep, current_user: CurrentUser):
    """One A-DMFE trip, by the same id GET /results returns."""
    trip = db.query(Trip).filter(Trip.id == result_id).first()
    if not trip:
        raise HTTPException(404, "Result not found")
    return _trip_to_result(trip)


@router.post("/simulate")
def simulate_requests(db: SessionDep, current_user: CurrentUser, count: int = 10):
    from app.services.mock_adapters import generate_simulation_requests
    requests = generate_simulation_requests(count, db)
    return {"message": f"{len(requests)} simulation requests created"}


@router.get("/requests")
def list_requests(db: SessionDep, current_user: CurrentUser, limit: int = 50):
    reqs = (
        db.query(SimulationRequest)
        .order_by(SimulationRequest.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "request_type": r.request_type,
            "provider_id": r.provider_id,
            "pickup_lat": r.pickup_lat,
            "pickup_lng": r.pickup_lng,
            "drop_lat": r.drop_lat,
            "drop_lng": r.drop_lng,
            "pickup_address": r.pickup_address or "",
            "drop_address": r.drop_address or "",
            "demand": r.demand or 1,
            "weight_kg": r.weight_kg or 0.0,
            "priority": r.priority or "Medium",
            "vehicle_type": r.vehicle_type or "Auto",
            "estimated_distance_km": r.estimated_distance_km or 0.0,
            "status": r.status or "Pending",
            "created_at": r.created_at,
        }
        for r in reqs
    ]
