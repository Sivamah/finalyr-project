import json
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from sqlalchemy import func
from app.db.models import Dataset, SimulationRequest, Provider, Vehicle, OptimizationResult
from app.schemas.orchestration import OptimizationResultResponse, DatasetResponse
from app.api.deps import SessionDep, CurrentUser
from app.engine.optimizer import AIOrchestrator

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
        fd, file_path = tempfile.mkstemp(suffix=ext, dir="datasets")
        os.close(fd)
        content = file.file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        if file_type == "csv":
            row_count = len(content.decode().splitlines()) - 1
        elif file_type == "json":
            data = json.loads(content)
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


@router.post("/optimize", response_model=List[OptimizationResultResponse])
def run_optimization(db: SessionDep, current_user: CurrentUser):
    providers = db.query(Provider).filter(Provider.status == "Active").all()
    if not providers:
        raise HTTPException(400, "No active providers found. Create providers first.")

    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()
    if not vehicles:
        raise HTTPException(400, "No active vehicles found. Add vehicles to providers first.")

    orchestrator = AIOrchestrator(providers=providers, vehicles=vehicles, db=db)
    results = orchestrator.run()

    saved_results = []
    for r in results:
        result = OptimizationResult(
            request_count=r["request_count"],
            provider_id=r.get("provider_id"),
            vehicle_id=r.get("vehicle_id"),
            best_route_json=json.dumps(r.get("best_route", {})),
            chosen_provider=r["chosen_provider"],
            chosen_vehicle=r["chosen_vehicle"],
            estimated_cost=r["estimated_cost"],
            eta_mins=r["eta_mins"],
            fuel_saved_l=r["fuel_saved_l"],
            distance_saved_km=r["distance_saved_km"],
            co2_saved_kg=r["co2_saved_kg"],
            optimization_score=r["optimization_score"],
            explanation_json=json.dumps(r.get("explanation", {})),
        )
        db.add(result)
        saved_results.append(result)

    db.commit()
    for r in saved_results:
        db.refresh(r)
    return saved_results


@router.get("/results", response_model=List[OptimizationResultResponse])
def list_results(db: SessionDep, current_user: CurrentUser, limit: int = 50):
    return (
        db.query(OptimizationResult)
        .order_by(OptimizationResult.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/results/{result_id}", response_model=OptimizationResultResponse)
def get_result(result_id: int, db: SessionDep, current_user: CurrentUser):
    result = db.query(OptimizationResult).filter(OptimizationResult.id == result_id).first()
    if not result:
        raise HTTPException(404, "Result not found")
    return result


@router.post("/simulate")
def simulate_requests(db: SessionDep, current_user: CurrentUser, count: int = 10):
    from app.services.mock_adapters import generate_simulation_requests
    requests = generate_simulation_requests(count, db)
    return {"message": f"{len(requests)} simulation requests created"}


@router.get("/requests", response_model=List)
def list_requests(db: SessionDep, current_user: CurrentUser, limit: int = 50):
    reqs = (
        db.query(SimulationRequest)
        .order_by(SimulationRequest.created_at.desc())
        .limit(limit)
        .all()
    )
    return reqs
