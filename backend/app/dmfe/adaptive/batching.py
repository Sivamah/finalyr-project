"""
A-DMFE Module 5 — Intelligent Batch Formation
=============================================
Forms batches from the Compatibility Matrix with explicit quality control:

  1. Context profile (Module 1) and adaptive weights (Module 2) are
     computed once per run.
  2. The N×N compatibility matrix (Module 4) supplies every evaluated pair
     (each pair scored exactly once).
  3. Candidate batches = pairs passing BOTH gates:
         CS  ≥ θ_eff     (adaptive compatibility threshold)
         BQS ≥ θ_bqs     (adaptive Batch Quality Score threshold)
     The BQS gate rejects poor-quality batches that a plain CS ≥ threshold
     rule would accept (e.g. high score but tiny savings / large delay).
  4. 3-member batches are formed by expanding the best pairs with the
     strongest compatible third request (capacity + quality checked).
  5. Final selection is greedy by BQS (then CS) with disjointness — the
     same contract as the Phase 9 generator, so the pipeline, decision
     engine and evaluation harness work unchanged.

Backwards compatibility: in ``admfe.mode = "static"`` this module is not
used; BatchGenerator falls back to the exact Phase 9 algorithm.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import SimulationRequest
from app.dmfe.compatibility import CompatibilityCalculator

logger = logging.getLogger(__name__)

# Triple expansion budget: only the top pairs (by BQS) are expanded
TRIPLE_EXPANSION_BUDGET = 60
# A triple is only kept if it improves BQS over its best sub-pair
TRIPLE_MIN_IMPROVEMENT = 0.02


class AdaptiveBatchFormation:
    """
    Context-driven batch formation on top of the compatibility matrix.
    """

    def __init__(self) -> None:
        self._calculator = CompatibilityCalculator()

    def create_feasible_batches(
        self,
        pending: List[SimulationRequest],
        db: Session,
        mode: str,
        context,
        weights: Dict[str, float],
        rules: Dict[str, float],
        threshold: float,
        bqs_threshold_value: float,
        learning_state: Optional[Dict[str, Any]] = None,
        matrix=None,
    ) -> List[Any]:
        """
        Returns a list of CandidateGroup objects (the Phase 9 contract).

        Every returned group carries its full CompatibilityResult including
        batch_score, decision_confidence, context profile and attribution.
        """
        from app.dmfe.batch_generator import CandidateGroup

        if len(pending) < 2:
            return []

        from app.dmfe.adaptive.matrix import CompatibilityMatrix

        if matrix is None:
            matrix = CompatibilityMatrix(
                pending, db, context, weights, mode, rules,
                threshold, bqs_threshold_value, learning_state,
                calculator=self._calculator,
            ).build()

        # ── 1. Pair-level candidates (both adaptive gates) ─────────────────
        pair_candidates = [
            cell for cell in matrix.cells.values()
            if cell.result.compatibility_score >= threshold
            and cell.bqs >= bqs_threshold_value
        ]
        pair_candidates.sort(
            key=lambda c: (-c.bqs, -c.result.compatibility_score)
        )

        groups: List[CandidateGroup] = [
            CandidateGroup(requests=self._by_ids(pending, c), result=c.result)
            for c in pair_candidates
        ]

        # ── 2. Triple expansion of the strongest pairs ─────────────────────
        if len(pair_candidates) > 0:
            groups = self._expand_triples(
                groups, pair_candidates, pending, db, context, weights,
                mode, rules, threshold, bqs_threshold_value,
                learning_state, matrix,
            )

        # ── 3. Greedy disjoint selection by BQS (then CS) ──────────────────
        groups.sort(
            key=lambda g: (
                -(g.result.batch_score or 0.0),
                -g.result.compatibility_score,
            )
        )
        assigned_ids = set()
        final: List[CandidateGroup] = []
        for g in groups:
            ids = {r.id for r in g.requests}
            if ids.isdisjoint(assigned_ids):
                assigned_ids.update(ids)
                final.append(g)

        logger.info(
            "AdaptiveBatchFormation: %d pairs evaluated → %d candidates "
            "(CS≥%.1f, BQS≥%.2f) → %d final batches",
            matrix.matrix_size(), len(groups), threshold,
            bqs_threshold_value, len(final),
        )
        return final

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _by_ids(pending: List[SimulationRequest], cell) -> List[SimulationRequest]:
        """Map a matrix cell back to request objects."""
        by_id = {r.id: r for r in pending}
        return [by_id[cell.i], by_id[cell.j]]

    def _expand_triples(
        self,
        groups: List[Any],
        pair_candidates: List[Any],
        pending: List[SimulationRequest],
        db: Session,
        context,
        weights: Dict[str, float],
        mode: str,
        rules: Dict[str, float],
        threshold: float,
        bqs_threshold_value: float,
        learning_state: Optional[Dict[str, Any]],
        matrix,
    ) -> List[Any]:
        """
        For the top-K pair candidates, attach the best compatible third
        request and evaluate the 3-member batch.  Triples that pass both
        gates AND improve BQS over their best sub-pair are kept.
        """
        from app.dmfe.batch_generator import CandidateGroup
        from app.dmfe.adaptive.decision import batch_quality_score

        by_id = {r.id: r for r in pending}
        max_capacity = int(rules.get("max_vehicle_capacity", 6))
        max_weight = rules.get("max_weight_kg", 100.0)
        triples: List[CandidateGroup] = []
        seen_triples: set = set()

        for cell in pair_candidates[:TRIPLE_EXPANSION_BUDGET]:
            a_id, b_id = cell.i, cell.j
            # Third-request candidates: best partners of either endpoint
            third_candidates: List[Any] = []
            for partner in matrix.best_partners(a_id, k=4):
                if partner.i not in (a_id, b_id):
                    third_candidates.append(partner.i)
                if partner.j not in (a_id, b_id):
                    third_candidates.append(partner.j)
            for partner in matrix.best_partners(b_id, k=4):
                if partner.i not in (a_id, b_id):
                    third_candidates.append(partner.i)
                if partner.j not in (a_id, b_id):
                    third_candidates.append(partner.j)

            for c_id in third_candidates:
                c = by_id.get(c_id)
                if c is None:
                    continue
                group = (a_id, b_id, c_id)
                if group in seen_triples:
                    continue
                seen_triples.add(group)

                r_a, r_b, r_c = by_id[a_id], by_id[b_id], c
                demand = ((r_a.demand or 1) + (r_b.demand or 1) + (c.demand or 1))
                weight = ((r_a.weight_kg or 0.0) + (r_b.weight_kg or 0.0)
                          + (c.weight_kg or 0.0))
                if demand > max_capacity or weight > max_weight:
                    continue

                try:
                    result = self._calculator.compute(
                        [r_a, r_b, r_c], db,
                        context=context, weights=weights, mode=mode,
                        learning_state=learning_state,
                    )
                except Exception:
                    continue

                if result.compatibility_score < threshold:
                    continue
                triple_bqs = batch_quality_score(
                    result.compatibility_score,
                    result.factor_scores,
                    result.extensions,
                    result.factor_details,
                    rules,
                    n_requests=3,
                )
                if triple_bqs < bqs_threshold_value:
                    continue
                ac = matrix.get(a_id, c_id)
                bc = matrix.get(b_id, c_id)
                best_pair_bqs = max(
                    cell.bqs,
                    ac.bqs if ac else 0.0,
                    bc.bqs if bc else 0.0,
                )
                if triple_bqs < best_pair_bqs + TRIPLE_MIN_IMPROVEMENT:
                    continue

                triples.append(CandidateGroup(requests=[r_a, r_b, r_c], result=result))

        return groups + triples
