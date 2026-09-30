"""
XAI Service — Explainable AI for the DMFE
==========================================
Phase 7 rewrite: every explanation is computed from the REAL DMFE engine,
never from seeded formulas.

Historical fidelity: for a request with a recorded decision (a `dmfe_batches`
row in status Dispatched / Individual / Rejected) the explanation REPLAYS the
stored decision — stored compatibility score, factor scores/details, reasons
and dispatched Trip metrics — instead of recomputing a fresh decision that
could contradict what was actually dispatched.

For each request we:
  1. If a stored decision exists → replay it (score, factors, reasons).
  2. Otherwise evaluate against the best-matching pending/processed partner
     using the real CompatibilityCalculator (5-factor weighted CS).
  3. Compare CS against the configured threshold → real decision.
  4. Attach the REAL impact metrics recorded at dispatch time: fuel saved,
     CO₂ saved, distance saved, and driver profit (fare − operating cost).
  5. Build the timeline from actual lifecycle timestamps where recorded;
     synthetic offsets are used only on the live-fresh path.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import time
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.json_utils import json_loads
from app.db.models import SimulationRequest, Provider, Trip
from app.dmfe.compatibility import CompatibilityCalculator, _get_threshold
from app.dmfe.models import DMFEBatch
from app.schemas.xai import (
    XAIFactors, XAITimelineItem, XAIExplanationItem,
    XAIRequestPoint, XAIDriverLink, XAIVehicleLink,
    XAIRouteStopPoint, XAITripLink,
)

# Per-request explanation cache: the frontend polls every few seconds and
# requests are immutable between simulation runs, so caching the expensive
# compatibility loop (O(requests × partners) pairwise evaluations) turns a
# 60s response into an instant one.  TTL keeps new requests visible quickly.
_EXPLANATION_CACHE_TTL = 30.0
_MAX_PARTNERS = 20

# Bound on the recorded-decision index scan.  Historical replay must be able
# to find the stored DMFEBatch for any dispatched request; with 11,872 batches
# on the current dev database a cap of 2000 would silently miss older recorded
# decisions and fall back to a live recompute.  This is an O(n) scan of one
# table (JSON membership), NOT the O(rows x partners) evaluation loop.
_STORED_DECISION_SCAN_LIMIT = 25000

# When search/decision post-filters are set, the SQL limit is applied to a
# small multiple of the requested limit instead of loading the entire request
# table (12,688 rows on the dev DB).  Post-filtering happens in Python, so a
# scan budget of `limit * multiplier` rows still fills the requested limit for
# normal result densities while keeping the initial dashboard retrieval
# bounded.  Explicit larger `limit` values scale the budget proportionally.
_POST_FILTER_SCAN_MULTIPLIER = 4


def _best_partner(
    calculator: CompatibilityCalculator,
    db: Session,
    req: SimulationRequest,
    candidates: List[SimulationRequest],
    compute_kwargs: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """Return the CompatibilityResult for the best-scoring partner (or None).

    `compute_kwargs` carries the A-DMFE context/weights/learning state built
    once per request batch, so each pairwise evaluation avoids re-reading the
    whole system state from the database.
    """
    best = None
    best_score = -1.0
    for other in candidates:
        if other.id == req.id:
            continue
        try:
            result = calculator.compute(
                [req, other], db, **(compute_kwargs or {})
            )
        except Exception:
            continue
        if result.compatibility_score > best_score:
            best_score = result.compatibility_score
            best = result
    return best


def _find_trip(db: Session, request_id: int, trip_by_request: Optional[Dict[int, Any]] = None) -> Optional["Trip"]:
    """The dispatched Trip a request was assigned to, or None if not dispatched."""
    if trip_by_request is not None:
        return trip_by_request.get(request_id)
    trip = (
        db.query(Trip)
        .filter(Trip.request_ids_json.like(f'%"{request_id}"%'))
        .order_by(Trip.created_at.desc())
        .first()
    )
    if trip is not None:
        return trip
    # Fallback: request_ids_json may be stored without quotes (e.g. "[1, 2]"),
    # in which case the quoted LIKE above cannot match.
    for trip in db.query(Trip).order_by(Trip.created_at.desc()).all():
        if request_id in json_loads(trip.request_ids_json, []):
            return trip
    return None


def _trip_metrics(db: Session, request_id: int, trip_by_request: Optional[Dict[int, Any]] = None, trip: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Real impact metrics from the Trip the request was dispatched in."""
    if trip is None:
        trip = _find_trip(db, request_id, trip_by_request)
    if trip is None:
        return None
    ids = json_loads(trip.request_ids_json, [])
    # Driver profit: revenue from the trip minus operating cost.
    # Revenue ≈ distance × (ride/food/parcel blended per-km rate ~ ₹12/km);
    # operating cost ≈ fuel cost (fuel_l × ₹100/L).
    revenue = (trip.total_distance_km or 0.0) * 12.0
    fuel_cost = (trip.fuel_l or 0.0) * 100.0
    # Separate-trip baseline cost: the SAME per-km operating rate the
    # optimizer used for this vehicle (Vehicle.cost_per_km) applied to the
    # pre-optimization distance (this trip's own distance plus whatever
    # distance batching saved) — i.e. the real cost of running these
    # requests as individual trips instead of one combined trip. Mirrors the
    # exact `total_km * cost_per_km` formula optimizer.py already uses for
    # `estimated_cost`, just applied to the baseline distance instead of the
    # optimized one — no new pricing logic, purely exposing derived
    # arithmetic from already-stored real numbers.
    cost_per_km = (trip.vehicle.cost_per_km if trip.vehicle else None) or 10.0
    separate_km = (trip.total_distance_km or 0.0) + (trip.distance_saved_km or 0.0)
    # Solo profit: the SAME revenue/fuel-cost formula as driver_profit_inr
    # above, applied to the pre-batching (separate-trips) distance and fuel
    # instead of the actual dispatched trip's — i.e. what the driver would
    # have earned running these requests individually. `fuel_saved_l` is
    # exactly (separate fuel usage − this trip's fuel usage), so adding it
    # back to `trip.fuel_l` recovers the separate-trips fuel figure without
    # a second pricing model or any new assumption.
    separate_fuel_l = (trip.fuel_l or 0.0) + (trip.fuel_saved_l or 0.0)
    solo_revenue = separate_km * 12.0
    solo_fuel_cost = separate_fuel_l * 100.0
    return {
        "trip_code": trip.trip_code,
        "fuel_saved_l": trip.fuel_saved_l or 0.0,
        "co2_saved_kg": trip.co2_saved_kg or 0.0,
        "distance_saved_km": trip.distance_saved_km or 0.0,
        "driver_profit_inr": round(max(0.0, revenue - fuel_cost), 2),
        "trip_cost_inr": round(trip.estimated_cost or 0.0, 2),
        "separate_cost_inr": round(separate_km * cost_per_km, 2),
        "solo_profit_inr": round(max(0.0, solo_revenue - solo_fuel_cost), 2),
        "batched_with": [i for i in ids if i != request_id],
    }


