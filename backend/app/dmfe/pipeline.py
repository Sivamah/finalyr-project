"""
DMFE Full Pipeline Runner — Phase 9 Core Engine
================================================
Orchestrates the complete DMFE dispatch chain:

    Incoming Requests
      → Compatibility Engine    (compatibility.py / scoring.py)
      → Batch Generator         (batch_generator.py)
      → Decision Engine         (decision_engine.py gates)
      → Route Optimizer         (optimizer.py, OR-Tools PDP)
      → Driver Selection        (driver_selection.py)
      → Trip Assignment         (driver_selection.py → Trip/Assignment)

This runner is the Programmatic/API entry point ("one-click dispatch").
The existing `/api/dmfe/analyze` endpoint (decision_engine.run_analysis)
remains the analysis-only path and is untouched.

Design rules:
  - Every pending request is processed exactly once per run.
  - A request is dispatched either in a Shared Trip or as an
    Individual Trip — never both, never skipped silently.
  - Unassignable trips are reported in the summary with reasons
    (requests keep status='Pending' for the next run).
  - All persistence happens through the engines; no direct table
    manipulation outside of the existing module contracts.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import SimulationRequest, DriverAssignment
from app.dmfe.batch_generator import BatchGenerator, CandidateGroup
from app.dmfe.decision_engine import _get_threshold
from app.dmfe.driver_selection import dispatch_trip, driver_selector
from app.dmfe.models import DMFEBatch
from app.dmfe.optimizer import _load_vrp_rules

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Structured output of one full pipeline run."""
    requests_processed: int = 0
    shared_trips: int = 0
    individual_trips: int = 0
    assignments_created: int = 0
    dispatches: List[Dict[str, Any]] = field(default_factory=list)
    unassigned: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_processed": self.requests_processed,
            "shared_trips": self.shared_trips,
            "individual_trips": self.individual_trips,
            "assignments_created": self.assignments_created,
            "dispatches": self.dispatches,
            "unassigned": self.unassigned,
        }


def _high_priority_violation(
    cg: CandidateGroup, rules: Dict[str, float]
) -> bool:
    """Gate D re-check: High-priority requests must not be delayed."""
    if not any((r.priority or "Medium") == "High" for r in cg.requests):
        return False
    return cg.result.estimated_delay_min > rules.get("max_allowed_delay_min", 20.0)


def _persist_batch(
    db: Session,
    batch_code: str,
    request_ids: List[int],
    score: float,
    decision: str,
    status: str,
    reasons: List[str],
    factor_scores: Optional[Dict] = None,
    delay_min: float = 0.0,
) -> DMFEBatch:
    """Persist a DMFEBatch row exactly like decision_engine does."""
    batch = DMFEBatch(
        batch_code=batch_code,
        request_ids_json=json.dumps(request_ids),
        compatibility_score=score,
        decision=decision,
        reason_json=json.dumps(reasons),
        factor_scores_json=json.dumps(factor_scores or {}),
        status=status,
        estimated_delay_min=delay_min,
    )
    db.add(batch)
    db.flush()
    return batch


