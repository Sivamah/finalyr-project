from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import Provider, Vehicle, SimulationRequest, OptimizationResult
from app.engine.optimizer import AIOrchestrator


def run_orchestration(db: Session) -> List[OptimizationResult]:
    providers = db.query(Provider).filter(Provider.status == "Active").all()
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()

    orchestrator = AIOrchestrator(providers=providers, vehicles=vehicles, db=db)
    results = orchestrator.run()

    saved_results = []
    for r in results:
        import json
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
