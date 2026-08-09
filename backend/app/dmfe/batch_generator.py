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
import math
from dataclasses import dataclass
from datetime import timezone
from typing import Dict, Iterator, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.db.models import SimulationRequest
from app.engine.distance import haversine
from app.dmfe.adaptive.matrix import CompatibilityMatrix
from app.dmfe.compatibility import (
    CompatibilityCalculator,
    CompatibilityResult,
    _get_ai_rules,
    _get_threshold,
    _pair_key,
    resolve_mode,
)

logger = logging.getLogger(__name__)


@dataclass
class CandidateGroup:
    """A proposed batch of 2–3 requests with its compatibility evaluation."""
    requests: List[SimulationRequest]
    result: CompatibilityResult


def _get_max_radius(db: Session) -> float:
    """Pickup radius from SystemConfig (cached via compatibility)."""
    return _get_ai_rules(db)["max_pickup_radius_km"]


def _time_diff_min(
    r1: SimulationRequest,
    r2: SimulationRequest,
) -> Optional[float]:
    """
    Raw absolute timestamp difference in minutes (tz-normalised);
    None when either timestamp is unknown (gate stays open, same as the
    legacy request_times_within_window behaviour).
    """
    if r1.request_timestamp is None or r2.request_timestamp is None:
        return None
    ts1, ts2 = r1.request_timestamp, r2.request_timestamp
    if ts1.tzinfo is None:
        ts1 = ts1.replace(tzinfo=timezone.utc)
    if ts2.tzinfo is None:
        ts2 = ts2.replace(tzinfo=timezone.utc)
    return abs((ts1 - ts2).total_seconds()) / 60.0


def _bucketized_pairs(
    pending: List[SimulationRequest],
    max_radius_km: float,
) -> Iterator[Tuple[int, int]]:
    """
    Yield (i, j) candidate pairs from the same or neighbouring latitude
    bands (width = pickup radius), mirroring CompatibilityMatrix.

    Any two requests closer than the pickup radius differ by at most that
    distance in latitude, so they always sit in the same or adjacent bands.
    This prunes the blind O(n²) scan to O(n·k) with the SAME candidate set —
    every pair still passes the exact haversine radius gate.
    """
    buckets = CompatibilityMatrix._bucketize(pending, max_radius_km)
    band = max(max_radius_km / 111.0, 1e-6)
    keys = sorted(buckets.keys())
    for bi, key in enumerate(keys):
        for idx in buckets[key]:
            for ki in range(max(0, bi - 1), min(len(keys), bi + 2)):
                for jdx in buckets[keys[ki]]:
                    if jdx <= idx:
                        continue
                    yield idx, jdx