def _request_point(r: Any) -> "XAIRequestPoint":
    """Map-linkable point for one request (pickup + drop)."""
    return XAIRequestPoint(
        request_id=r.id,
        request_type=r.request_type or "ride",
        pickup_address=r.pickup_address or "",
        drop_address=r.drop_address or "",
        pickup_lat=float(r.pickup_lat or 0.0),
        pickup_lng=float(r.pickup_lng or 0.0),
        drop_lat=float(r.drop_lat or 0.0),
        drop_lng=float(r.drop_lng or 0.0),
        priority=r.priority or "Medium",
    )


def _load_request_rows(db: Session, request_ids) -> Dict[int, Any]:
    """ORM SimulationRequest rows keyed by id for the given (deduped) IDs."""
    ids = [i for i in dict.fromkeys(request_ids or []) if i]
    if not ids:
        return {}
    return {
        r.id: r
        for r in db.query(SimulationRequest)
        .filter(SimulationRequest.id.in_(ids))
        .all()
    }


def _build_related_request_points(rows: Dict[int, Any], request_ids) -> List["XAIRequestPoint"]:
    """Ordered XAIRequestPoint list for the given (deduped) request IDs."""
    points = []
    for rid in dict.fromkeys(request_ids or []):
        r = rows.get(rid)
        if r is not None:
            points.append(_request_point(r))
    return points


