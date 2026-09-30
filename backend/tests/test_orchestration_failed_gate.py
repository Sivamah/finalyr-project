"""
Regression: orchestration `failed_gate` must reflect the REAL rejected gate.

Audit finding #5 (MINOR): `_batch_to_result` used a fragile keyword scan that
mislabelled 32 of 40 sampled rejects (e.g. capacity/weight rejections landed
on the "rejected"/"bqs" keywords).  The true gate is always the FIRST "✗"
reason recorded at decision time; read it directly.
"""

from __future__ import annotations

import json

from app.api.routes.orchestration import _batch_to_result
from app.dmfe.models import DMFEBatch


def _rejected_batch(db, reasons):
    b = DMFEBatch(
        batch_code="BATCH-REJ-1",
        request_ids_json="[1, 2]",
        compatibility_score=45.0,
        decision="Incompatible",
        status="Rejected",
        reason_json=json.dumps(reasons),
        factor_scores_json="{}",
        factor_details_json="{}",
    )
    db.add(b)
    db.flush()
    return b


def test_failed_gate_score_below_threshold(db):
    b = _rejected_batch(db, [
        "ℹ️ Compatibility Score: 45.0%",
        "✗ Compatibility score 45.0 < threshold 70.0",
        "Final Decision: Rejected",
    ])
    result = _batch_to_result(b, db)
    assert result["failed_gate"] == "✗ Compatibility score 45.0 < threshold 70.0"


def test_failed_gate_capacity(db):
    b = _rejected_batch(db, [
        "✗ Combined demand/weight exceeds vehicle capacity",
        "Final Decision: Rejected",
    ])
    result = _batch_to_result(b, db)
    assert "capacity" in result["failed_gate"].lower()


def test_failed_gate_weight_limit(db):
    b = _rejected_batch(db, [
        "✗ Combined weight 120.0 kg exceeds the 100 kg system limit",
        "Final Decision: Rejected",
    ])
    result = _batch_to_result(b, db)
    assert "weight" in result["failed_gate"].lower()
    # must NOT fall through to the "Final Decision: Rejected" line
    assert result["failed_gate"] != "Final Decision: Rejected"


def test_failed_gate_no_driver(db):
    b = _rejected_batch(db, [
        "✗ No feasible driver/vehicle pair within 25 km of the pickups "
        "(0 Available driver(s), 0 fitting vehicle(s) checked)",
        "Final Decision: Rejected",
    ])
    result = _batch_to_result(b, db)
    assert "No feasible driver" in result["failed_gate"]


def test_failed_gate_bqs(db):
    b = _rejected_batch(db, [
        "✗ Batch quality score 0.30 < BQS threshold 0.55 "
        "(poor utilisation/savings)",
        "Final Decision: Rejected",
    ])
    result = _batch_to_result(b, db)
    assert "Batch quality score" in result["failed_gate"]
    assert "BQS threshold" in result["failed_gate"]


def test_failed_gate_no_blockers_defaults(db):
    b = _rejected_batch(db, ["ℹ️ no gate recorded"])
    result = _batch_to_result(b, db)
    assert result["failed_gate"] == "Incompatible constraints"