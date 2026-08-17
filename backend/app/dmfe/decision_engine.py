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
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.db.models import SimulationRequest, SystemConfig, Driver, Vehicle
from app.dmfe.models import DMFEBatch, DMFEAnalysisRun
from app.dmfe.batch_generator import BatchGenerator, CandidateGroup
from app.dmfe.compatibility import resolve_mode, _get_ai_rules, _get_threshold, get_config_value
from app.dmfe.driver_selection import (
    DriverCandidate,
    DriverPool,
    DriverSelector,
    _cached_selector_rules,
)
from app.dmfe.scoring import DEFAULT_WEIGHTS, unified_decision_score, UNIFIED_WEIGHTS
from app.dmfe.serializers import candidate_batch_dict
from app.engine.distance import haversine

logger = logging.getLogger(__name__)

# New config keys introduced by DMFE (seeded if absent, never overwrite)
DMFE_CONFIG_DEFAULTS: Dict[str, Dict[str, Any]] = {
    # Phase 9 — five configurable weights (CS = w1..w5)
    **{
        f"{factor}_weight": {"category": "ai_rules", "value": str(weight), "data_type": "float"}
        for factor, weight in DEFAULT_WEIGHTS.items()
    },
    # Phase 8 legacy keys (kept for config migration, no longer read)
    "destination_weight":   {"category": "ai_rules", "value": "0.20", "data_type": "float"},
    "route_overlap_weight": {"category": "ai_rules", "value": "0.20", "data_type": "float"},
    # A-DMFE — adaptive framework keys (seeded if absent)
    "admfe.mode":               {"category": "ai_rules", "value": "adaptive", "data_type": "string"},
    "admfe.base_bqs_threshold": {"category": "ai_rules", "value": "0.55", "data_type": "float"},
    "admfe.learning_enabled":   {"category": "ai_rules", "value": "true", "data_type": "bool"},
    "admfe.learning_max_bias":  {"category": "ai_rules", "value": "0.15", "data_type": "float"},
    "admfe.unified_scoring_enabled": {"category": "ai_rules", "value": "false", "data_type": "bool"},
    "traffic_multiplier":       {"category": "ai_rules", "value": "1.0", "data_type": "float"},
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "total_pending": self.total_pending,
            "total_pairs_evaluated": self.total_pairs_evaluated,
            "batches_created": self.batches_created,
            "rejected_count": self.rejected_count,
            "avg_compatibility_score": self.avg_compatibility_score,
            "threshold_used": self.threshold_used,
            "compatible_batches": self.compatible_batches,
            "rejected_batches": self.rejected_batches,
            "unmatched_request_ids": self.unmatched_request_ids,
        }


def _availability_gate(
    db: Session, 
    demand: int,
    cache: Optional[Dict[int, Tuple[bool, str]]] = None,
) -> Tuple[bool, str]:
    """
    Driver/vehicle availability check for ONE demand level (pure DB part of
    Gate E; the per-group weight check is applied by the caller).  Cached
    per demand level inside a run so the analysis loop does not repeat the
    driver/vehicle counts for every candidate group.
    """
    if cache is not None and demand in cache:
        return cache[demand]

    total_drivers = db.query(Driver).count()

    # If no drivers are seeded at all, skip the availability gate —
    # batch eligibility is determined by the 5-factor compatibility score.
    if total_drivers == 0:
        return True, "No drivers seeded — availability gate skipped"

    free_drivers = db.query(Driver).filter(Driver.status == "Available").count()
    if free_drivers == 0:
        return False, "No driver is currently Available (all busy)"

    total_vehicles = db.query(Vehicle).count()
    if total_vehicles == 0:
        return free_drivers > 0, "No vehicles seeded — vehicle gate skipped"

    free_vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.status == "Available", Vehicle.is_active.is_(True))
        .count()
    )
    if free_vehicles == 0:
        return False, "No vehicle is currently Available (all busy)"

    fitting_vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.status == "Available", Vehicle.is_active.is_(True))
        .filter(Vehicle.capacity >= demand)
        .count()
    )
    
    if fitting_vehicle == 0:
        res = False, (
            f"No Available vehicle with capacity ≥ {demand} "
            f"(largest free vehicle capacity is insufficient)"
        )
    else:
        res = True, "Availability checks passed (gate skipped)"

    if cache is not None:
        cache[demand] = res
    return res


