"""
DMFE Compatibility Calculator — Phase 9 Core Engine
====================================================
Loads configurable weights from SystemConfig, computes the five Phase 9
scoring factors via app.dmfe.scoring, and assembles a structured
CompatibilityResult with the weighted aggregate score

    CS = w1*Pickup + w2*Route + w3*Time + w4*Capacity + w5*Priority

plus natural-language explainability output.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.models import SimulationRequest, SystemConfig
from app.dmfe.scoring import (
    vehicle_capacity_score,
    priority_score,
    weighted_compatibility_score,
    DEFAULT_WEIGHTS,
    FACTOR_KEYS,
)
from app.dmfe.score_engine import destination_similarity_score
from app.engine.distance import haversine

logger = logging.getLogger(__name__)

# Config keys are immutable during a run — cache them briefly so the XAI
# dashboard's per-pair compatibility loop does not fire 12 SQL queries for
# every (request, partner) comparison.  TTL keeps config edits visible.
_CONFIG_CACHE_TTL = 15.0
_config_cache: Dict[str, tuple] = {}


def _on_schema_create(*args, **kwargs) -> None:
    """Drop cached config when the metadata/schema is (re)created."""
    _config_cache.clear()


# Whenever Base.metadata.create_all() runs (fresh boot OR a schema reset in
# the evaluation harness), the SystemConfig table is re-seeded — cached
# values from the previous DB state must not be served.
event.listen(Base.metadata, "after_create", _on_schema_create)


def _cached(db: Session, key: str, loader) -> Any:
    """TTL-cache a config-derived value keyed on the SQL database."""
    cached = _config_cache.get(key)
    if cached is not None and time.monotonic() - cached[0] < _CONFIG_CACHE_TTL:
        return cached[1]
    value = loader(db)
    _config_cache[key] = (time.monotonic(), value)
    return value


def clear_config_cache() -> None:
    """
    Drop every cached config-derived value.

    Called after a config write (SystemConfig mutation) or a schema reset
    so the next read reflects the fresh database state instead of serving
    a value cached within the 15s TTL window.
    """
    _config_cache.clear()


# ── Phase 2: per-run memoisation helpers ───────────────────────────────────
# The compatibility matrix evaluates every pair of the pending pool with a
# full compute() — these helpers keep per-RUN values (config flags, context
# serialisation, shared pair metrics) out of the per-pair hot path without
# introducing a competing distance-matrix cache (the Phase 1 matrix in
# optimizer.py remains the single full-matrix implementation).

def _pair_key(a: int, b: int) -> Tuple[int, int]:
    """Canonical, direction-independent key for a request-id pair."""
    return (a, b) if a < b else (b, a)


def _refit_enabled(db: Session) -> bool:
    """
    TTL-free refit flag cached on the session object.

    ``LearningEngine.refit_enabled`` reads SystemConfig (one SQL query) and
    was being called once PER PAIR during matrix evaluation (~30k queries /
    run).  A batch run never flips the flag mid-flight, and the cache lives
    on the session (one session = one run/request), so per-session caching
    is safe and needs no TTL.
    """
    cached = getattr(db, "_dmfe_refit_enabled_cache", None)
    if cached is not None:
        return cached
    from app.dmfe.adaptive.learning import LearningEngine as _LE

    value = _LE.refit_enabled(db)
    try:
        setattr(db, "_dmfe_refit_enabled_cache", value)
    except Exception:
        logger.debug(
            "Could not cache _dmfe_refit_enabled on session object",
            exc_info=True,
        )
    return value


_last_context_obj = None
_last_context_dict: Optional[Dict[str, Any]] = None
_context_lock = threading.Lock()


def _context_profile_dict(context: Any) -> Optional[Dict[str, Any]]:
    """
    Serialise a ContextProfile once per object.

    The same context object is passed to every per-pair compute() of a run;
    before this helper the full dict was rebuilt ~N² times for byte-identical
    output.
    """
    global _last_context_obj, _last_context_dict
    if context is None:
        return None
    if context is _last_context_obj and _last_context_dict is not None:
        return _last_context_dict
    with _context_lock:
        if context is _last_context_obj and _last_context_dict is not None:
            return _last_context_dict
        d = context.to_dict() if hasattr(context, "to_dict") else dict(context or {})
        _last_context_obj, _last_context_dict = context, d
        return d


# ── Shared SystemConfig readers (single source of truth) ────────────────────

def get_config_value(db: Session, key: str, default: Any = None) -> Any:
    """Raw value of one SystemConfig key; ``default`` when the row is absent."""
    if db is None:
        return default
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return default if row is None else row.value


def read_float_value(db: Session, key: str, default: float) -> float:
    """One numeric SystemConfig value; ``default`` when absent/unparsable."""
    raw = get_config_value(db, key)
    if raw is None:
        return default
    try:
        return float(raw)
    except (ValueError, TypeError):
        return default


def read_float_rules(db: Session, defaults: Dict[str, float]) -> Dict[str, float]:
    """Numeric SystemConfig snapshot over ``defaults`` keys (missing → default)."""
    return {
        key: read_float_value(db, key, default)
        for key, default in defaults.items()
    }

# Config key names in SystemConfig table (Phase 9 — 5 configurable weights)
# DEFAULT_WEIGHTS is imported from app.dmfe.scoring (single source of truth)
WEIGHT_KEY_MAP = {
    "pickup":   "pickup_weight",
    "route":    "route_weight",
    "time":     "time_weight",
    "capacity": "capacity_weight",
    "priority": "priority_weight",
}


@dataclass
class CompatibilityResult:
    """Full output of one compatibility evaluation between 2–3 requests."""

    request_ids: List[int]
    compatibility_score: float          # 0–100 (percentage)
    factor_scores: Dict[str, float]     # individual factor scores 0–1
    factor_details: Dict[str, Any]      # raw metric values per factor
    reasons: List[str]                  # human-readable explanation bullets
    estimated_delay_min: float          # additional delay from batching
    weights_used: Dict[str, float]

    # ── A-DMFE extensions (additive; None/{} in static mode) ──────────────
    batch_score: Optional[float] = None             # BQS in [0, 1]
    decision_confidence: Optional[float] = None     # 0–100
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    extensions: Dict[str, float] = field(default_factory=dict)   # Module 3
    context_profile: Optional[Dict[str, Any]] = None              # Module 1
    mode: str = "static"

    def to_dict(self) -> Dict[str, Any]:
        """Dashboard-compatible dict (all original keys + additive extras)."""
        return {
            "request_ids": self.request_ids,
            "compatibility_score": self.compatibility_score,
            "factor_scores": self.factor_scores,
            "factor_details": self.factor_details,
            "reasons": self.reasons,
            "estimated_delay_min": self.estimated_delay_min,
            "weights_used": self.weights_used,
            "batch_score": self.batch_score,
            "decision_confidence": self.decision_confidence,
            "factor_contributions": self.factor_contributions,
            "extensions": self.extensions,
            "context_profile": self.context_profile,
            "mode": self.mode,
        }


def _load_weights(db: Session) -> Dict[str, float]:
    """
    Read weight values from SystemConfig.  Falls back to defaults if not found.
    Normalises weights so they always sum to exactly 1.0.
    """
    def _load(db: Session) -> Dict[str, float]:
        weights: Dict[str, float] = {}
        for factor, key in WEIGHT_KEY_MAP.items():
            weights[factor] = read_float_value(db, key, DEFAULT_WEIGHTS[factor])

        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        else:
            weights = dict(DEFAULT_WEIGHTS)

        return weights

    return _cached(db, "weights", _load)


def _get_ai_rules(db: Session) -> Dict[str, float]:
    """Load numeric AI rule settings from SystemConfig."""
    _AI_RULE_DEFAULTS: Dict[str, float] = {
        "max_pickup_radius_km": 5.0,
        "max_allowed_delay_min": 20.0,
        "max_vehicle_capacity": 6,
        "max_weight_kg": 100.0,
    }

    return _cached(db, "ai_rules", lambda _db: read_float_rules(_db, _AI_RULE_DEFAULTS))


# ─────────────────────────────────────────────────────────────────────────────
# A-DMFE mode resolution (Module 6 gate)
# ─────────────────────────────────────────────────────────────────────────────

ADMFE_MODE_KEY = "admfe.mode"


def _get_threshold(db: Session) -> float:
    """Compatibility threshold from SystemConfig (default 70.0)."""
    return _cached(db, "threshold", lambda _db: read_float_value(_db, "min_compatibility_score", 70.0))


def resolve_mode(db: Session) -> str:
    """
    Read the A-DMFE operating mode from SystemConfig.
    "adaptive" (default) — full context-aware stack;
    "static"             — exact Phase 9 fixed-weight behaviour.
    """
    def _load(db: Session) -> str:
        try:
            mode = get_config_value(db, ADMFE_MODE_KEY)
            if mode is not None:
                mode = str(mode).strip().lower()
                if mode in ("adaptive", "static"):
                    return mode
        except Exception:
            logger.warning(
                "Failed to read A-DMFE mode from SystemConfig; "
                "defaulting to 'adaptive'",
                exc_info=True,
            )
        return "adaptive"

    return _cached(db, "admfe_mode", _load)


class CompatibilityCalculator:
    """
    Evaluates compatibility between a group of SimulationRequests.

    Usage:
        calc = CompatibilityCalculator()
        result = calc.compute([req1, req2], db)
    """

    def compute(
        self,
        requests: List[SimulationRequest],
        db: Session,
        context: Optional[Any] = None,
        weights: Optional[Dict[str, float]] = None,
        mode: Optional[str] = None,
        learning_state: Optional[Dict[str, Any]] = None,
        precomputed: Optional[Dict[Tuple[int, int], Dict[str, float]]] = None,
        request_metrics: Optional[Dict[int, Dict[str, float]]] = None,
    ) -> CompatibilityResult:
        """
        Compute a full CompatibilityResult for a group of 2–3 requests.
        For groups > 2, pairwise scores are averaged.

        A-DMFE parameters (all optional — fully backward compatible):
          context        — ContextProfile from Module 1 (built lazily)
          weights        — adaptive weights from Module 2 (defaults to
                            configured weights when omitted)
          mode           — "adaptive" | "static" (resolved from SystemConfig)
          learning_state — Module 8 state (loaded lazily)

        Phase 2 performance parameters (additive, optional):
          precomputed    — {(min_id, max_id): {"pickup_distance_km": km,
                            "time_diff_min": raw_min}} — geodesic/time values
                            the caller already computed for its own gates;
                            missing entries are computed here as before.
          request_metrics— {request_id: {"trip_km": km}} — per-request trip
                            lengths shared by every pair evaluation.

        The five-factor scoring math is mirrored from app.dmfe.scoring /
        app.dmfe.score_engine (single source of truth) so the CS is
        byte-identical to calling those functions with fresh haversines.
        """
        if len(requests) < 2:
            raise ValueError("Need at least 2 requests to evaluate compatibility")

        if mode is None:
            mode = resolve_mode(db)

        # ── A-DMFE: context + adaptive weights (lazy when not supplied) ────
        adaptive = mode == "adaptive"
        context_profile_dict: Optional[Dict[str, Any]] = None
        if adaptive:
            if context is None:
                from app.dmfe.adaptive.context import ContextAwarenessEngine

                context = ContextAwarenessEngine().build(db, requests)
            if learning_state is None:
                from app.dmfe.adaptive.learning import LearningEngine

                learning_state = LearningEngine.load_state(db)
            if weights is None:
                from app.dmfe.adaptive.weights import AdaptiveWeightGenerator
                from app.dmfe.adaptive.learning import LearningEngine as LE

                weights = AdaptiveWeightGenerator(mode=mode).generate(
                    db, context, LE.weight_corrections(db)
                )
            context_profile_dict = _context_profile_dict(context)

        if weights is None:
            weights = _load_weights(db)
        rules = _get_ai_rules(db)

        # ── Shared raw metrics (computed once, reused by every factor) ─────
        precomputed = precomputed or {}
        request_metrics = request_metrics or {}
        max_radius = rules["max_pickup_radius_km"]
        max_delay = rules["max_allowed_delay_min"]
        avg_speed = rules.get("avg_speed_kmh", 25.0)

        def _pickup_km(r1, r2) -> float:
            pc = precomputed.get(_pair_key(r1.id, r2.id)) or {}
            km = pc.get("pickup_distance_km")
            if km is None:
                km = haversine(
                    r1.pickup_lat, r1.pickup_lng, r2.pickup_lat, r2.pickup_lng
                )
            return km

        def _time_diff(r1, r2) -> float:
            pc = precomputed.get(_pair_key(r1.id, r2.id)) or {}
            diff = pc.get("time_diff_min")
            if diff is not None:
                return diff
            ts1, ts2 = r1.request_timestamp, r2.request_timestamp
            if ts1.tzinfo is None:
                ts1 = ts1.replace(tzinfo=timezone.utc)
            if ts2.tzinfo is None:
                ts2 = ts2.replace(tzinfo=timezone.utc)
            return abs((ts1 - ts2).total_seconds()) / 60.0

        def _trip_km(r) -> float:
            rm = request_metrics.get(r.id) or {}
            km = rm.get("trip_km")
            if km is None:
                km = haversine(
                    r.pickup_lat, r.pickup_lng, r.drop_lat, r.drop_lng
                )
            return km

        # Evaluate all pairs and average factor scores
        factor_accum: Dict[str, List[float]] = {k: [] for k in FACTOR_KEYS}
        details: Dict[str, Any] = {}
        delay_accum: List[float] = []
        overlap_scores: List[float] = []

        pairs = [(requests[i], requests[j])
                 for i in range(len(requests))
                 for j in range(i + 1, len(requests))]

        for r1, r2 in pairs:
            # 1. Pickup Proximity — mirror of pickup_distance_score
            pickup_km = _pickup_km(r1, r2)
            if pickup_km >= max_radius:
                p_score = 0.0
            else:
                p_score = max(0.0, 1.0 - (pickup_km / max_radius))
            p_score = round(p_score, 4)
            factor_accum["pickup"].append(p_score)
            details.setdefault("pickup_distance_m", round(pickup_km * 1000.0, 1))

            # 2. Route Similarity — mirror of route_similarity_score
            #    (direction from destination_similarity_score — no haversine;
            #     overlap proxies share the pickup distance computed above)
            direction = destination_similarity_score(
                r1.pickup_lat, r1.pickup_lng, r1.drop_lat, r1.drop_lng,
                r2.pickup_lat, r2.pickup_lng, r2.drop_lat, r2.drop_lng,
            )
            drop_km = haversine(
                r1.drop_lat, r1.drop_lng, r2.drop_lat, r2.drop_lng
            )
            mid_km = haversine(
                (r1.pickup_lat + r1.drop_lat) / 2.0,
                (r1.pickup_lng + r1.drop_lng) / 2.0,
                (r2.pickup_lat + r2.drop_lat) / 2.0,
                (r2.pickup_lng + r2.drop_lng) / 2.0,
            )
            trip1_km = _trip_km(r1)
            trip2_km = _trip_km(r2)
            avg_len = (trip1_km + trip2_km) / 2.0 if (trip1_km + trip2_km) > 0 else 1.0
            mid_proxy = max(0.0, 1.0 - mid_km / max(avg_len, 0.1))
            pickup_proxy = max(0.0, 1.0 - pickup_km / max(avg_len, 0.1))
            drop_proxy = max(0.0, 1.0 - drop_km / max(avg_len, 0.1))
            overlap = round((mid_proxy + pickup_proxy + drop_proxy) / 3.0, 4)
            if overlap >= 0.7:
                overlap_label = "High"
            elif overlap >= 0.4:
                overlap_label = "Medium"
            else:
                overlap_label = "Low"
            r_score = round((direction + overlap) / 2.0, 4)
            factor_accum["route"].append(r_score)
            details.setdefault("direction_similarity", direction)
            details.setdefault("route_overlap_label", overlap_label)
            details.setdefault("route_overlap_score", overlap)
            details.setdefault("destination_distance_m", round(drop_km * 1000.0, 1))
            details.setdefault("estimated_travel_time_min", round(
                ((trip1_km + trip2_km) / 2.0) / max(avg_speed, 1.0) * 60.0, 1
            ))
            overlap_scores.append(overlap)

            # 3. Time Compatibility — mirror of time_window_score
            time_diff = _time_diff(r1, r2)
            if time_diff >= max_delay:
                t_score = 0.0
            else:
                t_score = max(0.0, 1.0 - (time_diff / max_delay))
            t_score = round(t_score, 4)
            factor_accum["time"].append(t_score)
            details.setdefault("time_diff_min", round(time_diff, 1))

            # Estimated Delay (used in explanation, not in weighted score) —
            # mirror of score_engine.estimated_delay_score (30 km/h default)
            delay_min = round((pickup_km / 30.0) * 60.0, 1)
            delay_accum.append(delay_min)

        # 4. Capacity (evaluated once across all requests)
        total_demand = sum(r.demand or 1 for r in requests)
        total_weight = sum(r.weight_kg or 0.0 for r in requests)
        cap_score, util_pct, cap_note = vehicle_capacity_score(
            total_demand, total_weight,
            max_capacity=int(rules["max_vehicle_capacity"]),
            max_weight_kg=rules.get("max_weight_kg", 100.0),
        )
        factor_accum["capacity"] = [cap_score]
        details["capacity_note"] = cap_note
        details["capacity_utilization_pct"] = util_pct
        details["total_demand"] = total_demand
        details["total_weight_kg"] = total_weight

        # Provider note (explanation only — CS uses the 5 required factors)
        provider_ids = [r.provider_id or 0 for r in requests]
        if len(set(provider_ids)) == 1:
            prov_note = "Same provider — optimal"
        else:
            prov_note = "Cross-provider batching supported"
        details["provider_note"] = prov_note

        # 5. Priority (evaluated once across all requests)
        prio_list = [r.priority or "Medium" for r in requests]
        pri_score, pri_label = priority_score(prio_list)
        factor_accum["priority"] = [pri_score]
        details["priority_label"] = pri_label

        # ── Aggregate factor scores ───────────────────────────────────────────
        avg_factors: Dict[str, float] = {
            k: (sum(v) / len(v)) if v else 0.0
            for k, v in factor_accum.items()
        }

        # Weighted compatibility score (0–100): CS = Σ wi·fi
        compatibility_pct = weighted_compatibility_score(weights, avg_factors)

        raw_delay = sum(delay_accum) / len(delay_accum) if delay_accum else 0.0
        avg_delay = round(raw_delay, 1)
        details["estimated_delay_min"] = avg_delay

        # ── A-DMFE: extension factors, BQS, confidence, attribution ───────────
        extensions: Dict[str, float] = {}
        batch_score: Optional[float] = None
        confidence: Optional[float] = None
        contributions: Dict[str, float] = {}
        threshold = _get_threshold(db)
        if adaptive:
            from app.dmfe.adaptive.factors import compute_extension_factors
            from app.dmfe.adaptive.decision import (
                effective_threshold,
                compute_confidence,
                batch_quality_score,
                bqs_threshold,
            )
            from app.dmfe.adaptive.xai import factor_contributions
            from app.dmfe.adaptive.learning import LearningEngine as _LE

            # A-DMFE Module 8: scale the estimated delay by the refitted
            # per-corridor multiplier (no-op when refit is off or the
            # corridor is unseen → multiplier 1.0)
            if learning_state and _refit_enabled(db):
                _types = sorted({(r.request_type or "ride").lower() for r in requests})
                _key = "|".join(_types) if _types else "unknown"
                _mult = _LE.corridor_multiplier_from_state(learning_state, _key)
                if _mult != 1.0:
                    avg_delay = round(raw_delay * _mult, 1)
                    details["estimated_delay_min"] = avg_delay
                    details["delay_corridor"] = _key
                    details["delay_multiplier"] = _mult

            # Weather context (existing signal — SimulationScenario.
            # weather_condition captured by the ContextAwarenessEngine).
            # Additive explainability detail; it does not re-weight CS.
            if context is not None:
                _weather = getattr(context, "raw", {}).get("scenario_weather")
                if _weather:
                    details["weather_condition"] = _weather

            pair_overlap = (
                sum(overlap_scores) / len(overlap_scores)
                if overlap_scores else None
            )
            ext_scores, ext_details = compute_extension_factors(
                requests, context, rules, learning_state,
                pair_overlap=pair_overlap,
            )
            extensions = ext_scores
            details.update(ext_details)

            threshold = effective_threshold(threshold, context)
            details["admfe_threshold"] = threshold
            details["admfe_bqs_threshold"] = bqs_threshold(context)

            batch_score = batch_quality_score(
                compatibility_pct, avg_factors, extensions, details,
                rules, n_requests=len(requests),
            )
            details["admfe_batch_score"] = batch_score
            confidence = compute_confidence(
                compatibility_pct, threshold, avg_factors,
                ext_details.get("expected_delay_min", avg_delay), rules,
            )
            details["admfe_confidence"] = confidence
            contributions = factor_contributions(weights, avg_factors)
            details["admfe_contributions"] = contributions

        # ── Build natural-language explanations ───────────────────────────────
        reasons = _build_reasons(avg_factors, details, compatibility_pct, rules)

        # ── A-DMFE: append adaptive rationale (attribution + gates) ───────────
        if adaptive:
            from app.dmfe.adaptive.xai import build_adaptive_reasons

            reasons += build_adaptive_reasons(
                compatibility_pct,
                threshold,
                batch_score or 0.0,
                details.get("admfe_bqs_threshold", 0.55),
                confidence or 0.0,
                contributions,
                extensions,
                details.get("expected_delay_min", avg_delay),
                decided="Compatible" if compatibility_pct >= threshold
                else "Incompatible",
                mode=mode,
            )

        return CompatibilityResult(
            request_ids=[r.id for r in requests],
            compatibility_score=compatibility_pct,
            factor_scores={k: round(v, 3) for k, v in avg_factors.items()},
            factor_details=details,
            reasons=reasons,
            estimated_delay_min=avg_delay,
            weights_used=weights,
            batch_score=batch_score,
            decision_confidence=confidence,
            factor_contributions=contributions,
            extensions=extensions,
            context_profile=context_profile_dict,
            mode=mode,
        )


def _build_reasons(
    factor_scores: Dict[str, float],
    details: Dict[str, Any],
    total_score: float,
    rules: Dict[str, float],
) -> List[str]:
    """Generate ✓/✗ explainability bullets from factor scores and detail values."""
    reasons: List[str] = []

    # Pickup distance
    dist_m = details.get("pickup_distance_m", 0)
    max_radius = rules.get("max_pickup_radius_km", 5.0) * 1000.0
    if dist_m > max_radius:
        reasons.append(f"✗ Pickup distance is too large ({dist_m:.0f} m — beyond {max_radius/1000:.0f} km pickup radius)")
    elif factor_scores.get("pickup", 0) >= 0.6:
        reasons.append(f"✓ Pickup distance is small ({dist_m:.0f} m — within acceptable range)")
    else:
        reasons.append(f"~ Pickup distance is moderate ({dist_m:.0f} m — inside radius but not ideal)")

    # Route similarity (direction + overlap, combined)
    if factor_scores.get("route", 0) >= 0.6:
        reasons.append("✓ Trips share a similar route and direction")
    else:
        reasons.append("✗ Trips follow different routes or directions")

    # Route overlap detail
    overlap = details.get("route_overlap_label", "Low")
    sym = "✓" if overlap in ("High", "Medium") else "✗"
    reasons.append(f"{sym} Route overlap is {overlap}")

    # Time window
    time_diff = details.get("time_diff_min", 0)
    max_delay = rules.get("max_allowed_delay_min", 20.0)
    if time_diff > max_delay:
        reasons.append(f"✗ Request time difference is too large ({time_diff:.1f} min > {max_delay:.0f} min limit)")
    elif factor_scores.get("time", 0) >= 0.6:
        reasons.append(f"✓ Request time difference is acceptable ({time_diff:.1f} min)")
    else:
        reasons.append(f"~ Request time difference is moderate ({time_diff:.1f} min — inside limit but not ideal)")

    # Capacity
    cap_note = details.get("capacity_note", "")
    sym = "✓" if factor_scores.get("capacity", 0) >= 0.3 else "✗"
    reasons.append(f"{sym} Vehicle capacity: {cap_note}")

    # Estimated delay
    delay = details.get("estimated_delay_min", 0)
    if delay <= 5:
        reasons.append(f"✓ Estimated additional delay is minimal ({delay:.1f} min)")
    elif delay <= max_delay:
        reasons.append(f"✓ Estimated additional delay is within limits ({delay:.1f} min)")
    else:
        reasons.append(f"✗ Estimated additional delay is excessive ({delay:.1f} min)")

    # Provider
    prov_note = details.get("provider_note", "")
    sym = "✓" if "Same" in prov_note else "~"
    reasons.append(f"{sym} {prov_note}")

    # Priority
    pri_label = details.get("priority_label", "Medium")
    sym = "✓" if pri_label in ("High", "Medium") else "~"
    reasons.append(f"{sym} Combined request priority is {pri_label}")

    return reasons
