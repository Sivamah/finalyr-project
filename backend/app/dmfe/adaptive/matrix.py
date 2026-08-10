"""
A-DMFE Module 4 — Compatibility Matrix
======================================
Builds a complete N×N upper-triangular compatibility matrix over the
pending request pool.  Every cell (i, j) stores the full adaptive
evaluation: five-factor CS, extension factors, expected delay, Batch
Quality Score and decision confidence.

Performance (Module 9): instead of O(n²) blind pairing, requests are
spatially bucketed into latitude bands of width = pickup radius.  Only
requests within the current or neighbouring bands (plus a longitude
quick-check and the haversine radius test) are evaluated, cutting the
work from O(n²) to O(n·k) with k ≪ n.

Matrix cells are reused by the Intelligent Batch Formation (Module 5),
the Adaptive Decision Engine (Module 6) and the XAI layer (Module 7) —
every pair is evaluated exactly once per run.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import SimulationRequest
from app.engine.distance import haversine
from app.dmfe.compatibility import CompatibilityCalculator, CompatibilityResult
from app.dmfe.score_engine import request_times_within_window

logger = logging.getLogger(__name__)


@dataclass
class PairCell:
    """One evaluated entry of the compatibility matrix."""
    i: int
    j: int
    result: CompatibilityResult
    bqs: float
    threshold: float
    confidence: float
    combined_demand: int
    combined_weight: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_ids": [self.i, self.j],
            "compatibility_score": self.result.compatibility_score,
            "bqs": self.bqs,
            "confidence": self.confidence,
            "threshold": self.threshold,
            "estimated_delay_min": self.result.estimated_delay_min,
        }


class CompatibilityMatrix:
    """
    N×N upper-triangular compatibility matrix with spatial bucketing.

    Usage:
        matrix = CompatibilityMatrix(
            requests, db, context, weights, mode, rules,
            threshold, bqs_threshold_value, learning_state,
        )
        matrix.build()
        cell = matrix.get(i, j)          # Optional[PairCell]
        best = matrix.best_partners(i, k=5)
    """

    def __init__(
        self,
        requests: List[SimulationRequest],
        db: Session,
        context,
        weights: Dict[str, float],
        mode: str,
        rules: Dict[str, float],
        threshold: float,
        bqs_threshold_value: float,
        learning_state: Optional[Dict[str, Any]] = None,
        calculator: Optional[CompatibilityCalculator] = None,
    ) -> None:
        self.requests = requests
        self.db = db
        self.context = context
        self.weights = weights
        self.mode = mode
        self.rules = rules
        self.threshold = threshold
        self.bqs_threshold_value = bqs_threshold_value
        self.learning_state = learning_state
        self._calculator = calculator or CompatibilityCalculator()
        self.cells: Dict[Tuple[int, int], PairCell] = {}
        self.evaluated = 0
        self.pruned = 0

    # ── spatial bucketing ───────────────────────────────────────────────────

    @staticmethod
    def _bucketize(
        requests: List[SimulationRequest], cell_km: float
    ) -> Dict[int, List[int]]:
        """Map request indices into latitude bands of width cell_km."""
        band = max(cell_km / 111.0, 1e-6)
        buckets: Dict[int, List[int]] = {}
        for idx, r in enumerate(requests):
            key = int(r.pickup_lat / band)
            buckets.setdefault(key, []).append(idx)
        return buckets

    def build(self) -> "CompatibilityMatrix":
        """Evaluate every relevant pair exactly once and store it."""
        n = len(self.requests)
        if n < 2:
            return self

        max_radius = self.rules.get("max_pickup_radius_km", 5.0)
        max_delay = self.rules.get("max_allowed_delay_min", 20.0)
        max_capacity = int(self.rules.get("max_vehicle_capacity", 6))
        max_weight = self.rules.get("max_weight_kg", 100.0)

        buckets = self._bucketize(self.requests, max_radius)
        bucket_keys = sorted(buckets.keys())

        for bi, key in enumerate(bucket_keys):
            for idx in buckets[key]:
                r1 = self.requests[idx]
                # Candidates: same band + neighbouring bands
                for ki in range(max(0, bi - 1), min(len(bucket_keys), bi + 2)):
                    for jdx in buckets[bucket_keys[ki]]:
                        if jdx <= idx:
                            continue
                        r2 = self.requests[jdx]

                        # ── Cheap gates before any scoring ──────────────────
                        # Longitude quick-check (≈ cos(lat) scaled)
                        lng_km = (
                            abs(r1.pickup_lng - r2.pickup_lng) * 111.0
                            * math.cos(r1.pickup_lat * math.pi / 180.0)
                        )
                        if lng_km > max_radius:
                            self.pruned += 1
                            continue
                        if haversine(
                            r1.pickup_lat, r1.pickup_lng,
                            r2.pickup_lat, r2.pickup_lng,
                        ) > max_radius:
                            self.pruned += 1
                            continue
                        if not request_times_within_window(
                            r1.request_timestamp, r2.request_timestamp, max_delay
                        ):
                            self.pruned += 1
                            continue
                        demand = (r1.demand or 1) + (r2.demand or 1)
                        weight = (r1.weight_kg or 0.0) + (r2.weight_kg or 0.0)
                        if demand > max_capacity or weight > max_weight:
                            self.pruned += 1
                            continue

                        # ── Full adaptive evaluation (once per pair) ────────
                        try:
                            result = self._calculator.compute(
                                [r1, r2], self.db,
                                context=self.context,
                                weights=self.weights,
                                mode=self.mode,
                                learning_state=self.learning_state,
                            )
                        except Exception as exc:
                            logger.warning(
                                "Matrix compute failed for (%d, %d): %s",
                                r1.id, r2.id, exc,
                            )
                            continue
                        self.evaluated += 1

                        from app.dmfe.adaptive.decision import (
                            batch_quality_score,
                        )

                        bqs = batch_quality_score(
                            result.compatibility_score,
                            result.factor_scores,
                            result.extensions,
                            result.factor_details,
                            self.rules,
                            n_requests=2,
                        )
                        self.cells[(idx, jdx)] = PairCell(
                            i=r1.id, j=r2.id, result=result, bqs=bqs,
                            threshold=self.threshold,
                            confidence=result.decision_confidence or 0.0,
                            combined_demand=demand,
                            combined_weight=weight,
                        )
        logger.info(
            "CompatibilityMatrix: n=%d, evaluated=%d, pruned=%d",
            n, self.evaluated, self.pruned,
        )
        return self

    # ── accessors ───────────────────────────────────────────────────────────

    def get(self, i: int, j: int) -> Optional[PairCell]:
        if i == j:
            return None
        return self.cells.get((i, j)) or self.cells.get((j, i))

    def best_partners(self, i: int, k: int = 5) -> List[PairCell]:
        """Top-k partners of request i ranked by BQS (then CS)."""
        matches = [
            c for (a, b), c in self.cells.items() if a == i or b == i
        ]
        matches.sort(key=lambda c: (-c.bqs, -c.result.compatibility_score))
        return matches[:k]

    def best_pairs(self, k: int = 10) -> List[PairCell]:
        """Global top-k cells ranked by BQS."""
        cells = list(self.cells.values())
        cells.sort(key=lambda c: (-c.bqs, -c.result.compatibility_score))
        return cells[:k]

    def matrix_size(self) -> int:
        return len(self.cells)
