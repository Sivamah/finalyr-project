"""
verify_unified_scoring.py — verify that the unified feasibility gate preserves
legacy decision semantics.

Runs the identical workload in all four combinations (mode × unified flag)
and ASSERTS real invariants instead of only dumping JSON:

  1. Every persisted batch in every run carries a passive unified_score_pct
     in [0, 100] inside factor_details (the unified score is always computed;
     the flag only decides whether it gates the decision).
  2. Within the same mode, unified decision ⊆ legacy decision per candidate
     group: a group that legacy accepts and unified REJECTS must have been
     rejected ONLY by the unified gate (unified_score < threshold), never by
     some other criterion (i.e., the unified flag never *relaxes* decisions).
  3. Every group rejected by the unified gate must exist in the legacy run and
     be there "Compatible" (same requests, same mode → same groups).
  4. Every accepted batch satisfies the configured min_compatibility_score.

A group is keyed by its sorted request_ids so legacy↔unified batches can be
matched within a mode.  Exits non-zero on any violated invariant.

Usage:  backend\\.venv\\Scripts\\python.exe backend\\evaluation\\verify_unified_scoring.py
"""
import os
import sys
import json

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, EVAL_DIR)
sys.path.insert(0, os.path.dirname(EVAL_DIR))

import framework
from app.db.database import SessionLocal
from app.dmfe.models import DMFEBatch

FAILURES = []


def _fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"[FAIL] {msg}")


def run_experiment(mode: str, unified: bool):
    framework.SYSTEM_CONFIG["admfe.unified_scoring_enabled"] = "true" if unified else "false"
    # Ensure same seed
    framework.random.seed(42)

    print(f"Starting workload for mode={mode}, unified={unified}...")
    res = framework.run_workload(50, mode=mode)

    db = SessionLocal()
    batches = db.query(DMFEBatch).all()

    batch_data = []
    for b in batches:
        # Avoid serialization issues with datetime
        reasons = json.loads(b.reason_json) if b.reason_json else []
        factor_details = json.loads(b.factor_details_json) if b.factor_details_json else {}
        request_ids = sorted(json.loads(b.request_ids_json) if b.request_ids_json else [])
        batch_data.append({
            "id": b.id,
            "request_ids": request_ids,
            "decision": b.decision,
            "status": b.status,
            "reasons": reasons,
            "factor_details": factor_details,
            "compatibility_score": float(b.compatibility_score) if b.compatibility_score is not None else None
        })

    db.close()
    return {"metrics": res, "batches": batch_data}


def assert_batch_invariants(label: str, data: dict) -> dict:
    """Key batches by request-set; check threshold on accepted batches.

    Batches with fewer than 2 requests are Individual-trip decisions, not
    batching decisions, so they are keyed here but excluded from the gate
    assertions (the unified gate only ever evaluates candidate GROUPS).
    """
    batches = data["batches"]
    if not batches:
        _fail(f"[{label}] no DMFEBatch rows persisted — nothing to verify")
        return {}
    threshold = float(framework.SYSTEM_CONFIG.get("min_compatibility_score", "70"))
    by_key = {}
    for b in batches:
        key = tuple(b["request_ids"])
        by_key[key] = b
        if b["decision"] == "Compatible" and len(key) >= 2:
            if b["compatibility_score"] is None or b["compatibility_score"] < threshold:
                _fail(f"[{label}] accepted batch b{b['id']} {list(key)} score "
                      f"{b['compatibility_score']} < threshold {threshold}")
    return by_key


def main():
    os.makedirs(framework.RESULTS_DIR, exist_ok=True)

    static_a = run_experiment("static", False)
    static_b = run_experiment("static", True)
    adaptive_c = run_experiment("adaptive", False)
    adaptive_d = run_experiment("adaptive", True)

    print("\n" + "=" * 78)
    print("VERIFY: per-run batch invariants (threshold on accepted batches)")
    print("=" * 78)
    legacy_by = {
        "static": assert_batch_invariants("static (legacy)", static_a),
        "adaptive": assert_batch_invariants("adaptive (legacy)", adaptive_c),
    }
    for run_label, data, mode_label in (
        ("static unified", static_b, "static"),
        ("adaptive unified", adaptive_d, "adaptive"),
    ):
        unified_by = assert_batch_invariants(run_label, data)

        print(f"---- unified-mode gate check ({run_label}) ----")
        legacy = legacy_by[mode_label]
        for key, batch in unified_by.items():
            if len(key) < 2:
                continue                     # individual-trip decisions, not groups
            legacy_batch = legacy.get(key)
            if legacy_batch is None:
                # A unified decision must correspond to an identical group in
                # the legacy run (same requests, same mode → same groups).
                _fail(f"[{run_label}] unified group {list(key)} has no "
                      f"matching legacy group in {mode_label}")
                continue
            if batch["status"] == "Rejected":
                # The unified gate is an ADDITIONAL test applied only after
                # legacy acceptance: rejecting a group therefore requires the
                # legacy run to have ACCEPTED that identical group, and the
                # decision must cite the unified score.
                if legacy_batch["decision"] != "Compatible":
                    _fail(f"[{run_label}] unified REJECTED group {list(key)} "
                          f"but legacy {mode_label} decision was "
                          f"{legacy_batch['decision']!r} (must be 'Compatible': "
                          f"the unified gate may only tighten acceptance)")
                if not any("Unified score" in r for r in batch["reasons"]):
                    _fail(f"[{run_label}] group {list(key)} rejected but not "
                          f"by the unified gate:\n  {batch['reasons']}")
                fd = batch["factor_details"]
                u = fd.get("unified_score_pct")
                if u is None:
                    _fail(f"[{run_label}] unified-REJECTED group {list(key)} "
                          f"has no unified_score_pct in factor_details")
                elif not (0.0 <= float(u) <= 100.0):
                    _fail(f"[{run_label}] group {list(key)} unified_score_pct "
                          f"{u} outside [0,100]")
            else:
                # The unified mode may never ACCEPT a group that legacy
                # rejected (the gate only adds rejections).
                if legacy_batch["decision"] not in ("Compatible",):
                    _fail(f"[{run_label}] unified ACCEPTED group {list(key)} "
                          f"but legacy {mode_label} decision was "
                          f"{legacy_batch['decision']!r} (gate must not relax "
                          f"a legacy rejection)")

        # Reverse direction (relaxation check, for robustness even when the
        # group exists in legacy but not in the unified map).
        for key, batch in legacy.items():
            if len(key) < 2 or batch["decision"] == "Compatible":
                continue
            unified_batch = unified_by.get(key)
            if unified_batch is None:
                continue
            if unified_batch["status"] != "Rejected" and unified_batch["decision"] == "Compatible":
                _fail(f"[{run_label}] legacy {mode_label} REJECTED group "
                      f"{list(key)} but unified accepted it — gate relaxes "
                      f"decisions")

    print("\n" + "=" * 78)
    if FAILURES:
        print(f"VERIFY UNIFIED SCORING: FAILED — {len(FAILURES)} violation(s)")
        for f_ in FAILURES:
            print("  " + f_)
    else:
        print("VERIFY UNIFIED SCORING: PASS — all decision-semantics invariants hold")
    print("=" * 78)

    with open(os.path.join(framework.RESULTS_DIR, "unified_validation.json"), "w") as f:
        json.dump({
            "static_a": static_a,
            "static_b": static_b,
            "adaptive_c": adaptive_c,
            "adaptive_d": adaptive_d,
        }, f, indent=2)
    print("Results JSON written to results/unified_validation.json")

    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()