def _build_request_metrics(
    pending: List[SimulationRequest],
) -> Dict[int, Dict[str, float]]:
    """Per-request trip lengths — computed once, shared by every pair."""
    return {
        r.id: {"trip_km": haversine(
            r.pickup_lat, r.pickup_lng, r.drop_lat, r.drop_lng,
        )}
        for r in pending
    }


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

        A-DMFE (admfe.mode = "adaptive", default): the whole context-aware
        stack runs here — context profile → adaptive weights → compatibility
        matrix → BQS-gated pair/triple formation → greedy selection.  The
        return contract (List[CandidateGroup]) is unchanged.

        Static mode: exact Phase 9 behaviour (see below).
        """
        if len(pending_requests) < 2:
            return []

        mode = resolve_mode(db)
        if mode == "adaptive":
            return self._create_adaptive_batches(pending_requests, db)

        rules = _get_ai_rules(db)
        threshold = _get_threshold(db)
        max_radius = rules["max_pickup_radius_km"]
        max_delay = rules["max_allowed_delay_min"]
        max_capacity = int(rules["max_vehicle_capacity"])
        max_weight = rules["max_weight_kg"]

        n = len(pending_requests)
        checked = 0
        evaluated = 0
        feasible: List[Tuple[int, int, CandidateGroup]] = []

        # ── Pairwise evaluation with cheap pre-checks ────────────────────────
        # Latitude-band scan (same candidate set as the blind O(n²) scan,
        # same gates, same scoring — just far fewer pairs touched).
        cos_cache = {
            r.id: math.cos(r.pickup_lat * math.pi / 180.0)
            for r in pending_requests
        }
        request_metrics = _build_request_metrics(pending_requests)
        precomputed: Dict[Tuple[int, int], Dict[str, float]] = {}
        lat_scale = 111.0

        for i, j in _bucketized_pairs(pending_requests, max_radius):
            r1, r2 = pending_requests[i], pending_requests[j]

            # Longitude quick-check (cheapest float gate, ≈cos(lat) scaled)
            if (abs(r1.pickup_lng - r2.pickup_lng) * lat_scale
                    * cos_cache[r1.id]) > max_radius:
                continue

            # Gate 1 pre-check — pickup proximity radius (exact haversine)
            pickup_km = haversine(r1.pickup_lat, r1.pickup_lng,
                                   r2.pickup_lat, r2.pickup_lng)
            if pickup_km > max_radius:
                continue

            # Gate 3 pre-check — time window (cheapest timestamp math)
            time_diff = _time_diff_min(r1, r2)
            if time_diff is not None and time_diff > max_delay:
                continue

            # Gate 2 pre-check — vehicle capacity (demand & weight)
            combined_demand = (r1.demand or 1) + (r2.demand or 1)
            combined_weight = (r1.weight_kg or 0.0) + (r2.weight_kg or 0.0)
            if combined_demand > max_capacity or combined_weight > max_weight:
                continue

            # Gate 4 pre-check — detour delay within the configured limit
            # (mirror of estimated_delay_score: pickup km at 30 km/h; with
            # the default radius/delay config this never fires, it only
            # guards against tighter delay limits than the radius allows)
            if (pickup_km / 30.0) * 60.0 > max_delay:
                continue

            checked += 1
            # Share the geodesic/time values already computed by the gates
            key = _pair_key(r1.id, r2.id)
            precomputed[key] = {
                "pickup_distance_km": pickup_km,
                "time_diff_min": time_diff,
            }
            try:
                result = self._calculator.compute(
                    [r1, r2], db,
                    precomputed=precomputed,
                    request_metrics=request_metrics,
                )
                evaluated += 1
            except Exception as exc:
                logger.warning("Compatibility compute failed for (%d, %d): %s",
                               r1.id, r2.id, exc)
                continue

            # ── Full compatibility gate ──────────────────────────────────────
            # Gate 1: weighted Compatibility Score >= threshold
            if result.compatibility_score < threshold:
                continue
            # Gate 2 (re-verify): capacity factor must not be exceeded
            if result.factor_scores.get("capacity", 0.0) <= 0.0:
                continue
            # Gate 3 (re-verify): time factor must be within window
            if result.factor_scores.get("time", 0.0) <= 0.0:
                continue

            feasible.append((i, j, CandidateGroup(requests=[r1, r2], result=result)))

        # Highest compatibility first → best batches claimed first.
        # (i, j) tie-break mirrors the stable scan order of the legacy
        # pairwise loop, so equal-score candidates claim in the same order.
        feasible.sort(key=lambda t: (-t[2].result.compatibility_score, t[0], t[1]))

        # ── Greedy disjoint assignment: one request in exactly one batch ─────
        assigned_ids: Set[int] = set()
        final_batches: List[CandidateGroup] = []

        for _, _, cg in feasible:
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

    # ────────────────────────────────────────────────────────────────────────
    # A-DMFE adaptive path (Module 1→6 orchestration)
    # ────────────────────────────────────────────────────────────────────────

    def _create_adaptive_batches(
        self,
        pending_requests: List[SimulationRequest],
        db: Session,
    ) -> List[CandidateGroup]:
        """
        Full A-DMFE batch formation:

          1. Context profile            (Module 1)
          2. Adaptive weights           (Module 2)
          3. Effective thresholds       (Module 6)
          4. Compatibility matrix       (Module 4)
          5. BQS-gated pair/triple set  (Module 5)
        """
        from app.dmfe.adaptive.batching import AdaptiveBatchFormation
        from app.dmfe.adaptive.context import ContextAwarenessEngine
        from app.dmfe.adaptive.weights import AdaptiveWeightGenerator
        from app.dmfe.adaptive.decision import (
            effective_threshold,
            bqs_threshold,
        )
        from app.dmfe.adaptive.learning import LearningEngine

        rules = _get_ai_rules(db)
        context = ContextAwarenessEngine().build(db, pending_requests)
        learning_state = LearningEngine.load_state(db)
        weights = AdaptiveWeightGenerator(mode="adaptive").generate(
            db, context, LearningEngine.weight_corrections(db)
        )
        threshold = effective_threshold(_get_threshold(db), context)
        bqs_thr = bqs_threshold(context)

        logger.info(
            "A-DMFE run: %d pending → traffic %.2f, demand %.2f, drivers %.2f, "
            "θ_eff %.1f, θ_bqs %.2f, weights %s",
            len(pending_requests),
            context.traffic_index, context.demand_pressure,
            context.driver_availability, threshold, bqs_thr,
            {k: round(v, 3) for k, v in weights.items()},
        )

        return AdaptiveBatchFormation().create_feasible_batches(
            pending_requests, db, mode="adaptive", context=context,
            weights=weights, rules=rules, threshold=threshold,
            bqs_threshold_value=bqs_thr, learning_state=learning_state,
        )

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

        A-DMFE: in adaptive mode the compatibility matrix is used (each pair
        evaluated exactly once with context-aware weights) — the returned
        contract (sorted CandidateGroups) is unchanged.
        """
        if len(pending_requests) < 2:
            return []

        mode = resolve_mode(db)

        if mode == "adaptive":
            from app.dmfe.adaptive.context import ContextAwarenessEngine
            from app.dmfe.adaptive.weights import AdaptiveWeightGenerator
            from app.dmfe.adaptive.decision import (
                effective_threshold,
                bqs_threshold,
            )
            from app.dmfe.adaptive.learning import LearningEngine
            from app.dmfe.adaptive.matrix import CompatibilityMatrix

            rules = _get_ai_rules(db)
            context = ContextAwarenessEngine().build(db, pending_requests)
            learning_state = LearningEngine.load_state(db)
            weights = AdaptiveWeightGenerator(mode="adaptive").generate(
                db, context, LearningEngine.weight_corrections(db)
            )
            threshold = effective_threshold(_get_threshold(db), context)
            bqs_thr = bqs_threshold(context)

            matrix = CompatibilityMatrix(
                pending_requests, db, context, weights, mode, rules,
                threshold, bqs_thr, learning_state,
                calculator=self._calculator,
            ).build()

            evaluated: List[Tuple[int, int, CandidateGroup]] = [
                (c.i, c.j, CandidateGroup(
                    requests=self._matrix_requests(pending_requests, c),
                    result=c.result,
                ))
                for c in matrix.cells.values()
            ]
            logger.info(
                "BatchGenerator (A-DMFE): %d requests → %d pairs evaluated",
                len(pending_requests), len(evaluated),
            )
        else:
            max_radius = _get_max_radius(db)
            n = len(pending_requests)
            total_pairs = 0
            evaluated: List[Tuple[int, int, CandidateGroup]] = []

            # ── Pairwise evaluation (latitude-band scan, radius gate only) ──
            cos_cache = {
                r.id: math.cos(r.pickup_lat * math.pi / 180.0)
                for r in pending_requests
            }
            request_metrics = _build_request_metrics(pending_requests)
            precomputed: Dict[Tuple[int, int], Dict[str, float]] = {}
            lat_scale = 111.0

            for i, j in _bucketized_pairs(pending_requests, max_radius):
                r1, r2 = pending_requests[i], pending_requests[j]

                # Longitude quick-check (cheapest float gate)
                if (abs(r1.pickup_lng - r2.pickup_lng) * lat_scale
                        * cos_cache[r1.id]) > max_radius:
                    continue

                # Pre-filter: skip geographically distant pairs (exact)
                dist = haversine(r1.pickup_lat, r1.pickup_lng,
                                  r2.pickup_lat, r2.pickup_lng)
                if dist > max_radius:
                    continue

                total_pairs += 1
                key = _pair_key(r1.id, r2.id)
                precomputed[key] = {"pickup_distance_km": dist}
                try:
                    result = self._calculator.compute(
                        [r1, r2], db,
                        precomputed=precomputed,
                        request_metrics=request_metrics,
                    )
                    evaluated.append((i, j, CandidateGroup(
                        requests=[r1, r2], result=result)))
                except Exception as exc:
                    logger.warning("Compatibility compute failed for (%d, %d): %s",
                                   r1.id, r2.id, exc)

            logger.info(
                "BatchGenerator: %d requests → %d pairs within radius → %d evaluated",
                n, total_pairs, len(evaluated)
            )

        # Sort by score descending ((i, j) tie-break mirrors legacy scan order)
        evaluated.sort(key=lambda t: (-t[2].result.compatibility_score, t[0], t[1]))

        # ── Greedy assignment: each request in at most one batch ─────────────
        assigned_ids: Set[int] = set()
        final_groups: List[CandidateGroup] = []

        for _, _, cg in evaluated:
            req_ids = {r.id for r in cg.requests}
            if req_ids.isdisjoint(assigned_ids):
                assigned_ids.update(req_ids)
                final_groups.append(cg)

        return final_groups

    @staticmethod
    def _matrix_requests(pending_requests, cell) -> List[SimulationRequest]:
        """Map a matrix cell (request ids) back to request objects."""
        by_id = {r.id: r for r in pending_requests}
        return [by_id[cell.i], by_id[cell.j]]
