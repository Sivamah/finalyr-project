"""
PHASE 8 — FINAL VALIDATION
==========================

Consumes the cached, deterministic experiment results
(results/admfe_*_experiments.json + admfe_repetitions.json) and emits:

  1. results/final_metrics_table.md        - Static vs Adaptive per workload
  2. results/final_statistical_summary.csv - mean / std / min / max per metric
                                             (repeated seeds)
  3. results/final_improvement_summary.md  - verifies each metric with
                                             direction-aware classification
                                             (IMPROVEMENT / REGRESSION / NEUTRAL)

No statistical significance is claimed: the simulation is deterministic
given its seed; repeated runs differ only in the RNG seed, so
mean/std/min/max are descriptive summaries over seeds.
"""
import csv
import json
import os

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
WORKLOADS = [50, 100, 250, 500]
EPS = 5.0  # neutral band on relative % change


def pick(path: str, run: dict):
    node = run or {}
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


# (category, key, label, json path, higher_is_better)
METRICS = [
    # REQUESTS
    ("REQUESTS", "total", "Total requests", "single_pass.requests_processed", False),
    ("REQUESTS", "completed", "Requests completed", "single_pass.trips.requests_completed", True),
    ("REQUESTS", "failed", "Requests failed", "single_pass.trips.requests_failed", False),
    ("REQUESTS", "unassigned", "Unassigned (single pass)", "single_pass.unassigned_count", False),
    ("REQUESTS", "completion", "Completion rate (%)", "waves.completion_rate_pct", True),
    # BATCHING
    ("BATCHING", "shared", "Shared trips", "single_pass.trips.shared_trips", True),
    ("BATCHING", "individual", "Individual trips", "single_pass.trips.individual_trips", False),
    ("BATCHING", "batching_rate", "Batching rate %", "single_pass.trips.batching_rate_pct", True),
    ("BATCHING", "batch_size", "Avg batch size", "single_pass.batches.avg_requests_per_batch", True),
    # MOBILITY
    ("MOBILITY", "avg_distance", "Avg trip distance (km)", "single_pass.trips.avg_distance_km", False),
    ("MOBILITY", "total_distance", "Total distance (km)", "single_pass.trips.total_distance_km", False),
    ("MOBILITY", "travel_time", "Avg travel time (min)", "single_pass.trips.avg_travel_time_min", False),
    # R3: the "waiting" row was dropped — framework.collect_metrics emits
    # avg_waiting_min as an alias of avg_delay_min, so the two rows carried
    # identical values and presented one measurement as two findings.
    ("MOBILITY", "delay", "Avg delay (min)", "single_pass.trips.avg_delay_min", False),
    # UTILIZATION
    ("UTILIZATION", "vehicle_util", "Avg vehicle utilisation %", "single_pass.trips.avg_utilization_pct", True),
    ("UTILIZATION", "driver_util", "Driver pool utilisation %", "single_pass.drivers.driver_pool_utilization_pct", True),
    # ENVIRONMENT
    ("ENVIRONMENT", "fuel", "Fuel consumed (L)", "single_pass.trips.total_fuel_l", False),
    ("ENVIRONMENT", "fuel_saved", "Fuel saved (L)", "single_pass.trips.fuel_saved_l", True),
    ("ENVIRONMENT", "co2", "CO2 emitted (kg)", "single_pass.trips.co2_emitted_kg", False),
    ("ENVIRONMENT", "co2_saved", "CO2 saved (kg)", "single_pass.trips.co2_saved_kg", True),
    # PERFORMANCE
    ("PERFORMANCE", "runtime", "Pipeline runtime (s)", "timing.pipeline_total_s", False),
    ("PERFORMANCE", "processing", "Processing / request (ms)", "timing.avg_processing_ms_per_request", False),
    ("PERFORMANCE", "batch_fmt", "Batch formation (s)", "timing.batch_formation_total_s", False),
    ("PERFORMANCE", "routing", "Routing (s)", "timing.route_optimization_total_s", False),
    ("PERFORMANCE", "driver_sel", "Driver selection (s)", "timing.driver_selection_total_s", False),
    ("PERFORMANCE", "decision", "Decision gate (s)", "timing.decision_total_s", False),
    ("PERFORMANCE", "persistence", "Persistence (s)", "timing.persistence_total_s", False),
    ("PERFORMANCE", "learning_t", "Learning (s)", "timing.learning_total_s", False),
]