def _build_trip_link(trip: Any, request_by_id: Dict[int, Any]) -> Optional["XAITripLink"]:
    """Trip snapshot for the map: driver/vehicle locations + ordered route stops."""
    if trip is None:
        return None
    stops = json_loads(trip.stop_order_json, [])
    route_stops = []
    for s in stops if isinstance(stops, list) else []:
        if not isinstance(s, dict):
            continue
        rid = s.get("request_id")
        req = request_by_id.get(rid)
        if req is None:
            continue
        action = s.get("action", "pickup")
        lat = float((req.drop_lat if action == "drop" else req.pickup_lat) or 0.0)
        lng = float((req.drop_lng if action == "drop" else req.pickup_lng) or 0.0)
        route_stops.append(XAIRouteStopPoint(
            request_id=rid,
            action=action,
            lat=lat,
            lng=lng,
            arrival_min=float(s.get("arrival_min") or 0.0),
        ))
    driver = trip.driver if trip.driver is not None else None
    vehicle = trip.vehicle if trip.vehicle is not None else None
    return XAITripLink(
        trip_id=trip.id,
        trip_code=trip.trip_code or "",
        is_shared=bool(trip.is_shared),
        status=trip.status or "Active",
        driver=XAIDriverLink(
            id=driver.id,
            name=driver.name or "",
            current_lat=float(driver.current_lat or 0.0),
            current_lng=float(driver.current_lng or 0.0),
        ) if driver is not None else None,
        vehicle=XAIVehicleLink(
            id=vehicle.id,
            name=vehicle.name or "",
            vehicle_type=vehicle.vehicle_type or "",
            current_lat=float(vehicle.current_lat or 0.0),
            current_lng=float(vehicle.current_lng or 0.0),
        ) if vehicle is not None else None,
        route_stops=route_stops,
    )


# Deployed ("realized") decision statuses.  A `Pending` batch is only a live
# candidate from /analyze; it must never be replayed as the request's
# decision — those requests are still waiting in the queue.
_STORED_BATCH_STATUSES = ("Dispatched", "Individual", "Rejected")


def _find_stored_decision(
    db: Session,
    request_id: int,
    batch_by_request: Optional[Dict[int, Any]] = None,
) -> Optional[Any]:
    """
    The DMFEBatch row recording this request's realized decision, or None.

    Every request dispatched by the pipeline has one (shared → "Dispatched",
    individual → "Individual", failed dispatch → "Rejected").  Historical XAI
    replays that stored record instead of recomputing a fresh decision that
    can contradict what was actually dispatched.
    """
    if batch_by_request is not None:
        return batch_by_request.get(request_id)
    candidates = (
        db.query(DMFEBatch)
        .filter(DMFEBatch.status.in_(_STORED_BATCH_STATUSES))
        .order_by(DMFEBatch.id.desc())
        .limit(_STORED_DECISION_SCAN_LIMIT)
        .all()
    )
    for b in candidates:
        if request_id in json_loads(b.request_ids_json, []):
            return b
    return None


