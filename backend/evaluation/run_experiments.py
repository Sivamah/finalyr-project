"""
DMFE Phase 10 — Experiment Runner
=================================
Executes the full evaluation for workloads 50 / 100 / 250 / 500 requests
(40% ride, 40% food, 20% parcel) against the existing Phase 9 DMFE
pipeline, computes the baseline (individual-only, no DMFE) comparison,
and writes:

    results/experiments.json      — complete machine-readable results
    results/per_workload.csv      — compact per-workload metric table
    results/baseline_comparison.csv — DMFE vs baseline comparison table
"""

import csv
import json
import os
import sys

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, EVAL_DIR)
sys.path.insert(0, os.path.dirname(EVAL_DIR))  # backend root (for `app` package)

from framework import RESULTS_DIR, run_all_workloads  # noqa: E402


def write_csvs(results: dict) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)

    per_workload_rows = []
    baseline_rows = []
    for n, r in results.items():
        sp = r["single_pass"]
        t = sp["trips"]
        base = r["baseline"]
        per_workload_rows.append({
            "workload": n,
            "total_requests": sp["requests_processed"],
            "shared_trips": sp["shared_trips"],
            "individual_trips": sp["individual_trips"],
            "unassigned": sp["unassigned_count"],
            "avg_compatibility_score": sp["batches"]["avg_compatibility_score"],
            "avg_route_distance_km": t["avg_distance_km"],
            "avg_travel_time_min": t["avg_travel_time_min"],
            "avg_waiting_min": t["avg_waiting_min"],
            "vehicle_utilization_pct": t["avg_utilization_pct"],
            "driver_pool_utilization_pct": sp["drivers"]["driver_pool_utilization_pct"],
            "fuel_l": t["total_fuel_l"],
            "fuel_saved_l": t["fuel_saved_l"],
            "co2_kg": t["co2_emitted_kg"],
            "co2_saved_kg": t["co2_saved_kg"],
            "requests_completed": t["requests_completed"],
            "requests_failed": t["requests_failed"],
            "avg_processing_ms_per_request": r["timing"]["avg_processing_ms_per_request"],
            "route_optimization_total_s": r["timing"]["route_optimization_total_s"],
            "driver_selection_total_s": r["timing"]["driver_selection_total_s"],
            "batch_formation_total_s": r["timing"]["batch_formation_total_s"],
            "waves_completion_rate_pct": r["waves"]["completion_rate_pct"],
        })
        baseline_rows.append({
            "workload": n,
            "total_requests": base["requests_completed"],
            "shared_trips": 0,
            "individual_trips": base["individual_trips"],
            "avg_route_distance_km": round(
                base["total_distance_km"] / max(base["requests_completed"], 1), 2),
            "avg_travel_time_min": base["avg_travel_time_min"],
            "avg_waiting_min": 0,
            "vehicle_utilization_pct": base["avg_utilization_pct"],
            "driver_pool_utilization_pct": 100.0,
            "fuel_l": base["total_fuel_l"],
            "fuel_saved_l": 0,
            "co2_kg": base["total_co2_kg"],
            "co2_saved_kg": 0,
            "requests_completed": base["requests_completed"],
            "requests_failed": 0,
            "avg_processing_ms_per_request": base["avg_processing_ms"],
            "route_optimization_total_s": 0,
            "driver_selection_total_s": 0,
            "batch_formation_total_s": 0,
            "waves_completion_rate_pct": 100.0,
        })

    with open(os.path.join(RESULTS_DIR, "per_workload.csv"), "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(per_workload_rows[0].keys()))
        writer.writeheader()
        writer.writerows(per_workload_rows)

    with open(os.path.join(RESULTS_DIR, "baseline_comparison.csv"), "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(baseline_rows[0].keys()))
        writer.writeheader()
        writer.writerows(baseline_rows)

    print(f"wrote {os.path.join(RESULTS_DIR, 'per_workload.csv')}")
    print(f"wrote {os.path.join(RESULTS_DIR, 'baseline_comparison.csv')}")


if __name__ == "__main__":
    workloads = None
    if len(sys.argv) > 1:
        workloads = [int(a) for a in sys.argv[1:]]
    results = run_all_workloads(workloads)
    write_csvs(results)
    with open(os.path.join(RESULTS_DIR, "experiments.json")) as fh:
        final = json.load(fh)
    print("COMPLETE:", {k: v["single_pass"]["trips"]["requests_completed"]
                        for k, v in final.items()})