def _estimate_fuel_co2(
    requests: List[SimulationRequest],
    candidate: DriverCandidate,
) -> Tuple[float, float]:
    """
    Dispatch-time fuel/CO₂ estimate for the selected (driver, vehicle) pair,
    computed from the same inputs the route optimizer uses:

        fuel = Σ(per-request trip km) / vehicle.mileage_kmpl
        CO₂   = fuel × 2.68 kg/L (petrol emission factor)

    Trip distance falls back to the pickup→drop haversine when the request
    has no distance estimate.  Labeled as an estimate in the decision text.
    """
    total_km = 0.0
    for r in requests:
        est = getattr(r, "estimated_distance_km", None) or 0.0
        if est and est > 0.0:
            total_km += float(est)
        else:
            total_km += haversine(
                r.pickup_lat, r.pickup_lng, r.drop_lat, r.drop_lng,
            )
    mileage = max(getattr(candidate.vehicle, "mileage_kmpl", None) or 0.0, 1.0)
    fuel_l = round(total_km / mileage, 2)
    return fuel_l, round(fuel_l * 2.68, 2)


def _driver_feasibility(
    db: Session,
    requests: List[SimulationRequest],
    rules: Dict[str, float],
    selector: Optional[DriverSelector] = None,
    driver_pool: Optional[DriverPool] = None,
    selector_rules: Optional[Dict[str, float]] = None,
    availability_cache: Optional[Dict[int, Tuple[bool, str]]] = None,
) -> Tuple[bool, str, Optional[DriverCandidate]]:
    """
    Gate E — exact driver feasibility for THIS group.

    Runs the real DriverSelector over the shared in-memory pool and returns
    (feasible, precise_reason, best_candidate).  The old aggregate count
    gate is only used as a fallback when no pool/selector is supplied.

    Failure reasons are always supported by the actual calculation:
    driver/vehicle counts, capacity vs combined demand, and the search
    radius of the pickups.
    """
    total_demand = sum(r.demand or 1 for r in requests)
    total_weight = sum(r.weight_kg or 0.0 for r in requests)
    max_weight = rules.get("max_weight_kg", 100.0)

    if total_weight > max_weight:
        return False, (
            f"Combined weight {total_weight:.1f} kg exceeds the "
            f"{max_weight:.0f} kg system limit"
        ), None

    if selector is None or driver_pool is None:
        ok, reason = _availability_gate(
            db, total_demand, cache=availability_cache
        )
        return ok, reason, None
    # Unseeded system — the gate is skipped so a missing seed cannot veto
    # compatibility-score decisions (legacy semantic preserved).
    if driver_pool.total_driver_count == 0:
        return True, "No drivers seeded — availability gate skipped", None
    if not driver_pool.drivers:
        return False, "No driver is currently Available (all busy)", None
    if driver_pool.total_vehicle_count == 0:
        return True, "No vehicles seeded — vehicle gate skipped", None
    if not driver_pool.vehicles:
        return False, "No vehicle is currently Available (all busy)", None
    fitting = driver_pool.fitting_vehicles(total_demand)
    if not fitting:
        return False, (
            f"No Available vehicle with capacity ≥ {total_demand} "
            f"(largest free vehicle capacity is insufficient)"
        ), None

    candidate = selector.select(
        db, requests, rules=selector_rules, pool=driver_pool,
    )
    if candidate is None:
        max_km = (selector_rules or {}).get("driver_max_search_km", 25.0)
        return False, (
            f"No feasible driver/vehicle pair within {max_km:.0f} km of the "
            f"pickups ({len(driver_pool.drivers)} Available driver(s), "
            f"{len(fitting)} fitting vehicle(s) checked)"
        ), None

    return True, (
        f"Driver #{candidate.driver.id} ({candidate.driver.name}) + vehicle "
        f"#{candidate.vehicle.id} ({candidate.vehicle.vehicle_type}, "
        f"capacity {candidate.vehicle.capacity}) feasible — ETA "
        f"{candidate.eta_min:.1f} min"
    ), candidate