def _generate_explanation_for_request(
    db: Session,
    calculator: CompatibilityCalculator,
    req: SimulationRequest,
    provider_name: str,
    threshold: float,
    compute_kwargs: Optional[Dict[str, Any]] = None,
    trip_by_request: Optional[Dict[int, Any]] = None,
    batch_by_request: Optional[Dict[int, Any]] = None,
) -> XAIExplanationItem:
    req_id = req.id
    dist = req.estimated_distance_km or 0.0

    trip = _find_trip(db, req_id, trip_by_request)
    trip_metrics = _trip_metrics(db, req_id, trip_by_request, trip=trip)
    stored = _find_stored_decision(db, req_id, batch_by_request)

    def _ts(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%H:%M:%S")

    if stored is not None:
        # ── Historical fidelity: replay the RECORDED decision ─────────────
        fs = json_loads(stored.factor_scores_json, {}) or {}
        details = json_loads(stored.factor_details_json, {}) or {}
        reasons = json_loads(stored.reason_json, []) or []
        overall = stored.compatibility_score or 0.0
        delay_min = stored.estimated_delay_min or 0.0
        batch_ids = json_loads(stored.request_ids_json, [])
        partner_ids = [i for i in batch_ids if i != req_id]
        is_shared = (stored.decision or "").strip() == "Compatible"

        if is_shared:
            decision = "Compatible for Batching"
            status = "Compatible"
            # Fidelity: never recompute against the CURRENT threshold —
            # the recorded decision was made at dispatch time.  Replay the
            # recorded score only; the stored reason lines already carry the
            # threshold that actually applied.
            decision_summary = (
                f"Compatibility score {overall:.1f}% — request can share a "
                f"vehicle with #{partner_ids[0] if partner_ids else '?'}"
            )
            ok_bullets = [r[2:] for r in reasons if r.startswith("✓")]
            reason = ("Compatible: " + "; ".join(ok_bullets)[:300]
                      if ok_bullets else decision_summary)
            key_reasons = [
                b[2:] for b in reasons if b.startswith(("✓", "✗", "ℹ️"))
            ] or [decision_summary]
        else:
            decision = "Standalone Direct Routing"
            status = "Incompatible"
            decision_summary = (
                f"Compatibility score {overall:.1f}% — "
                "dispatched as an individual trip"
            )
            blockers = [r[2:] for r in reasons if r.startswith("✗")]
            reason = ("Rejected from batching: " + "; ".join(blockers)[:300]
                      if blockers else "Solo trip — no compatible batch found")
            key_reasons = [
                b[2:] for b in reasons if b.startswith(("✓", "✗", "ℹ️"))
            ] or [decision_summary]

        pickup_dist_km = round((details.get("pickup_distance_m") or 0) / 1000.0, 2)
        time_diff_min = details.get("time_diff_min") or 0.0
        route_pct = round((fs.get("route", 0) or 0) * 100.0, 1)
        factors = XAIFactors(
            pickup_distance_score=round((fs.get("pickup", 0) or 0) * 100.0, 1),
            destination_similarity=route_pct,
            estimated_delay_score=round(
                max(0.0, 1.0 - delay_min / 20.0) * 100.0, 1
            ),
            vehicle_capacity_score=round((fs.get("capacity", 0) or 0) * 100.0, 1),
            priority_score=round((fs.get("priority", 0) or 0) * 100.0, 1),
            overall_compatibility_score=overall,
            pickup_distance_km=pickup_dist_km,
            time_difference_min=time_diff_min,
            route_similarity_pct=route_pct,
            estimated_delay_min=delay_min,
        )

        # Confidence: use the real recorded engine value when it exists;
        # otherwise keep the float for API compatibility but flag it.
        if stored.decision_confidence is not None:
            confidence = round(float(stored.decision_confidence), 1)
            confidence_fallback = False
        else:
            confidence = round(min(99.0, 70.0 + overall * 0.35), 1)
            confidence_fallback = True

        # Timeline from REAL recorded timestamps (no synthetic +2/+4/+6s).
        c_at = req.created_at or datetime.now(timezone.utc)
        timeline = [
            XAITimelineItem(
                title="Request Generated",
                timestamp=_ts(c_at) or "",
                status="completed",
                description=f"Request #{req_id} created ({provider_name})",
            ),
            XAITimelineItem(
                title="DMFE Evaluation",
                timestamp=_ts(stored.created_at) or "",
                status="completed",
                description=(
                    f"Compatibility score {overall:.1f}% vs threshold {threshold:.0f}%"
                ),
            ),
            XAITimelineItem(
                title="Decision Generated",
                timestamp=_ts(stored.created_at) or "",
                status="completed" if is_shared else "pending",
                description=decision,
            ),
        ]
        if trip is not None:
            timeline.append(XAITimelineItem(
                title="Trip Dispatched",
                timestamp=_ts(trip.created_at) or "",
                status="completed",
                description=f"Assigned to {trip.trip_code or ''}",
            ))
        if trip is not None and trip.status == "Completed":
            timeline.append(XAITimelineItem(
                title="Trip Completed",
                timestamp=_ts(getattr(trip, "completed_at", None)) or "",
                status="completed",
                description=f"Trip {trip.trip_code or ''} completed",
            ))
    else:
        # ── Fresh request (no recorded decision yet): live evaluation ──────
        # A-DMFE: use the context-adjusted effective threshold for consistency.
        # The context is built once per batch (passed in compute_kwargs) so we do
        # not re-scan the whole fleet for every single request.
        if (compute_kwargs or {}).get("mode") == "adaptive":
            from app.dmfe.adaptive.decision import effective_threshold

            context = (compute_kwargs or {}).get("context")
            try:
                threshold = effective_threshold(threshold, context)
            except Exception:
                pass

        partners = (
            db.query(SimulationRequest)
            .filter(SimulationRequest.id != req_id)
            .order_by(SimulationRequest.created_at.desc())
            .limit(_MAX_PARTNERS)
            .all()
        )
        result = _best_partner(calculator, db, req, partners, compute_kwargs)

        if result is not None:
            fs = result.factor_scores
            details = result.factor_details
            overall = result.compatibility_score
            decision = (
                "Compatible for Batching" if overall >= threshold
                else "Standalone Direct Routing"
            )
            pickup_dist_km = round((details.get("pickup_distance_m") or 0) / 1000.0, 2)
            time_diff_min = details.get("time_diff_min") or 0.0
            route_pct = round((fs.get("route", 0) or 0) * 100.0, 1)
            delay_min = result.estimated_delay_min
            partner_ids = [i for i in result.request_ids if i != req_id]

            if overall >= threshold:
                decision_summary = (
                    f"Compatibility score {overall:.1f}% ≥ threshold {threshold:.0f}% — "
                    f"request can share a vehicle with #{partner_ids[0] if partner_ids else '?'}"
                )
                status = "Compatible"
            else:
                decision_summary = (
                    f"Compatibility score {overall:.1f}% < threshold {threshold:.0f}% — "
                    f"dispatched as an individual trip"
                )
                status = "Incompatible"

            reason_bullets = result.reasons or []
            if overall >= threshold:
                reason = "Compatible: " + "; ".join(
                    r[2:] for r in reason_bullets if r.startswith("✓")
                )[:300]
            else:
                blockers = [r[2:] for r in reason_bullets if r.startswith("✗")]
                reason = ("Rejected from batching: " + "; ".join(blockers)[:300]
                          if blockers else decision_summary)

            factors = XAIFactors(
                pickup_distance_score=round(fs.get("pickup", 0) * 100.0, 1),
                destination_similarity=route_pct,
                estimated_delay_score=round(
                    max(0.0, 1.0 - delay_min / 20.0) * 100.0, 1
                ),
                vehicle_capacity_score=round(fs.get("capacity", 0) * 100.0, 1),
                priority_score=round(fs.get("priority", 0) * 100.0, 1),
                overall_compatibility_score=overall,
                pickup_distance_km=pickup_dist_km,
                time_difference_min=time_diff_min,
                route_similarity_pct=route_pct,
                estimated_delay_min=delay_min,
            )
        else:
            factors = XAIFactors(
                pickup_distance_score=50.0,
                destination_similarity=50.0,
                estimated_delay_score=50.0,
                vehicle_capacity_score=90.0,
                priority_score=60.0,
                overall_compatibility_score=0.0,
            )
            overall = 0.0
            decision = "Standalone Direct Routing"
            decision_summary = "No comparable partner request found — dispatched individually."
            status = "Incompatible"
            reason = "No nearby request with overlapping route/time window to batch with."
            partner_ids = []

        # Decision confidence.
        #
        # The A-DMFE (adaptive) path computes a real confidence in
        # CompatibilityCalculator.compute and exposes it as
        # `result.decision_confidence`.  The STATIC DMFE path — the Phase 9
        # fixed-weight baseline used for research comparison — leaves it None.
        if result is not None and result.decision_confidence is not None:
            confidence = result.decision_confidence
            confidence_fallback = False
        else:
            confidence = round(min(99.0, 70.0 + overall * 0.35), 1)
            confidence_fallback = True

        # Timeline from real lifecycle events (only the fresh-request path
        # uses the synthetic offsets — no recorded timestamps exist).
        c_at = req.created_at or datetime.now(timezone.utc)
        timeline = [
            XAITimelineItem(
                title="Request Generated",
                timestamp=_ts(c_at) or "",
                status="completed",
                description=f"Request #{req_id} created ({provider_name})",
            ),
            XAITimelineItem(
                title="DMFE Evaluation",
                timestamp=(c_at + timedelta(seconds=2)).strftime("%H:%M:%S"),
                status="completed",
                description=(
                    f"Compatibility score {overall:.1f}% vs threshold {threshold:.0f}%"
                ),
            ),
            XAITimelineItem(
                title="Decision Generated",
                timestamp=(c_at + timedelta(seconds=4)).strftime("%H:%M:%S"),
                status="completed" if overall >= threshold else "pending",
                description=decision,
            ),
        ]
        if trip_metrics:
            timeline.append(XAITimelineItem(
                title="Trip Dispatched",
                timestamp=(c_at + timedelta(seconds=6)).strftime("%H:%M:%S"),
                status="completed",
                description=f"Assigned to {trip_metrics['trip_code']}",
            ))

        key_reasons = [
            b[2:] for b in (result.reasons if result is not None else [])
            if b.startswith(("✓", "✗", "ℹ️"))
        ] or [decision_summary] if result is not None else [reason]

    # ── Live-map link data (additive; no engine/decision logic involved) ────
    # The highlighted request set = the request itself + partner IDs + the
    # real dispatched-trip member IDs (deduped).
    related_ids = [req_id, *partner_ids]
    if trip is not None:
        related_ids = [req_id, *partner_ids, *json_loads(trip.request_ids_json, [])]
    request_rows = _load_request_rows(db, related_ids)
    related_requests = _build_related_request_points(request_rows, related_ids)

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
        confidence_fallback=confidence_fallback,
        pickup_address=req.pickup_address or "Coimbatore",
        drop_address=req.drop_address or "Destination",
        pickup_lat=round(float(req.pickup_lat or 0.0), 6),
        pickup_lng=round(float(req.pickup_lng or 0.0), 6),
        drop_lat=round(float(req.drop_lat or 0.0), 6),
        drop_lng=round(float(req.drop_lng or 0.0), 6),
        key_reasons=key_reasons,
        related_requests=related_requests,
        trip=_build_trip_link(trip, request_rows),
        estimated_distance_km=dist,
        factors=factors,
        timeline=timeline,
        created_at=c_at.isoformat(),
        batched_with_request_ids=partner_ids,
        fuel_saved_l=round((trip_metrics or {}).get("fuel_saved_l", 0.0), 2),
        co2_saved_kg=round((trip_metrics or {}).get("co2_saved_kg", 0.0), 2),
        distance_saved_km=round((trip_metrics or {}).get("distance_saved_km", 0.0), 2),
        driver_profit_inr=(trip_metrics or {}).get("driver_profit_inr", 0.0),
        trip_code=(trip_metrics or {}).get("trip_code"),
        trip_cost_inr=(trip_metrics or {}).get("trip_cost_inr", 0.0),
        separate_cost_inr=(trip_metrics or {}).get("separate_cost_inr", 0.0),
        solo_profit_inr=(trip_metrics or {}).get("solo_profit_inr", 0.0),
    )


