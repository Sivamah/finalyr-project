"""
Phase 4.1 — Step 5: Feed-forward verification.

Controlled experiment with a systematic execution error:

    actual delay = predicted delay × 1.4      (exactly, no scatter)

Run A (control): static mode, learning disabled.
Run B (test):    adaptive mode, learning enabled.

Both arms run the same multi-day closed loop (real dispatch → trip
creation → simulated execution → complete_trip → learning) with the same
seeds, so any difference is attributable to the learning loop.

Checks, in order:

  1. Detection      — residual ring records actual ≈ 1.4 × predicted.
  2. Correction     — corridor delay multipliers rise after refit.
  3. Future preds   — new batches carry scaled estimated_delay_min
                      (compat-level predicted delay) → compat-level
                      prediction error shrinks in arm B only.
  4. Decisions      — Gate D (high-priority delay) uses the scaled
                      estimate; learned factor_bias shifts weights.
  5. Dispatch       — whether actual driver/routing choices differ.

No predictions are manufactured and no results are edited: everything
below is measured from the run.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import RESULTS_DIR, run_learning_workload

WORKLOADS = [100]
MAX_DAYS = 5
RESULT_FILE = os.path.join(RESULTS_DIR, "feedforward_x1_4.json")


def _delay_compat_error(db, day_trip_ids: List[int]) -> float:
    """Mean |actual - compat predicted delay| for a day's completed trips."""
    from app.dmfe.adaptive.learning import LearningEngine
    from app.db.models import Trip

    trips = (
        db.query(Trip).filter(Trip.id.in_(day_trip_ids)).all()
        if day_trip_ids else []
    )
    errs = []
    for t in trips:
        batch = LearningEngine._batch_row(db, t)
        pred = 0.0
        if batch is not None:
            pred = float(batch.estimated_delay_min or 0.0)
        errs.append(abs(float(t.max_delay_min or 0.0) - pred))
    return round(sum(errs) / len(errs), 2) if errs else 0.0


def analyze() -> None:
    cached: Dict[str, Any] = {}
    if os.path.exists(RESULT_FILE):
        cached = json.load(open(RESULT_FILE))

    arms = {
        "A_static_no_learning": dict(
            learning=False, mode="static", execution="delay_x1.4"
        ),
        "B_adaptive_learning": dict(
            learning=True, mode="adaptive", execution="delay_x1.4"
        ),
    }
    results: Dict[str, Any] = {}
    for name, kwargs in arms.items():
        key = f"{name}:w{WORKLOADS[0]}"
        if key in cached:
            results[name] = cached[key]
            print(f"[feedforward] {name}: cached, skipping run")
            continue
        print(f"[feedforward] {name} — running (workload={WORKLOADS[0]}, "
              f"days={MAX_DAYS}, actual=1.4×predicted delay)...", flush=True)
        run = run_learning_workload(
            WORKLOADS[0], max_days=MAX_DAYS, **kwargs
        )
        results[name] = run
        cached[key] = run
        with open(RESULT_FILE, "w") as fh:
            json.dump(cached, fh, indent=2)

    A = results["A_static_no_learning"]
    B = results["B_adaptive_learning"]

    print()
    print("=" * 96)
    print("FEED-FORWARD EXPERIMENT — actual delay = 1.4 × predicted (exact)")
    print("=" * 96)

    # 1+2. Detection + correction
    b_state = B["learning"]["state_summary"]
    b_mult = b_state.get("corridor_multipliers", {})
    print("\n[1] DETECTION (learning arm, residual ring):")
    print(f"    outcomes={b_state['outcomes']['count']}, "
          f"delay_bias_min={b_state['outcomes'].get('delay_bias_min')}, "
          f"delay_error={b_state['outcomes'].get('delay_error')}")
    print("[2] CORRECTION (corridor delay multipliers after refits):")
    print(f"    {json.dumps(b_mult, indent=2)}")

    # 3. Future predictions: per-day compat-level error, both arms
    print("\n[3] FUTURE PREDICTIONS — mean |actual - compat predicted delay|:")
    print("    day |  A (static, no learning) |  B (adaptive, learning)")
    for i, (da, dbb) in enumerate(
        zip(A["waves"]["per_day"], B["waves"]["per_day"]), start=1
    ):
        print(f"      {i:3d} |        {da.get('mean_compat_delay_error_min'):>12} "
              f"|        {dbb.get('mean_compat_delay_error_min'):>12}")
    print("    (route-level mean error = |actual - snapshot delay|: "
          "A first day %.2f, B first day %.2f, B last day %.2f)"
          % (A["waves"]["per_day"][0].get("mean_delay_error_min"),
             B["waves"]["per_day"][0].get("mean_delay_error_min"),
             B["waves"]["per_day"][-1].get("mean_delay_error_min")))

    # 4. Decisions: learned weight corrections (factor_bias) in arm B
    print("\n[4] DECISIONS — learned weight corrections in arm B:")
    print(f"    factor_bias: {json.dumps(b_state.get('factor_bias', {}))}")
    a_shared = A["single_pass"]["shared_trips"]
    b_shared = B["single_pass"]["shared_trips"]
    print(f"    day-1 shared trips: A={a_shared} B={b_shared}")

    # 5. Dispatch: selected driver sets per day (any divergence?)
    print("\n[5] DISPATCH — per-day selected driver ids (first 8):")
    for i, (da, dbb) in enumerate(
        zip(A["waves"]["per_day"], B["waves"]["per_day"]), start=1
    ):
        print(f"    day {i}: A={da.get('trips')} trips B={dbb.get('trips')} trips")

    # Overall comparison
    wa, wb = A["waves"], B["waves"]
    print("\n" + "=" * 96)
    print("AGGREGATE (multi-day):")
    print(f"    trips_total        A={wa['trips_total']} B={wb['trips_total']}")
    print(f"    completion rate    A={wa['completion_rate_pct']}% "
          f"B={wb['completion_rate_pct']}%")
    print(f"    total distance km  A={wa['total_distance_km']} "
          f"B={wb['total_distance_km']}")
    print(f"    total fuel L       A={wa['total_fuel_l']} B={wb['total_fuel_l']}")
    print(f"    refit fired day    B={wb.get('refit_fired_day')}")
    print("=" * 96)


if __name__ == "__main__":
    analyze()