class PipelineRunner:
    """
    Runs the complete DMFE pipeline on the pending queue.

    Usage:
        result = PipelineRunner().run(db, limit=200)
    """

    def __init__(self):
        self._generator = BatchGenerator()

    def run(self, db: Session, limit: int = 200) -> PipelineResult:
        pending: List[SimulationRequest] = (
            db.query(SimulationRequest)
            .filter(SimulationRequest.status == "Pending")
            .order_by(SimulationRequest.created_at.asc())
            .limit(max(1, min(limit, 500)))
            .all()
        )
        if not pending:
            return PipelineResult(
                requests_processed=0, shared_trips=0,
                individual_trips=0, assignments_created=0,
            )

        threshold = _get_threshold(db)
        rules = _load_vrp_rules(db)
        result = PipelineResult(requests_processed=len(pending))

        # ── 1+2. Compatibility + batching (gates A–C) ──────────────────────
        feasible = self._generator.create_feasible_batches(pending, db)

        covered_ids: Dict[int, str] = {}   # request_id → trip kind
        for cg in feasible:
            # Gate D — High-priority delay rule (same as decision_engine)
            if _high_priority_violation(cg, rules):
                for r in cg.requests:
                    covered_ids[r.id] = "high_priority_reject"
                continue
            for r in cg.requests:
                covered_ids[r.id] = "shared"

        # ── 4+5+6. Dispatch shared batches ──────────────────────────────────
        for cg in feasible:
            ids = {r.id for r in cg.requests}
            if any(covered_ids.get(i) != "shared" for i in ids):
                continue  # rejected by Gate D — handled as individuals

            batch_code = f"BATCH-{cg.requests[0].id:04d}-{cg.requests[-1].id:04d}"
            batch = _persist_batch(
                db, batch_code,
                [r.id for r in cg.requests],
                cg.result.compatibility_score,
                decision="Compatible", status="Pending",
                reasons=list(cg.result.reasons),
                factor_scores=cg.result.factor_scores,
                delay_min=cg.result.estimated_delay_min,
            )
            try:
                outcome = dispatch_trip(
                    db, cg.requests, batch=batch,
                    trip_key=batch_code,
                )
            except ValueError as exc:
                db.rollback()
                logger.warning("Shared trip %s not dispatched: %s", batch_code, exc)
                result.unassigned.append({
                    "batch_code": batch_code,
                    "request_ids": [r.id for r in cg.requests],
                    "kind": "shared",
                    "reason": str(exc),
                })
                continue

            result.shared_trips += 1
            result.assignments_created += 1
            result.dispatches.append(self._outcome_to_dict(outcome, batch_code))

        # ── 4+5+6. Dispatch individual trips ────────────────────────────────
        for req in pending:
            if req.id in covered_ids:
                continue
            batch = _persist_batch(
                db, f"TRIP-{req.id:04d}", [req.id],
                0.0, decision="Individual", status="Individual",
                reasons=["Solo trip — no compatible batch found"],
            )
            try:
                outcome = dispatch_trip(
                    db, [req], batch=batch, trip_key=f"TRIP-{req.id:04d}",
                )
            except ValueError as exc:
                db.rollback()
                logger.warning("Individual trip %s not dispatched: %s",
                               req.id, exc)
                result.unassigned.append({
                    "request_ids": [req.id],
                    "kind": "individual",
                    "reason": str(exc),
                })
                continue

            result.individual_trips += 1
            result.assignments_created += 1
            result.dispatches.append(
                self._outcome_to_dict(outcome, f"TRIP-{req.id:04d}")
            )

        db.commit()
        logger.info(
            "Pipeline run: %d requests → %d shared + %d individual trips, "
            "%d unassigned (threshold %.1f)",
            result.requests_processed, result.shared_trips,
            result.individual_trips, len(result.unassigned), threshold,
        )
        return result

    @staticmethod
    def _outcome_to_dict(outcome: Dict, label: str) -> Dict[str, Any]:
        trip = outcome["trip"]
        assignment = outcome["assignment"]
        return {
            "trip_code": trip.trip_code,
            "trip_id": trip.id,
            "assignment_id": assignment.id if assignment else None,
            "batch_id": trip.batch_id,
            "is_shared": trip.is_shared,
            "request_ids": [r.id for r in outcome["requests"]],
            "driver": {
                "id": outcome["driver"].id,
                "name": outcome["driver"].name,
            },
            "vehicle": {
                "id": outcome["vehicle"].id,
                "name": outcome["vehicle"].name,
                "vehicle_type": outcome["vehicle"].vehicle_type,
            },
            "candidate": outcome["candidate"].to_dict(),
            "route": outcome["route_dict"],
            "label": label,
        }


# Module-level singleton
pipeline_runner = PipelineRunner()