FIELDS = ["category", "metric", "workload",
          "static_mean", "static_std", "static_min", "static_max", "static_n",
          "adaptive_mean", "adaptive_std", "adaptive_min", "adaptive_max", "adaptive_n"]


def fmt(v, nd=2):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    return f"{v:.{nd}f}"


def delta_pct(a, b):
    if a is None or b is None or not isinstance(a, (int, float)) or a == 0:
        return "-"
    return f"{(b / a - 1.0) * 100.0:+.1f}%"


def main():
    single = {}
    for mode in ("static", "adaptive"):
        single[mode] = {}
        p = os.path.join(RESULTS_DIR, f"admfe_{mode}_experiments.json")
        if os.path.exists(p):
            data = json.load(open(p))
            for k, v in data.items():
                try:
                    single[mode][int(k)] = v
                except ValueError:
                    continue

    repeats = {}
    p = os.path.join(RESULTS_DIR, "admfe_repetitions.json")
    if os.path.exists(p):
        for key, entry in json.load(open(p)).items():
            parts = key.split(":")
            if len(parts) != 3:
                continue
            try:
                w = int(parts[0])
            except ValueError:
                continue
            runs = entry.get("runs", []) or []
            if runs:
                repeats[(w, parts[1])] = runs

    # ── 1. final metrics table ─────────────────────────────────────────────
    lines = ["# FINAL METRICS — STATIC vs ADAPTIVE", ""]
    lines.append("Canonical single-run comparison (seed = 1000 + workload). "
                 "Δ % is the relative change of adaptive over static.")
    lines.append("")
    for cat_i, cat in enumerate([m[0] for m in METRICS if
                                 m[0] not in [x[0] for x in METRICS[:0]]]):
        pass
    cat_order = []
    for cat, _, _, _, _ in METRICS:
        if cat not in cat_order:
            cat_order.append(cat)
    for cat in cat_order:
        lines.append(f"## {cat}")
        lines.append("")
        lines.append("| Metric | W | Static | Adaptive | Δ % |")
        lines.append("|---|---|---|---|---|")
        for _, _, label, path_, hi in [m for m in METRICS if m[0] == cat]:
            for w in WORKLOADS:
                s = pick(path_, single.get("static", {}).get(w, {}))
                a = pick(path_, single.get("adaptive", {}).get(w, {}))
                lines.append(f"| {label} | {w} | {fmt(s)} | {fmt(a)} | {delta_pct(s, a)} |")
        lines.append("")

    with open(os.path.join(RESULTS_DIR, "final_metrics_table.md"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    # ── 2. statistical summary (repeated seeds) ────────────────────────────
    rows = []
    for cat, _k, label, path_, _hi in METRICS:
        for w in WORKLOADS:
            row = {"category": cat, "metric": label, "workload": w}
            for mode in ("static", "adaptive"):
                vals = [pick(path_, r) for r in repeats.get((w, mode), [])]
                vals = [v for v in vals
                        if isinstance(v, (int, float)) and not isinstance(v, bool)]
                if vals:
                    n = len(vals)
                    mean = sum(vals) / n
                    var = sum((v - mean) ** 2 for v in vals) / n
                    row[mode + "_mean"] = round(mean, 3)
                    row[mode + "_std"] = round(var ** 0.5, 3)
                    row[mode + "_min"] = round(min(vals), 3)
                    row[mode + "_max"] = round(max(vals), 3)
                    row[mode + "_n"] = n
                else:
                    for k in ("mean", "std", "min", "max", "n"):
                        row[mode + "_" + k] = ""
            rows.append(row)

    with open(os.path.join(RESULTS_DIR, "final_statistical_summary.csv"),
              "w", newline="", encoding="utf-8") as fh:
        wcsv = csv.DictWriter(fh, fieldnames=FIELDS)
        wcsv.writeheader()
        wcsv.writerows(rows)

    # ── 3. improvement classification ──────────────────────────────────────
    out = ["# IMPROVEMENT CLASSIFICATION (Static vs Adaptive)", ""]
    out.append("Δ % = (adaptive_mean / static_mean − 1) × 100 over repeated seeds. "
               "Verdict uses direction-aware rules: for metrics where higher is "
               "better (completion, batching rate, utilisation, fuel/CO2 saved) a "
               "positive Δ is IMPROVEMENT; where lower is better (distance, delay, "
               "waiting, fuel/CO2 emitted, processing time) a negative Δ is "
               "IMPROVEMENT. |Δ| ≤ " + fmt(EPS) + "% is NEUTRAL.")
    out.append("")
    out.append("| Category | Metric | W | Δ % (means) | Verdict |")
    out.append("|---|---|---|---|---|")

    class_votes = {}
    for w in WORKLOADS:
        for cat, k, label, path_, hi in METRICS:
            s_vals = [v for v in [pick(path_, r) for r in repeats.get((w, "static"), [])]
                      if isinstance(v, (int, float)) and not isinstance(v, bool)]
            a_vals = [v for v in [pick(path_, r) for r in repeats.get((w, "adaptive"), [])]
                      if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if not s_vals or not a_vals:
                continue
            d = None
            s_mean = sum(s_vals) / len(s_vals)
            a_mean = sum(a_vals) / len(a_vals)
            if s_mean == 0 or a_mean == 0:
                verdict = "-"
            elif abs(a_mean) < 0.005 and abs(s_mean) < 0.005:
                d = None                      # sub-5 ms → relative % meaningless
                verdict = "NEUTRAL"
            else:
                d = (a_mean / s_mean - 1.0) * 100.0
                if abs(d) <= EPS:
                    verdict = "NEUTRAL"
                elif hi:
                    verdict = "IMPROVEMENT" if d > 0 else "REGRESSION"
                else:
                    verdict = "IMPROVEMENT" if d < 0 else "REGRESSION"
            key = (cat, label, hi)
            summary = class_votes.setdefault(key, {"cat": cat, "label": label,
                                                   "hi": hi, "deltas": []})
            if d is not None:
                summary["deltas"].append(d)
            out.append(
                f"| {cat} | {label} | {w} | "
                f"{f'{d:+.1f}%' if d is not None else '-'} | {verdict} |"
            )

    # Workload-aggregated verdict on top of per-workload votes
    summary_rows = []
    for (cat, label, hi), info in class_votes.items():
        ds = info["deltas"]
        if not ds:
            continue
        mean_d = sum(ds) / len(ds)
        if abs(mean_d) <= EPS:
            verdict = "NEUTRAL"
        elif hi:
            verdict = "IMPROVEMENT" if mean_d > 0 else "REGRESSION"
        else:
            verdict = "IMPROVEMENT" if mean_d < 0 else "REGRESSION"
        summary_rows.append((cat, label, mean_d, verdict))

    out.append("")
    out.append("## Aggregate verdict (mean Δ over workloads)")
    out.append("")
    out.append("| Category | Metric | Mean Δ % | Verdict |")
    out.append("|---|---|---|---|")
    for cat, label, mean_d, verdict in summary_rows:
        out.append(f"| {cat} | {label} | {mean_d:+.1f}% | {verdict} |")

    with open(os.path.join(RESULTS_DIR, "final_improvement_summary.md"),
              "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))

    print("generated:")
    for f in ("final_metrics_table.md", "final_statistical_summary.csv",
              "final_improvement_summary.md"):
        print("  " + os.path.join(RESULTS_DIR, f))


if __name__ == "__main__":
    main()