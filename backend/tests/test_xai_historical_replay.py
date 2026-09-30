"""
Regression: XAI historical fidelity.

Audit finding #2 (HIGH): `/api/xai/explanations` recomputed the decision at
query time, contradicting what was actually stored/dispatched (a request
dispatched in a shared trip was recently explained as standalone).

The explanation builder must REPLAY the stored DMFEBatch decision when one
exists (Dispatched / Individual / Rejected), and only live-evaluate requests
with no recorded decision.  Stored engine confidence is used when present;
otherwise the score-derived float is kept but flagged `confidence_fallback`.
"""

from __future__ import annotations

import json

from app.dmfe.compatibility import CompatibilityCalculator
from app.dmfe.models import DMFEBatch
from app.services.xai_service import _generate_explanation_for_request


def _explain(db, req, threshold=60.0):
    return _generate_explanation_for_request(
        db, CompatibilityCalculator(), req, "Test Provider", threshold,
        compute_kwargs=None, trip_by_request=None, batch_by_request=None,
    )


def _stored_batch(db, requests, **overrides):
    defaults = dict(
        batch_code=f"BATCH-{requests[0].id:04d}-{requests[-1].id:04d}",
        request_ids_json=json.dumps([r.id for r in requests]),
        compatibility_score=82.5,
        decision="Compatible",
        status="Dispatched",
        reason_json=json.dumps([
            "ℹ️ Compatibility Score: 82.5%",
            "✓ Driver #1 selected — vehicle #1 (Car, capacity 4)",
        ]),
        factor_scores_json=json.dumps({
            "pickup": 0.90, "time": 0.70, "route": 0.85,
            "capacity": 1.00, "priority": 0.80,
        }),
        factor_details_json=json.dumps({
            "pickup_distance_m": 1500.0, "time_diff_min": 4.2,
        }),
        estimated_delay_min=3.0,
        decision_confidence=85.2,
    )
    defaults.update(overrides)
    b = DMFEBatch(**defaults)
    db.add(b)
    db.flush()
    return b


def test_shared_dispatch_replays_stored_decision(db, make_request, make_trip):
    r1 = make_request()
    r2 = make_request()
    batch = _stored_batch(db, [r1, r2])
    trip = make_trip(requests=[r1, r2], batch=batch, status="Active")
    db.flush()

    exp = _explain(db, r1)

    assert exp.decision == "Compatible for Batching"
    assert exp.status == "Compatible"
    assert exp.factors.overall_compatibility_score == 82.5
    assert exp.batched_with_request_ids == [r2.id]
    # Stored engine confidence, real — not flagged.
    assert exp.confidence_score == 85.2
    assert exp.confidence_fallback is False
    # Impact metrics come from the real dispatched trip.
    assert exp.trip_code == trip.trip_code
    assert exp.trip is not None
    # Stored factor values are replayed, not recomputed.
    assert exp.factors.pickup_distance_score == 90.0
    assert exp.factors.route_similarity_pct == 85.0

    # Explanations for BOTH members agree with the same stored record.
    exp2 = _explain(db, r2)
    assert exp2.decision == "Compatible for Batching"
    assert exp2.batched_with_request_ids == [r1.id]


def test_timeline_uses_real_recorded_timestamps(db, make_request):
    r1 = make_request()
    r2 = make_request()
    batch = _stored_batch(db, [r1, r2])
    db.flush()

    exp = _explain(db, r1)
    evals = [t for t in exp.timeline if t.title == "DMFE Evaluation"]
    assert evals, "timeline must contain DMFE Evaluation"
    recorded = batch.created_at.strftime("%H:%M:%S")
    assert evals[0].timestamp == recorded
    assert "82.5" in evals[0].description


def test_individual_dispatch_replays_as_standalone(db, make_request):
    r = make_request()
    batch = _stored_batch(
        db, [r],
        decision="Individual", status="Individual",
        compatibility_score=0.0,
        reason_json=json.dumps(["Solo trip — no compatible batch found"]),
        decision_confidence=None,  # historical row: no engine confidence
    )
    db.flush()

    exp = _explain(db, r)
    assert exp.decision == "Standalone Direct Routing"
    assert exp.status == "Incompatible"
    assert exp.confidence_score == 70.0          # 70 + 0*0.35, kept float
    assert exp.confidence_fallback is True       # ...but explicitly flagged
    assert "Solo trip" in exp.reason


def test_rejected_batch_blockers_surface_in_reason(db, make_request):
    r1 = make_request()
    r2 = make_request()
    _stored_batch(
        db, [r1, r2],
        decision="Incompatible", status="Rejected",
        compatibility_score=45.0,
        reason_json=json.dumps([
            "ℹ️ Compatibility Score: 45.0%",
            "✗ Compatibility score 45.0 < threshold 60.0",
            "Final Decision: Rejected",
        ]),
    )
    db.flush()

    exp = _explain(db, r1)
    assert exp.decision == "Standalone Direct Routing"
    assert "45.0 < threshold" in exp.reason


def test_live_path_unchanged_when_no_stored_decision(db, make_request):
    """A fresh request with no batch/trip keeps live evaluation."""
    req = make_request()
    db.flush()

    exp = _explain(db, req)
    assert exp.decision == "Standalone Direct Routing"
    assert 0.0 <= exp.confidence_score <= 100.0
    assert exp.confidence_fallback is True   # live estimate, not recorded
    assert exp.factors is not None


def test_stored_decision_immune_to_live_threshold_change(db, make_request, set_config):
    """
    Adaptive-state change immunity.

    A request dispatched under threshold 60 must be replayed identically after
    SystemConfig lowers the threshold to 45 — the recorded decision, status,
    confidence and score must not be rewritten against the new live value.
    """
    r1 = make_request()
    r2 = make_request()
    batch = _stored_batch(
        db, [r1, r2],
        decision="Compatible", status="Dispatched",
        compatibility_score=82.5, decision_confidence=85.2,
    )
    db.flush()

    # Adaptive threshold lowered AFTER the dispatch was recorded.
    set_config("compatibility_threshold", 45.0)

    exp = _explain(db, r1, threshold=45.0)
    assert exp.decision == "Compatible for Batching"
    assert exp.status == "Compatible"
    assert exp.confidence_score == 85.2
    assert exp.confidence_fallback is False
    assert exp.factors.overall_compatibility_score == 82.5
    assert exp.batched_with_request_ids == [r2.id]

    # The replay must not claim the record was judged against ANY live
    # threshold — no fresh comparison is injected at query time.
    assert "threshold" not in exp.decision_summary

    # Same immunity for a recorded rejection replayed under the new threshold.
    r3 = make_request()
    _stored_batch(
        db, [r3],
        decision="Incompatible", status="Rejected",
        compatibility_score=45.0,
        reason_json=json.dumps([
            "ℹ️ Compatibility Score: 45.0%",
            "✗ Compatibility score 45.0 < threshold 60.0",
            "Final Decision: Rejected",
        ]),
    )
    db.flush()

    rej = _explain(db, r3, threshold=45.0)
    assert rej.decision == "Standalone Direct Routing"
    # Replayed verbatim from the RECORDED reason (still "threshold 60.0"),
    # not recomputed against the live 45.
    assert "45.0 < threshold 60.0" in rej.reason
    assert "threshold" not in rej.decision_summary