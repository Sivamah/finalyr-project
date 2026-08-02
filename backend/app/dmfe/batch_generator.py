"""
DMFE Batch Generator — Phase 9 Core Engine
===========================================
Generates candidate batch groups from a list of pending SimulationRequests
and creates feasible batches from the weighted Compatibility Score
produced by CompatibilityCalculator.

Phase 8 (unchanged contract):
  generate_candidates() — all pairwise candidates within radius, sorted by
  compatibility score, greedy disjoint assignment.  Returns both compatible
  and incompatible groups; DecisionEngine (/analyze) applies the threshold
  and persists Compatible / Rejected records.

Phase 9 (new):
  create_feasible_batches() — production batching with three gates:

      1. Compatibility Score >= configured threshold (min_compatibility_score)
      2. Vehicle capacity is sufficient (demand & weight within limits)
      3. Time compatibility is acceptable (within max_allowed_delay_min)

  Cheap pre-checks (time, radius, capacity) run BEFORE the full 5-factor
  evaluation to avoid unnecessary pairwise computations.

No routing, no OR-Tools, no vehicle assignment.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Set, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import SimulationRequest, SystemConfig
from app.engine.distance import haversine
from app.dmfe.compatibility import CompatibilityCalculator, CompatibilityResult

logger = logging.getLogger(__name__)


@dataclass
class CandidateGroup:
    """A proposed batch of 2–3 requests with its compatibility evaluation."""
    requests: List[SimulationRequest]
    result: CompatibilityResult


def _get_max_radius(db: Session) -> float:
    row = db.query(SystemConfig).filter(SystemConfig.key == "max_pickup_radius_km").first()
    if row:
        try:
            return float(row.value)
        except (ValueError, TypeError):
            pass
    return 5.0


def _get_threshold(db: Session) -> float:
    """
    Read the batching threshold from SystemConfig (min_compatibility_score).
    Same config key used by DecisionEngine.  Defaults to 70.0.
    """
    row = db.query(SystemConfig).filter(SystemConfig.key == "min_compatibility_score").first()
    if row:
        try:
            return float(row.value)
        except (ValueError, TypeError):
            pass
    return 70.0


def _get_ai_rules(db: Session) -> Dict[str, float]:
    """
    Load the numeric batching limits from SystemConfig.
    Keys are identical to the ones read by CompatibilityCalculator so the
    pre-checks here and the factor scores computed there always agree.
    """
    rules: Dict[str, float] = {
        "max_pickup_radius_km": 5.0,
        "max_allowed_delay_min": 20.0,
        "max_vehicle_capacity": 6,
        "max_weight_kg": 100.0,
    }
    key_map = {
        "max_pickup_radius_km": "max_pickup_radius_km",
        "max_allowed_delay_min": "max_allowed_delay_min",
        "max_vehicle_capacity": "max_vehicle_capacity",
        "max_weight_kg": "max_weight_kg",
    }
    for field_name, cfg_key in key_map.items():
        row = db.query(SystemConfig).filter(SystemConfig.key == cfg_key).first()
        if row:
            try:
                rules[field_name] = float(row.value)
            except (ValueError, TypeError):
                pass
    return rules


def _time_within_window(
    r1: SimulationRequest,
    r2: SimulationRequest,
    max_delay_min: float,
) -> bool:
    """Cheap gate 3 pre-check: request timestamps within the delay window."""
    ts1, ts2 = r1.request_timestamp, r2.request_timestamp
    if ts1 is None or ts2 is None:
        return True  # unknown timestamps → do not block batching
    if ts1.tzinfo is None:
        ts1 = ts1.replace(tzinfo=timezone.utc)
    if ts2.tzinfo is None:
        ts2 = ts2.replace(tzinfo=timezone.utc)
    diff_min = abs((ts1 - ts2).total_seconds()) / 60.0
    return diff_min <= max_delay_min


class BatchGenerator:
    """
    Generates candidate batch groups from pending requests using a
    proximity-first, greedy-assignment strategy.
    """

    def __init__(self):
        self._calculator = CompatibilityCalculator()

    def create_feasible_batches(
        self,
        pending_requests: List[SimulationRequest],
        db: Session,
    ) -> List[CandidateGroup]:
        """
        Phase 9 — Create feasible batches from the pending queue.

        Only batches passing ALL THREE gates are returned:
          1. Compatibility Score >= configured threshold
          2. Vehicle capacity is sufficient (combined demand/weight fits)
          3. Time compatibility is acceptable (within max_allowed_delay_min)

        Optimisation: cheap pair-level pre-checks (time window, pickup
        radius, capacity) run BEFORE the full 5-factor compatibility
        computation, so infeasible pairs are skipped without any scoring.

        Each request is assigned to at most one batch (greedy disjoint
        assignment, highest-scoring batch first).  Requests not present in
        any returned batch must be dispatched as individual trips.
        """
        if len(pending_requests) < 2:
            return []

        rules = _get_ai_rules(db)
        threshold = _get_threshold(db)
        max_radius = rules["max_pickup_radius_km"]
        max_delay = rules["max_allowed_delay_min"]
        max_capacity = int(rules["max_vehicle_capacity"])
        max_weight = rules["max_weight_kg"]

        n = len(pending_requests)
        checked = 0
        evaluated = 0
        feasible: List[CandidateGroup] = []

        # ── Pairwise evaluation with cheap pre-checks ────────────────────────
        for i in range(n):
            for j in range(i + 1, n):
                r1, r2 = pending_requests[i], pending_requests[j]

                # Gate 3 pre-check — time window (cheapest: timestamp math)
                if not _time_within_window(r1, r2, max_delay):
                    continue

                # Gate 1 pre-check — pickup proximity radius
                if haversine(r1.pickup_lat, r1.pickup_lng,
                             r2.pickup_lat, r2.pickup_lng) > max_radius:
                    continue

                # Gate 2 pre-check — vehicle capacity (demand & weight)
                combined_demand = (r1.demand or 1) + (r2.demand or 1)
                combined_weight = (r1.weight_kg or 0.0) + (r2.weight_kg or 0.0)
                if combined_demand > max_capacity or combined_weight > max_weight:
                    continue

                checked += 1
                try:
                    result = self._calculator.compute([r1, r2], db)
                    evaluated += 1
                except Exception as exc:
                    logger.warning("Compatibility compute failed for (%d, %d): %s",
                                   r1.id, r2.id, exc)
                    continue

                # ── Full compatibility gate ──────────────────────────────────
                # Gate 1: weighted Compatibility Score >= threshold
                if result.compatibility_score < threshold:
                    continue
                # Gate 2 (re-verify): capacity factor must not be exceeded
                if result.factor_scores.get("capacity", 0.0) <= 0.0:
                    continue
                # Gate 3 (re-verify): time factor must be within window
                if result.factor_scores.get("time", 0.0) <= 0.0:
                    continue

                feasible.append(CandidateGroup(requests=[r1, r2], result=result))

        # Highest compatibility first → best batches claimed first
        feasible.sort(key=lambda cg: cg.result.compatibility_score, reverse=True)

        # ── Greedy disjoint assignment: one request in exactly one batch ─────
        assigned_ids: Set[int] = set()
        final_batches: List[CandidateGroup] = []

        for cg in feasible:
            req_ids = {r.id for r in cg.requests}
            if req_ids.isdisjoint(assigned_ids):
                assigned_ids.update(req_ids)
                final_batches.append(cg)

        logger.info(
            "BatchGenerator: %d pending → %d pairs pre-checked → %d fully "
            "evaluated → %d feasible batches (threshold %.1f)",
            n, checked, evaluated, len(final_batches), threshold,
        )

        return final_batches

    def generate_candidates(
        self,
        pending_requests: List[SimulationRequest],
        db: Session,
    ) -> List[CandidateGroup]:
        """
        Evaluate all valid pairwise combinations and return CandidateGroup
        objects sorted by compatibility score (descending).

        Only considers pairs where pickup-to-pickup distance ≤ max_pickup_radius_km.
        Each request is included in at most one candidate group (greedy assignment).
        """
        if len(pending_requests) < 2:
            return []

        max_radius = _get_max_radius(db)
        n = len(pending_requests)
        total_pairs = 0
        evaluated: List[CandidateGroup] = []

        # ── Pairwise evaluation ──────────────────────────────────────────────
        for i in range(n):
            for j in range(i + 1, n):
                r1, r2 = pending_requests[i], pending_requests[j]

                # Pre-filter: skip geographically distant pairs
                dist = haversine(r1.pickup_lat, r1.pickup_lng,
                                  r2.pickup_lat, r2.pickup_lng)
                if dist > max_radius:
                    continue

                total_pairs += 1
                try:
                    result = self._calculator.compute([r1, r2], db)
                    evaluated.append(CandidateGroup(requests=[r1, r2], result=result))
                except Exception as exc:
                    logger.warning("Compatibility compute failed for (%d, %d): %s",
                                   r1.id, r2.id, exc)

        logger.info(
            "BatchGenerator: %d requests → %d pairs within radius → %d evaluated",
            n, total_pairs, len(evaluated)
        )

        # Sort by score descending
        evaluated.sort(key=lambda cg: cg.result.compatibility_score, reverse=True)

        # ── Greedy assignment: each request in at most one batch ─────────────
        assigned_ids: Set[int] = set()
        final_groups: List[CandidateGroup] = []

        for cg in evaluated:
            req_ids = {r.id for r in cg.requests}
            if req_ids.isdisjoint(assigned_ids):
                assigned_ids.update(req_ids)
                final_groups.append(cg)

        return final_groups