def _accept_selection_reason(
    candidate: DriverCandidate,
    cg: CandidateGroup,
    rules: Dict[str, float],
) -> str:
    """
    One-line transparency record for an accepted decision: selected driver,
    score, ETA, capacity, expected delay, expected utilization, expected
    fuel & CO₂ impact, confidence.  Every number comes from the actual
    calculation (candidate scores, compatibility result, request distances).
    """
    fd = cg.result.factor_details
    fuel_l, co2_kg = _estimate_fuel_co2(cg.requests, candidate)
    weights = candidate.weights_used or {}
    w_sum = max(sum(weights.values()), 1e-9)
    confidence = max(0.0, min(candidate.total_score / w_sum, 1.0))
    return (
        f"✓ Driver #{candidate.driver.id} ({candidate.driver.name}) selected — "
        f"vehicle #{candidate.vehicle.id} ({candidate.vehicle.vehicle_type}, "
        f"capacity {candidate.vehicle.capacity}), ETA {candidate.eta_min:.1f} min, "
        f"driver score {candidate.total_score:.3f}, expected delay "
        f"{cg.result.estimated_delay_min:.1f} min, expected utilization "
        f"{float(fd.get('capacity_utilization_pct', 0.0)):.0f}%, "
        f"est. fuel {fuel_l:.2f} L, est. CO₂ {co2_kg:.2f} kg, "
        f"confidence {confidence * 100.0:.0f}%"
    )


def _has_available_driver(
    db: Session,
    requests: List[SimulationRequest],
    rules: Dict[str, float],
    availability_cache: Optional[Dict[int, Tuple[bool, str]]] = None,
    selector: Optional[DriverSelector] = None,
    driver_pool: Optional[DriverPool] = None,
    selector_rules: Optional[Dict[str, float]] = None,
) -> Tuple[bool, str]:
    """
    Gate E — Driver Availability (backwards-compatible wrapper).

    With a shared pool + selector this is the exact per-group feasibility
    probe; without them it falls back to the aggregate availability gate.
    The aggregate fallback is cached per demand level; the exact probe is
    in-memory and needs no caching.
    """
    total_demand = sum(r.demand or 1 for r in requests)
    total_weight = sum(r.weight_kg or 0.0 for r in requests)
    max_weight = rules.get("max_weight_kg", 100.0)

    # Weight-only check (always applies regardless of driver seed state)
    if total_weight > max_weight:
        return False, (
            f"Combined weight {total_weight:.1f} kg exceeds the "
            f"{max_weight:.0f} kg system limit"
        )

    if availability_cache is not None and total_demand in availability_cache:
        return availability_cache[total_demand]

    ok, reason, _candidate = _driver_feasibility(
        db, requests, rules, selector, driver_pool, selector_rules,
    )
    if availability_cache is not None:
        availability_cache[total_demand] = (ok, reason)
    return ok, reason



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


