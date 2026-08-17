"""
DMFE Serializers
================
Single source of truth for the JSON payload shapes used by the DMFE API
routes (dmfe_engine, dmfe_v2) and the DecisionEngine analysis output.

Every serializer is a pure DB-object → dict mapper; the output shapes are
byte-identical to the historical inline definitions they replaced.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.json_utils import json_loads
from app.db.models import DriverAssignment, SimulationRequest, Trip

from app.dmfe.models import DMFEBatch, DMFEAnalysisRun

# ── Combined summary of a request (used by batch payloads) ────────────────


def request_summary(r) -> Dict[str, Any]:
    """6-key summary of one request inside a batch payload."""
    return {
        "id": r.id,
        "request_type": r.request_type,
        "pickup_address": r.pickup_address,
        "drop_address": r.drop_address,
        "priority": r.priority,
        "demand": r.demand,
    }


# ── Full request / trip / assignment serializers ──────────────────────────


def request_to_dict(r: SimulationRequest) -> Dict[str, Any]:
    return {
        "id": r.id,
        "request_type": r.request_type,
        "pickup_address": r.pickup_address,
        "drop_address": r.drop_address,
        "pickup_lat": r.pickup_lat,
        "pickup_lng": r.pickup_lng,
        "drop_lat": r.drop_lat,
        "drop_lng": r.drop_lng,
        "demand": r.demand,
        "weight_kg": r.weight_kg,
        "priority": r.priority,
        "vehicle_type": r.vehicle_type,
        "estimated_distance_km": r.estimated_distance_km,
        "status": r.status,
        "created_at": r.created_at.strftime("%Y-%m-%d %I:%M %p")
                     if r.created_at else "",
    }


def trip_to_dict(t: Trip) -> Dict[str, Any]:
    return {
        "id": t.id,
        "trip_code": t.trip_code,
        "batch_id": t.batch_id,
        "driver_id": t.driver_id,
        "vehicle_id": t.vehicle_id,
        "request_ids": json_loads(t.request_ids_json, []),
        "is_shared": t.is_shared,
        "status": t.status,
        "stop_order": json_loads(t.stop_order_json, []),
        "total_distance_km": t.total_distance_km,
        "total_duration_min": t.total_duration_min,
        "eta_min": t.eta_min,
        "fuel_l": t.fuel_l,
        "utilization_pct": t.utilization_pct,
        "max_delay_min": t.max_delay_min,
        "matrix_source": t.matrix_source,
        "estimated_cost": t.estimated_cost,
        "distance_saved_km": t.distance_saved_km,
        "fuel_saved_l": t.fuel_saved_l,
        "co2_saved_kg": t.co2_saved_kg,
        "optimization_score": t.optimization_score,
        "driver_name": t.driver.name if t.driver else None,
        "vehicle_name": t.vehicle.name if t.vehicle else None,
        "created_at": t.created_at.strftime("%Y-%m-%d %I:%M %p")
                     if t.created_at else "",
    }


def assignment_to_dict(a: DriverAssignment) -> Dict[str, Any]:
    return {
        "id": a.id,
        "trip_id": a.trip_id,
        "trip_code": a.trip.trip_code if a.trip else None,
        "driver_id": a.driver_id,
        "vehicle_id": a.vehicle_id,
        "driver_name": a.driver_name,
        "vehicle_name": a.vehicle_name,
        "assignment_type": a.assignment_type,
        "status": a.status,
        "assigned_at": a.assigned_at.strftime("%Y-%m-%d %I:%M %p")
                       if a.assigned_at else "",
    }


# ── Persisted DMFE records (analysis + batching) ──────────────────────────


def batch_requests_summary(db, request_ids: List[int]) -> List[Dict[str, Any]]:
    """Build the requests_summary for a persisted batch (7-key form)."""
    if db is None or not request_ids:
        return []
    from app.db.models import SimulationRequest as _Req

    rows = (
        db.query(_Req)
        .filter(_Req.id.in_(request_ids))
        .all()
    )
    by_id = {r.id: r for r in rows}
    summary: List[Dict[str, Any]] = []
    for rid in request_ids:
        r = by_id.get(rid)
        if r is not None:
            summary.append({
                **request_summary(r),
                "weight_kg": r.weight_kg,
            })
    return summary


def batch_to_dict(b: DMFEBatch, db: Optional[Any] = None, request_by_id: Optional[Dict[int, Any]] = None) -> Dict[str, Any]:
    request_ids = json_loads(b.request_ids_json, [])
    if request_by_id is not None:
        requests_summary = [
            {**request_summary(request_by_id[rid]), "weight_kg": request_by_id[rid].weight_kg}
            for rid in request_ids if rid in request_by_id
        ]
    else:
        requests_summary = batch_requests_summary(db, request_ids)
    return {
        "id": b.id,
        "batch_code": b.batch_code,
        "analysis_run_id": b.analysis_run_id,
        "request_ids": request_ids,
        "requests_summary": requests_summary,
        "compatibility_score": b.compatibility_score,
        "decision": b.decision,
        "reasons": json_loads(b.reason_json, []),
        "factor_scores": json_loads(b.factor_scores_json, {}),
        "factor_details": json_loads(getattr(b, "factor_details_json", None), {}),
        "status": b.status,
        "estimated_delay_min": b.estimated_delay_min,
        "created_at": b.created_at.strftime("%Y-%m-%d %I:%M %p") if b.created_at else "",
    }


def run_to_dict(r: DMFEAnalysisRun) -> Dict[str, Any]:
    return {
        "id": r.id,
        "total_pending": r.total_pending,
        "total_evaluated_pairs": r.total_evaluated_pairs,
        "batches_created": r.batches_created,
        "rejected_count": r.rejected_count,
        "avg_compatibility_score": r.avg_compatibility_score,
        "threshold_used": r.threshold_used,
        "run_at": r.run_at.strftime("%Y-%m-%d %I:%M %p") if r.run_at else "",
    }


# ── Candidate-group payloads (pairwise/feasible-batch responses) ────────────


def candidate_batch_dict(
    cg,
    batch_code: str,
    *,
    persisted: bool = False,
    batch_id: Optional[int] = None,
    decision: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Serialize one candidate group (batch payload)."""
    result = cg.result
    base = {
        "batch_code": batch_code,
        "request_ids": [r.id for r in cg.requests],
        "requests_summary": [request_summary(r) for r in cg.requests],
        "compatibility_score": result.compatibility_score,
        "factor_scores": result.factor_scores,
        "factor_details": result.factor_details,
        "reasons": result.reasons,
        "estimated_delay_min": result.estimated_delay_min,
        "weights_used": result.weights_used,
        "batch_score": result.batch_score,
        "decision_confidence": result.decision_confidence,
        "factor_contributions": result.factor_contributions,
        "extensions": result.extensions,
        "context_profile": result.context_profile,
        "mode": result.mode,
    }
    if not persisted:
        return base
    return {
        "id": batch_id,
        "batch_code": batch_code,
        "request_ids": base["request_ids"],
        "requests_summary": base["requests_summary"],
        "compatibility_score": base["compatibility_score"],
        "decision": decision,
        "reasons": base["reasons"],
        "factor_scores": base["factor_scores"],
        "factor_details": base["factor_details"],
        "status": status,
        "estimated_delay_min": base["estimated_delay_min"],
        "weights_used": base["weights_used"],
        "batch_score": base["batch_score"],
        "decision_confidence": base["decision_confidence"],
        "factor_contributions": base["factor_contributions"],
        "extensions": base["extensions"],
        "context_profile": base["context_profile"],
        "mode": base["mode"],
    }


def compatibility_score_response(result, threshold: float) -> Dict[str, Any]:
    """Payload for the /api/dmfe/compatibility-score endpoint."""
    return {
        "request_ids": result.request_ids,
        "compatibility_score": result.compatibility_score,
        "factor_scores": result.factor_scores,
        "factor_details": result.factor_details,
        "reasons": result.reasons,
        "estimated_delay_min": result.estimated_delay_min,
        "weights_used": result.weights_used,
        "threshold": threshold,
        "decision": "Compatible" if result.compatibility_score >= threshold
                    else "Individual",
        "batch_score": result.batch_score,
        "decision_confidence": result.decision_confidence,
        "factor_contributions": result.factor_contributions,
        "extensions": result.extensions,
        "context_profile": result.context_profile,
        "mode": result.mode,
    }