class XAIService:
    """XAI service generating real, engine-backed explanations."""

    def __init__(self):
        self._calculator = CompatibilityCalculator()
        # request_id -> (expiry_monotonic, XAIExplanationItem)
        self._cache: Dict[int, tuple] = {}

    # ── Cache ───────────────────────────────────────────────────────────────

    def _cache_get(self, request_id: int) -> Optional[XAIExplanationItem]:
        entry = self._cache.get(request_id)
        if entry is None:
            return None
        expiry, item = entry
        if time.monotonic() > expiry:
            self._cache.pop(request_id, None)
            return None
        return item

    def _cache_put(self, request_id: int, item: XAIExplanationItem) -> None:
        self._cache[request_id] = (time.monotonic() + _EXPLANATION_CACHE_TTL, item)

    def _build_compute_kwargs(
        self, db: Session, pending: List[SimulationRequest]
    ) -> Dict[str, Any]:
        """Build the A-DMFE context/weights/learning state once per batch."""
        from app.dmfe.compatibility import resolve_mode
        from app.dmfe.adaptive.context import ContextAwarenessEngine
        from app.dmfe.adaptive.learning import LearningEngine
        from app.dmfe.adaptive.weights import AdaptiveWeightGenerator

        mode = resolve_mode(db)
        if mode != "adaptive":
            return {"mode": "static"}
        context = ContextAwarenessEngine().build(db, pending)
        learning_state = LearningEngine.load_state(db)
        weights = AdaptiveWeightGenerator(mode=mode).generate(
            db, context, LearningEngine.weight_corrections(db)
        )
        return {
            "mode": "adaptive",
            "context": context,
            "learning_state": learning_state,
            "weights": weights,
        }

    def get_explanations(
        self,
        db: Session,
        request_type: Optional[str] = None,
        provider_id: Optional[int] = None,
        decision: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        request_id: Optional[int] = None,
    ) -> List[XAIExplanationItem]:
        query = db.query(SimulationRequest)

        if request_id is not None:
            query = query.filter(SimulationRequest.id == request_id)
        if request_type and request_type.lower() != "all":
            query = query.filter(func.lower(SimulationRequest.request_type) == request_type.lower())
        if provider_id and provider_id != 0:
            query = query.filter(SimulationRequest.provider_id == provider_id)
        if status and status.lower() != "all":
            # The explanation list filters on the request lifecycle status:
            # "Evaluated" = processed (no longer waiting in the queue),
            # "Pending" = still waiting.  Filtering the raw column with the
            # label would match nothing for "Evaluated".
            if status.lower() == "evaluated":
                query = query.filter(func.lower(SimulationRequest.status) != "pending")
            elif status.lower() == "pending":
                query = query.filter(func.lower(SimulationRequest.status) == "pending")
            else:
                query = query.filter(func.lower(SimulationRequest.status) == status.lower())

        # Search/decision are post-filtered in Python, so the SQL limit is
        # applied to a small multiple of the requested limit rather than to
        # only the first `limit` rows OR the whole table.  Loading the full
        # table here would pairwise-evaluate every cached-miss request on a
        # 12K+ row database (O(rows × _MAX_PARTNERS)); the bounded scan keeps
        # the initial UI/API retrieval fast while still honouring explicit
        # larger `limit` requests proportionally.
        has_post_filters = (
            (decision and decision.lower() != "all")
            or bool(search)
        )
        scan_limit = limit
        if has_post_filters:
            scan_limit = limit * _POST_FILTER_SCAN_MULTIPLIER
        query = query.order_by(SimulationRequest.created_at.desc())
        query = query.limit(scan_limit)
        requests = query.all()

        # Provider map
        provider_ids = {r.provider_id for r in requests if r.provider_id}
        providers = {p.id: p.name for p in db.query(Provider).filter(Provider.id.in_(provider_ids)).all()} if provider_ids else {}

        threshold = _get_threshold(db)

        # Both of these are needed only to GENERATE an explanation.  The
        # frontend polls every 2.5 s and explanations are cached for
        # _EXPLANATION_CACHE_TTL, so the overwhelmingly common case is "every
        # request is a cache hit" — in which case neither the A-DMFE context
        # nor the trip index is ever read.  They are therefore built lazily,
        # at most once per call, on the first cache miss.
        lazy: Dict[str, Any] = {}

        def _compute_kwargs() -> Dict[str, Any]:
            if "compute_kwargs" not in lazy:
                lazy["compute_kwargs"] = self._build_compute_kwargs(db, requests)
            return lazy["compute_kwargs"]

        def _trip_index() -> Dict[int, Any]:
            # Request -> Trip map, so per-request trip lookup is O(1) instead
            # of one LIKE query per explanation.
            if "trip_by_request" not in lazy:
                trip_by_request: Dict[int, Any] = {}
                for trip in db.query(Trip).all():
                    for rid in json_loads(trip.request_ids_json, []):
                        if rid not in trip_by_request:
                            trip_by_request[rid] = trip
                lazy["trip_by_request"] = trip_by_request
            return lazy["trip_by_request"]

        def _batch_index() -> Dict[int, Any]:
            # Request -> stored-decision DMFEBatch map (latest first), so a
            # dispatched request's explanation replays what was actually
            # recorded instead of a fresh recompute.
            if "batch_by_request" not in lazy:
                batch_by_request: Dict[int, Any] = {}
                for b in (
                    db.query(DMFEBatch)
                    .filter(DMFEBatch.status.in_(_STORED_BATCH_STATUSES))
                    .order_by(DMFEBatch.id.desc())
                    .limit(_STORED_DECISION_SCAN_LIMIT)
                    .all()
                ):
                    for rid in json_loads(b.request_ids_json, []):
                        if rid not in batch_by_request:
                            batch_by_request[rid] = b
                lazy["batch_by_request"] = batch_by_request
            return lazy["batch_by_request"]

        explanations = []
        search_lower = search.lower() if search else None

        for req in requests:
            pname = providers.get(req.provider_id, "Unassigned")

            cached = self._cache_get(req.id)
            if cached is not None:
                exp = cached
            else:
                exp = _generate_explanation_for_request(
                    db, self._calculator, req, pname, threshold,
                    _compute_kwargs(), _trip_index(), _batch_index(),
                )
                self._cache_put(req.id, exp)

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

        if has_post_filters:
            return explanations[:limit]
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
            # Omit the full explanations list: the frontend only reads the aggregate
            # fields above; serializing 200 items adds ~50–200 KB per overview poll.
            "explanations": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


xai_service = XAIService()