def _make_batch_row(
    batch_code: str,
    request_ids: List[int],
    compatibility_score: float,
    decision: str,
    reasons: List[str],
    factor_scores: Optional[Dict[str, Any]] = None,
    factor_details: Optional[Dict[str, Any]] = None,
    status: str = "Pending",
    estimated_delay_min: float = 0.0,
) -> DMFEBatch:
    """
    Build a DMFEBatch row with the standard JSON encoding used by both the
    analysis path and the dispatch pipeline (single source of truth).
    """
    return DMFEBatch(
        batch_code=batch_code,
        request_ids_json=json.dumps(request_ids),
        compatibility_score=compatibility_score,
        decision=decision,
        reason_json=json.dumps(reasons),
        factor_scores_json=json.dumps(factor_scores or {}),
        factor_details_json=json.dumps(factor_details or {}),
        status=status,
        estimated_delay_min=estimated_delay_min,
        predicted_utilization_pct=(factor_details or {}).get(
            "capacity_utilization_pct", 0.0
        ),
    )


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
        availability_cache: Optional[Dict[int, Tuple[bool, str]]] = None,
        selector: Optional[DriverSelector] = None,
        driver_pool: Optional[DriverPool] = None,
        selector_rules: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, str, List[str]]:
        """
        Phase 9 decision logic for one candidate group.

        Returns (decision, status, decision_reasons):
          ("Compatible", "Pending")    → Shared Trip (all gates pass)
          ("Incompatible", "Rejected") → Individual trip (a gate failed)
        """
        result = cg.result
        reasons = list(result.reasons)
        fs = result.factor_scores
        fd = result.factor_details
        
        # Add detailed evaluation logs
        pickup_dist_km = (fd.get("pickup_distance_m", 0) / 1000.0)
        time_diff_min = fd.get("time_diff_min", 0.0)
        
        reasons.append(f"ℹ️ Compatibility Score: {result.compatibility_score:.1f}%")
        reasons.append(f"ℹ️ Pickup Distance: {pickup_dist_km:.1f} km (Score: {fs.get('pickup', 0)*100:.1f}%)")
        reasons.append(f"ℹ️ Time Difference: {time_diff_min:.1f} min (Score: {fs.get('time', 0)*100:.1f}%)")
        reasons.append(f"ℹ️ Route Similarity Score: {fs.get('route', 0)*100:.1f}%")
        reasons.append(f"ℹ️ Capacity Score: {fs.get('capacity', 0)*100:.1f}%")

        # Gate A — weighted Compatibility Score >= configured threshold
        if result.compatibility_score < threshold:
            reasons.append(
                f"✗ Compatibility score {result.compatibility_score:.1f} "
                f"< threshold {threshold:.1f}"
            )
            logger.info("Group %s rejected: Score %s < %s", [r.id for r in cg.requests], result.compatibility_score, threshold)
            reasons.append("Final Decision: Rejected")
            return "Incompatible", "Rejected", reasons

        # A-DMFE — Batch Quality gate (additive; BQS is None in static mode)
        if result.batch_score is not None:
            bqs_thr = result.factor_details.get("admfe_bqs_threshold", 0.55)
            if result.batch_score < bqs_thr:
                reasons.append(
                    f"✗ Batch quality score {result.batch_score:.2f} "
                    f"< BQS threshold {bqs_thr:.2f} (poor utilisation/savings)"
                )
                logger.info(
                    "Group %s rejected: BQS %.3f < %.3f",
                    [r.id for r in cg.requests], result.batch_score, bqs_thr,
                )
                reasons.append("Final Decision: Rejected")
                return "Incompatible", "Rejected", reasons
            reasons.append(
                f"ℹ️ Batch Quality Score: {result.batch_score:.2f} "
                f"(θ_bqs {bqs_thr:.2f}) — quality gate passed"
            )
        if result.decision_confidence is not None:
            reasons.append(
                f"ℹ️ Decision Confidence: {result.decision_confidence:.1f}%"
            )

        # Gate B — Vehicle Capacity (factor score must be viable)
        if result.factor_scores.get("capacity", 0.0) <= 0.0:
            reasons.append("✗ Combined demand/weight exceeds vehicle capacity")
            logger.info("Group %s rejected: Capacity exceeded", [r.id for r in cg.requests])
            reasons.append("Final Decision: Rejected")
            return "Incompatible", "Rejected", reasons

        # Gate C — Time Compatibility (factor score must be within window)
        if result.factor_scores.get("time", 0.0) <= 0.0:
            reasons.append(
                f"✗ Request time gap exceeds {rules.get('max_allowed_delay_min', 20.0):.0f} min limit"
            )
            logger.info("Group %s rejected: Time gap exceeded", [r.id for r in cg.requests])
            reasons.append("Final Decision: Rejected")
            return "Incompatible", "Rejected", reasons

        # Gate D — Priority rules: High-priority requests must not be delayed
        if any((r.priority or "Medium") == "High" for r in cg.requests):
            delay_limit = rules.get("max_allowed_delay_min", 20.0)
            if result.estimated_delay_min > delay_limit:
                reasons.append(
                    f"✗ High-priority request delayed by {result.estimated_delay_min:.1f} "
                    f"min (limit {delay_limit:.0f} min)"
                )
                logger.info("Group %s rejected: High priority delayed", [r.id for r in cg.requests])
                reasons.append("Final Decision: Rejected")
                return "Incompatible", "Rejected", reasons

        # Gate E — Driver Availability (exact per-group feasibility probe)
        gate_e_ok, gate_e_reason, gate_e_candidate = _driver_feasibility(
            db, cg.requests, rules, selector, driver_pool, selector_rules,
            availability_cache=availability_cache,
        )
        reasons.append(f"ℹ️ Driver Availability: {gate_e_reason}")
        if not gate_e_ok:
            reasons.append(f"✗ {gate_e_reason}")
            logger.info("Group %s rejected: %s", [r.id for r in cg.requests], gate_e_reason)
            reasons.append("Final Decision: Rejected")
            return "Incompatible", "Rejected", reasons

        if gate_e_candidate is not None:
            # Phase 5: Unified Scoring
            fuel_l, co2_kg = _estimate_fuel_co2(cg.requests, gate_e_candidate)
            total_km = sum(getattr(r, "estimated_distance_km", None) or haversine(r.pickup_lat, r.pickup_lng, r.drop_lat, r.drop_lng) for r in cg.requests)
            cost = total_km * 1.5  # Simple cost heuristic
            
            unified_w = {k: rules.get(f"{k}_unified_weight", v) for k, v in UNIFIED_WEIGHTS.items()}
            
            unified_score, unified_factors = unified_decision_score(
                weights=unified_w,
                compatibility_pct=result.compatibility_score,
                driver_score=gate_e_candidate.total_score,
                cost=cost,
                fuel_l=fuel_l,
                co2_kg=co2_kg,
                delay_min=cg.result.estimated_delay_min
            )
            
            cg.result.factor_details["unified_score_pct"] = unified_score
            cg.result.factor_details["unified_factors"] = unified_factors
            cg.result.factor_details["unified_weights_used"] = unified_w
            
            use_unified = str(get_config_value(db, "admfe.unified_scoring_enabled", "false")).strip().lower() == "true"
            if use_unified:
                unified_threshold = rules.get("admfe.unified_threshold", 50.0)
                reasons.append(f"ℹ️ Unified Feasibility Score: {unified_score:.1f}% (θ_uni {unified_threshold:.1f}%)")
                if unified_score < unified_threshold:
                    reasons.append(f"✗ Unified score {unified_score:.1f} < threshold {unified_threshold:.1f}")
                    logger.info("Group %s rejected: Unified Score %s < %s", [r.id for r in cg.requests], unified_score, unified_threshold)
                    reasons.append("Final Decision: Rejected")
                    return "Incompatible", "Rejected", reasons
            else:
                # Still log it for transparency in legacy mode
                reasons.append(f"ℹ️ Unified Feasibility Score: {unified_score:.1f}% (evaluated passively)")
                
            reasons.append(_accept_selection_reason(gate_e_candidate, cg, rules))

        logger.info("Group %s accepted: Score %s >= %s", [r.id for r in cg.requests], result.compatibility_score, threshold)
        reasons.append("Final Decision: Compatible")
        return "Compatible", "Pending", reasons

    def run_analysis(self, db: Session) -> DMFEResult:
        """
        Full DMFE analysis pipeline (Phase 9 decision logic):
          0. Release stale trips to free drivers/vehicles.
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
        # Step 0 — Release stale trips (mirrors PipelineRunner.run step 0)
        from app.dmfe.driver_selection import complete_stale_trips
        released = complete_stale_trips(db, max_age_min=10.0)
        if released:
            logger.info("DMFE analysis pre-run: released %d stale trip(s)", released)

        _seed_dmfe_configs(db)
        threshold = _get_threshold(db)
        rules = _get_ai_rules(db)

        # The queue this run analyses.  Fetched BEFORE the context profile so
        # both are derived from the same requests: the profile used to be
        # built from a separate `id.asc()` query while the analysis ran on
        # `created_at.desc()`, so above 200 pending the adaptive threshold
        # came from a disjoint set of requests.
        pending: List[SimulationRequest] = (
            db.query(SimulationRequest)
            .filter(SimulationRequest.status == "Pending")
            .order_by(SimulationRequest.created_at.desc())
            .limit(200)            # cap for performance
            .all()
        )

        # A-DMFE: effective threshold (context-adjusted) in adaptive mode
        mode = resolve_mode(db)
        context_profile_dict = None
        if mode == "adaptive":
            from app.dmfe.adaptive.context import ContextAwarenessEngine
            from app.dmfe.adaptive.decision import effective_threshold

            context = ContextAwarenessEngine().build(db, pending)
            context_profile_dict = context.to_dict()
            threshold = effective_threshold(threshold, context)

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

        # Gate E pool — one grouped-query snapshot shared by every probe
        selector = DriverSelector()
        driver_pool = selector.build_pool(db)
        selector_rules = _cached_selector_rules(db)

        # Track which requests were matched into a candidate group;
        # the remainder are processed once as Individual Trips below.
        matched_ids = set()
        for cg in candidate_groups:
            for r in cg.requests:
                matched_ids.add(r.id)

        compatible_batches: List[Dict[str, Any]] = []
        rejected_batches: List[Dict[str, Any]] = []
        score_accumulator: List[float] = []
        availability_cache: Dict[int, Tuple[bool, str]] = {}
        run_batch_ids: List[int] = []

        for idx, cg in enumerate(candidate_groups, start=1):
            score = cg.result.compatibility_score
            score_accumulator.append(score)

            # Phase 9 decision gates → Shared Trip or Individual Trip
            decision, status, decision_reasons = self._evaluate_group(
                cg, rules, threshold, db,
                availability_cache=availability_cache,
                selector=selector,
                driver_pool=driver_pool,
                selector_rules=selector_rules,
            )
            is_shared = decision == "Compatible"
            batch_code = f"BATCH-{cg.requests[0].id:04d}-{cg.requests[-1].id:04d}"

            # Persist
            batch = _make_batch_row(
                batch_code=batch_code,
                request_ids=[r.id for r in cg.requests],
                compatibility_score=score,
                decision=decision,
                reasons=decision_reasons,
                factor_scores=cg.result.factor_scores,
                factor_details=cg.result.factor_details,
                status=status,
                estimated_delay_min=cg.result.estimated_delay_min,
            )
            db.add(batch)
            db.flush()  # get batch.id before commit
            run_batch_ids.append(batch.id)

            batch_dict = candidate_batch_dict(
                cg, batch_code,
                persisted=True,
                batch_id=batch.id,
                decision=decision,
                status=status,
            )

            if is_shared:
                compatible_batches.append(batch_dict)
            else:
                rejected_batches.append(batch_dict)

        # Phase 9 — persist Individual Trip rows for requests that could
        # not be batched (each request is processed exactly once per run).
        unmatched_ids = [r.id for r in pending if r.id not in matched_ids]
        for rid in unmatched_ids:
            batch = _make_batch_row(
                batch_code=f"TRIP-{rid:04d}",
                request_ids=[rid],
                compatibility_score=0.0,
                decision="Individual",
                reasons=["Solo trip — no compatible batch found"],
                status="Individual",
            )
            db.add(batch)
            db.flush()
            run_batch_ids.append(batch.id)
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

        # Back-fill analysis_run_id on only the batches created in this run
        # (a blanket NULL update would misattribute batches persisted by the
        # dispatch pipeline, which never sets analysis_run_id).
        if run_batch_ids:
            db.query(DMFEBatch).filter(DMFEBatch.id.in_(run_batch_ids)).update(
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
