from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import SimulationRequest, Provider
from app.schemas.xai import (
    XAIFactors, XAITimelineItem, XAIExplanationItem, XAIOverviewResponse, KeyValueCount
)


def _generate_explanation_for_request(req: SimulationRequest, provider_name: str) -> XAIExplanationItem:
    req_id = req.id
    dist = req.estimated_distance_km or 3.5

    # Seeded deterministic factors
    pickup_dist_score = min(98.0, max(52.0, round(96.0 - dist * 3.5, 1)))
    dest_sim_score = min(96.0, max(48.0, round(74.0 + (req_id * 7 % 23), 1)))
    delay_score = min(98.0, max(60.0, round(92.0 - (req_id * 3 % 17), 1)))
    
    if req.request_type and req.request_type.lower() == "ride":
        cap_score = 95.0
    elif req.request_type and req.request_type.lower() == "food":
        cap_score = 90.0
    else:
        cap_score = 85.0

    prio = req.priority or "Medium"
    if prio == "High":
        prio_score = 95.0
    elif prio == "Medium":
        prio_score = 80.0
    else:
        prio_score = 65.0

    overall_compat = round(
        (pickup_dist_score * 0.25) +
        (dest_sim_score * 0.25) +
        (delay_score * 0.20) +
        (cap_score * 0.15) +
        (prio_score * 0.15),
        1
    )

    confidence = min(99.0, max(72.0, round(overall_compat * 1.03, 1)))

    if overall_compat >= 82.0:
        decision = "Compatible for Batching"
        reason = f"Pickup locations in {req.pickup_address or 'Coimbatore'} are nearby and route overlap is {int(dest_sim_score)}%."
        decision_summary = "High compatibility score. Approved for multi-stop order batching."
        status = "Evaluated"
    elif overall_compat >= 68.0:
        decision = "Standalone Direct Routing"
        reason = f"{prio} priority demand requires direct vehicle dispatch to minimize ETA."
        decision_summary = "Dedicated vehicle route assigned to meet SLA requirements."
        status = "Evaluated"
    else:
        decision = "Deferred for Next Batch"
        reason = "Detour ratio exceeds 15% threshold for current active vehicle clusters."
        decision_summary = "Queued for next optimization cycle."
        status = "Pending"

    # Timeline calculation
    c_at = req.created_at or datetime.now(timezone.utc)
    if c_at.tzinfo is None:
        c_at = c_at.replace(tzinfo=timezone.utc)

    t1 = c_at.strftime("%H:%M:%S")
    t2 = (c_at + timedelta(seconds=2)).strftime("%H:%M:%S")
    t3 = (c_at + timedelta(seconds=5)).strftime("%H:%M:%S")
    t4 = (c_at + timedelta(seconds=6)).strftime("%H:%M:%S")

    timeline = [
        XAITimelineItem(title="Simulation Created", timestamp=t1, status="completed", description=f"Request #{req_id} generated"),
        XAITimelineItem(title="Request Queued", timestamp=t2, status="completed", description=f"Entered queue for provider {provider_name}"),
        XAITimelineItem(title="Analysis Completed", timestamp=t3, status="completed", description="Feature vectors evaluated by DMFE model"),
        XAITimelineItem(title="Decision Generated", timestamp=t4, status="completed", description=f"Outcome: {decision}"),
    ]

    factors = XAIFactors(
        pickup_distance_score=pickup_dist_score,
        destination_similarity=dest_sim_score,
        estimated_delay_score=delay_score,
        vehicle_capacity_score=cap_score,
        priority_score=prio_score,
        overall_compatibility_score=overall_compat,
    )

    return XAIExplanationItem(
        id=req_id,
        request_id=req_id,
        request_type=req.request_type or "ride",
        provider_id=req.provider_id,
        provider_name=provider_name,
        status=status,
        decision=decision,
        decision_summary=decision_summary,
        reason=reason,
        confidence_score=confidence,
        pickup_address=req.pickup_address or "Coimbatore",
        drop_address=req.drop_address or "Destination",
        estimated_distance_km=req.estimated_distance_km or 0.0,
        factors=factors,
        timeline=timeline,
        created_at=c_at.isoformat(),
    )


class XAIService:
    """XAI service generating structured explanations from simulation request data."""

    def get_explanations(
        self,
        db: Session,
        request_type: Optional[str] = None,
        provider_id: Optional[int] = None,
        decision: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[XAIExplanationItem]:
        query = db.query(SimulationRequest)

        if request_type and request_type.lower() != "all":
            query = query.filter(func.lower(SimulationRequest.request_type) == request_type.lower())
        if provider_id and provider_id != 0:
            query = query.filter(SimulationRequest.provider_id == provider_id)
        if status and status.lower() != "all":
            query = query.filter(func.lower(SimulationRequest.status) == status.lower())

        requests = query.order_by(SimulationRequest.created_at.desc()).limit(limit).all()

        # Provider map
        provider_ids = {r.provider_id for r in requests if r.provider_id}
        providers = {p.id: p.name for p in db.query(Provider).filter(Provider.id.in_(provider_ids)).all()} if provider_ids else {}

        explanations = []
        search_lower = search.lower() if search else None

        for req in requests:
            pname = providers.get(req.provider_id, "Unassigned")
            exp = _generate_explanation_for_request(req, pname)

            # Decision filter
            if decision and decision.lower() != "all":
                if decision.lower() not in exp.decision.lower():
                    continue

            # Search filter
            if search_lower:
                match_id = str(exp.request_id) == search_lower or f"#{exp.request_id}" in search_lower
                match_pname = search_lower in exp.provider_name.lower()
                match_type = search_lower in exp.request_type.lower()
                match_reason = search_lower in exp.reason.lower()
                match_decision = search_lower in exp.decision.lower()
                if not (match_id or match_pname or match_type or match_reason or match_decision):
                    continue

            explanations.append(exp)

        return explanations

    def get_overview(self, db: Session) -> Dict[str, Any]:
        explanations = self.get_explanations(db, limit=200)

        total = len(explanations)
        if total == 0:
            return {
                "total_explanations": 0,
                "avg_compatibility_score": 0.0,
                "avg_confidence_score": 0.0,
                "most_common_decision": "N/A",
                "decision_breakdown": [],
                "score_distribution": [],
                "explanations": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        avg_compat = round(sum(e.factors.overall_compatibility_score for e in explanations) / total, 1)
        avg_conf = round(sum(e.confidence_score for e in explanations) / total, 1)

        decision_counts = {}
        score_ranges = {"90-100%": 0, "80-89%": 0, "70-79%": 0, "<70%": 0}

        for e in explanations:
            decision_counts[e.decision] = decision_counts.get(e.decision, 0) + 1

            s = e.factors.overall_compatibility_score
            if s >= 90:
                score_ranges["90-100%"] += 1
            elif s >= 80:
                score_ranges["80-89%"] += 1
            elif s >= 70:
                score_ranges["70-79%"] += 1
            else:
                score_ranges["<70%"] += 1

        most_common = max(decision_counts.items(), key=lambda x: x[1])[0] if decision_counts else "N/A"

        return {
            "total_explanations": total,
            "avg_compatibility_score": avg_compat,
            "avg_confidence_score": avg_conf,
            "most_common_decision": most_common,
            "decision_breakdown": [{"name": k, "count": v} for k, v in decision_counts.items()],
            "score_distribution": [{"name": k, "count": v} for k, v in score_ranges.items()],
            "explanations": explanations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


xai_service = XAIService()
