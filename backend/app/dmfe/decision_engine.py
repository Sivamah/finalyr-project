"""
DMFE Decision Engine — Phase 9 Core Engine
===========================================
Applies the Phase 9 decision logic to each CandidateGroup using the new
weighted Compatibility Score (5 factors) and additional feasibility gates:

    Gate A — Compatibility Score >= configured threshold   → Shared Trip
    Gate B — Vehicle capacity is sufficient
    Gate C — Time compatibility is acceptable
    Gate D — Priority rules (High-priority must not be delayed)
    Gate E — Driver availability (free driver + fitting vehicle)

If ALL gates pass the group is persisted as a Shared Trip
(decision="Compatible", status="Pending").  Otherwise the requests are
dispatched as Individual Trips (persisted with decision="Incompatible"
or as per-request rows with decision="Individual").

Also persists DMFEBatch and DMFEAnalysisRun records, and seeds missing
weight/threshold config keys if they don't yet exist in SystemConfig.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.models import SimulationRequest, SystemConfig, Driver, Vehicle
from app.dmfe.models import DMFEBatch, DMFEAnalysisRun
from app.dmfe.batch_generator import (
    BatchGenerator,
    CandidateGroup,
    _get_ai_rules,
)

logger = logging.getLogger(__name__)

# New config keys introduced by DMFE (seeded if absent, never overwrite)
DMFE_CONFIG_DEFAULTS: Dict[str, Dict[str, Any]] = {
    # Phase 9 — five configurable weights (CS = w1..w5)
    "pickup_weight":    {"category": "ai_rules", "value": "0.30", "data_type": "float"},
    "route_weight":     {"category": "ai_rules", "value": "0.25", "data_type": "float"},
    "time_weight":      {"category": "ai_rules", "value": "0.20", "data_type": "float"},
    "capacity_weight":  {"category": "ai_rules", "value": "0.15", "data_type": "float"},
    "priority_weight":  {"category": "ai_rules", "value": "0.10", "data_type": "float"},
    # Phase 8 legacy keys (kept for config migration, no longer read)
    "destination_weight":   {"category": "ai_rules", "value": "0.20", "data_type": "float"},
    "route_overlap_weight": {"category": "ai_rules", "value": "0.20", "data_type": "float"},
}


@dataclass
class DMFEResult:
    """Full output of one analysis run."""
    run_id: int
    total_pending: int
    total_pairs_evaluated: int
    batches_created: int
    rejected_count: int
    avg_compatibility_score: float
    threshold_used: float
    compatible_batches: List[Dict[str, Any]] = field(default_factory=list)
    rejected_batches: List[Dict[str, Any]] = field(default_factory=list)
    unmatched_request_ids: List[int] = field(default_factory=list)


def _get_threshold(db: Session) -> float:
    row = db.query(SystemConfig).filter(SystemConfig.key == "min_compatibility_score").first()
    if row:
        try:
            return float(row.value)
        except (ValueError, TypeError):
            pass
    return 70.0


def _has_available_driver(
    db: Session,
    requests: List[SimulationRequest],
    rules: Dict[str, float],
) -> bool:
    """
    Gate E — Driver Availability.

    A shared trip is only feasible if, at decision time, at least one
    driver is Available AND at least one Available active vehicle can
    carry the combined demand and weight of the group.

    IMPORTANT: If the driver table is empty (fresh install / unseeded system)
    this gate is bypassed so that compatibility-score decisions are not
    silently vetoed by a missing seed.  The gate only blocks when drivers
    exist in the system but none are currently free.
    """
    total_demand = sum(r.demand or 1 for r in requests)
    total_weight = sum(r.weight_kg or 0.0 for r in requests)
    max_weight = rules.get("max_weight_kg", 100.0)

    # Weight-only check (always applies regardless of driver seed state)
    if total_weight > max_weight:
        return False

    total_drivers = db.query(Driver).count()

    # If no drivers are seeded at all, skip the availability gate —
    # batch eligibility is determined by the 5-factor compatibility score.
    if total_drivers == 0:
        return True

    any_driver_free = (
        db.query(Driver).filter(Driver.status == "Available").count() > 0
    )

    total_vehicles = db.query(Vehicle).count()
    if total_vehicles == 0:
        # No vehicles seeded — skip vehicle capacity gate
        return any_driver_free

    fitting_vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.status == "Available", Vehicle.is_active.is_(True))
        .filter(Vehicle.capacity >= total_demand)
        .count() > 0
    )

    return any_driver_free and fitting_vehicle



def _seed_dmfe_configs(db: Session) -> None:
    """Seed DMFE-specific config keys that may not yet exist in SystemConfig."""
    try:
        existing = {c.key for c in db.query(SystemConfig).all()}
        for key, info in DMFE_CONFIG_DEFAULTS.items():
            if key not in existing:
                db.add(SystemConfig(
                    category=info["category"],
                    key=key,
                    value=info["value"],
                    data_type=info["data_type"],
                ))
        db.commit()
    except Exception as exc:
        logger.warning("_seed_dmfe_configs error: %s", exc)
        db.rollback()


def _batch_to_dict(batch: DMFEBatch) -> Dict[str, Any]:
    return {
        "id": batch.id,
        "batch_code": batch.batch_code,
        "analysis_run_id": batch.analysis_run_id,
        "request_ids": json.loads(batch.request_ids_json or "[]"),
        "compatibility_score": batch.compatibility_score,
        "decision": batch.decision,
        "reasons": json.loads(batch.reason_json or "[]"),
        "factor_scores": json.loads(batch.factor_scores_json or "{}"),
        "status": batch.status,
        "estimated_delay_min": batch.estimated_delay_min,
        "created_at": batch.created_at.strftime("%Y-%m-%d %I:%M %p")
                      if batch.created_at else "",
    }


class DecisionEngine:
    """
    Applies the compatibility threshold to each CandidateGroup,
    persists results, and returns a structured DMFEResult.
    """

    def __init__(self):
        self._generator = BatchGenerator()

    def _evaluate_group(
        self,
        cg: CandidateGroup,
        rules: Dict[str, float],
        threshold: float,
        db: Session,
    ) -> Tuple[str, str, List[str]]:
        """
        Phase 9 decision logic for one candidate group.

        Returns (decision, status, decision_reasons):
          ("Compatible", "Pending")    → Shared Trip (all gates pass)
          ("Incompatible", "Rejected") → Individual trip (a gate failed)
        """
        result = cg.result
        reasons = list(result.reasons)

        # Gate A — weighted Compatibility Score >= configured threshold
        if result.compatibility_score < threshold:
            reasons.append(
                f"✗ Compatibility score {result.compatibility_score:.1f} "
                f"< threshold {threshold:.1f}"
            )
            return "Incompatible", "Rejected", reasons

        # Gate B — Vehicle Capacity (factor score must be viable)
        if result.factor_scores.get("capacity", 0.0) <= 0.0:
            reasons.append("✗ Combined demand/weight exceeds vehicle capacity")
            return "Incompatible", "Rejected", reasons

        # Gate C — Time Compatibility (factor score must be within window)
        if result.factor_scores.get("time", 0.0) <= 0.0:
            reasons.append(
                f"✗ Request time gap exceeds {rules['max_allowed_delay_min']:.0f} min limit"
            )
            return "Incompatible", "Rejected", reasons

        # Gate D — Priority rules: High-priority requests must not be delayed
        if any((r.priority or "Medium") == "High" for r in cg.requests):
            delay_limit = rules.get("max_allowed_delay_min", 20.0)
            if result.estimated_delay_min > delay_limit:
                reasons.append(
                    f"✗ High-priority request delayed by {result.estimated_delay_min:.1f} "
                    f"min (limit {delay_limit:.0f} min)"
                )
                return "Incompatible", "Rejected", reasons

        # Gate E — Driver Availability (free driver + fitting vehicle)
        if not _has_available_driver(db, cg.requests, rules):
            reasons.append("✗ No available driver with sufficient vehicle capacity")
            return "Incompatible", "Rejected", reasons

        return "Compatible", "Pending", reasons

    def run_analysis(self, db: Session) -> DMFEResult:
        """
        Full DMFE analysis pipeline (Phase 9 decision logic):
          1. Seed any missing config keys (weights, threshold, limits).
          2. Load all pending requests (status='Pending').
          3. Generate candidate groups (BatchGenerator).
          4. Apply the Phase 9 decision gates per group:
               CS >= threshold + capacity + time + priority + driver
               availability → Shared Trip | otherwise → Individual Trip.
          5. Persist DMFEBatch rows (Compatible / Incompatible / Individual)
             and one DMFEAnalysisRun summary.
          6. Return DMFEResult (response shape unchanged).
        """
        _seed_dmfe_configs(db)
        threshold = _get_threshold(db)
        rules = _get_ai_rules(db)

        pending: List[SimulationRequest] = (
            db.query(SimulationRequest)
            .filter(SimulationRequest.status == "Pending")
            .order_by(SimulationRequest.created_at.desc())
            .limit(200)            # cap for performance
            .all()
        )

        if not pending:
            # Persist empty analysis run
            run = DMFEAnalysisRun(
                total_pending=0, total_evaluated_pairs=0,
                batches_created=0, rejected_count=0,
                avg_compatibility_score=0.0, threshold_used=threshold,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            return DMFEResult(
                run_id=run.id, total_pending=0, total_pairs_evaluated=0,
                batches_created=0, rejected_count=0,
                avg_compatibility_score=0.0, threshold_used=threshold,
            )

        candidate_groups: List[CandidateGroup] = self._generator.generate_candidates(
            pending, db
        )

        # Track which requests were matched into a candidate group;
        # the remainder are processed once as Individual Trips below.
        matched_ids = set()
        for cg in candidate_groups:
            for r in cg.requests:
                matched_ids.add(r.id)

        compatible_batches: List[Dict[str, Any]] = []
        rejected_batches: List[Dict[str, Any]] = []
        score_accumulator: List[float] = []

        for idx, cg in enumerate(candidate_groups, start=1):
            score = cg.result.compatibility_score
            score_accumulator.append(score)

            # Phase 9 decision gates → Shared Trip or Individual Trip
            decision, status, decision_reasons = self._evaluate_group(
                cg, rules, threshold, db
            )
            is_shared = decision == "Compatible"
            batch_code = f"BATCH-{cg.requests[0].id:04d}-{cg.requests[-1].id:04d}"

            # Persist
            batch = DMFEBatch(
                batch_code=batch_code,
                request_ids_json=json.dumps([r.id for r in cg.requests]),
                compatibility_score=score,
                decision=decision,
                reason_json=json.dumps(decision_reasons),
                factor_scores_json=json.dumps(cg.result.factor_scores),
                status=status,
                estimated_delay_min=cg.result.estimated_delay_min,
            )
            db.add(batch)
            db.flush()  # get batch.id before commit

            batch_dict = {
                "id": batch.id,
                "batch_code": batch_code,
                "request_ids": [r.id for r in cg.requests],
                "requests_summary": [
                    {
                        "id": r.id,
                        "request_type": r.request_type,
                        "pickup_address": r.pickup_address,
                        "drop_address": r.drop_address,
                        "priority": r.priority,
                        "demand": r.demand,
                    }
                    for r in cg.requests
                ],
                "compatibility_score": score,
                "decision": decision,
                "reasons": decision_reasons,
                "factor_scores": cg.result.factor_scores,
                "factor_details": cg.result.factor_details,
                "status": status,
                "estimated_delay_min": cg.result.estimated_delay_min,
                "weights_used": cg.result.weights_used,
            }

            if is_shared:
                compatible_batches.append(batch_dict)
            else:
                rejected_batches.append(batch_dict)

        # Phase 9 — persist Individual Trip rows for requests that could
        # not be batched (each request is processed exactly once per run).
        unmatched_ids = [r.id for r in pending if r.id not in matched_ids]
        for rid in unmatched_ids:
            db.add(DMFEBatch(
                batch_code=f"TRIP-{rid:04d}",
                request_ids_json=json.dumps([rid]),
                compatibility_score=0.0,
                decision="Individual",
                reason_json=json.dumps(["Solo trip — no compatible batch found"]),
                factor_scores_json="{}",
                status="Individual",
                estimated_delay_min=0.0,
            ))
        db.flush()

        avg_score = round(
            sum(score_accumulator) / len(score_accumulator), 1
        ) if score_accumulator else 0.0

        # Persist analysis run summary
        run = DMFEAnalysisRun(
            total_pending=len(pending),
            total_evaluated_pairs=len(candidate_groups),
            batches_created=len(compatible_batches),
            rejected_count=len(rejected_batches),
            avg_compatibility_score=avg_score,
            threshold_used=threshold,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Back-fill analysis_run_id on all batches created in this run
        db.query(DMFEBatch).filter(DMFEBatch.analysis_run_id.is_(None)).update(
            {"analysis_run_id": run.id}
        )
        db.commit()

        logger.info(
            "DMFE run #%d: %d pending → %d evaluated → %d compatible, %d rejected",
            run.id, len(pending), len(candidate_groups),
            len(compatible_batches), len(rejected_batches),
        )

        return DMFEResult(
            run_id=run.id,
            total_pending=len(pending),
            total_pairs_evaluated=len(candidate_groups),
            batches_created=len(compatible_batches),
            rejected_count=len(rejected_batches),
            avg_compatibility_score=avg_score,
            threshold_used=threshold,
            compatible_batches=compatible_batches,
            rejected_batches=rejected_batches,
            unmatched_request_ids=unmatched_ids,
        )


# Module-level singleton
decision_engine = DecisionEngine()
