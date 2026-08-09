"""
A-DMFE Experiment Runner
========================
Runs the same workloads through the DMFE pipeline in BOTH operating modes:

    static   — Phase 9 behaviour exactly (baseline DMFE)
    adaptive — A-DMFE (context weights, matrix, BQS gate, learning)

Writes per-mode results to:

    results/admfe_static_experiments.json
    results/admfe_adaptive_experiments.json
    results/admfe_comparison.json          — static vs adaptive, delta %,
                                             improvement/regression/neutral
    results/research_summary.md            — one-row-per-(workload, mode) table

Repeatability (Step 5): pass `--reps N` to run every workload N times with
different deterministic seeds and aggregate mean / min / max / std per key
metric into `results/admfe_repetitions.json`.  A single run is fully
deterministic (fixed seed, fixed fleet, deterministic execution model), so
identical-seed repeats produce identical results; *different* seeds sample
the request/fleet/execution distribution.

Usage:
    python evaluation/run_admfe_experiments.py [50 100 250] [--reps 5] [--force]
"""

import json
import os
import statistics
import sys
from typing import Any, Dict, List, Optional, Tuple

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, EVAL_DIR)
sys.path.insert(0, os.path.dirname(EVAL_DIR))  # backend root (for `app` package)

from framework import RESULTS_DIR, run_workload  # noqa: E402

WORKLOADS = [50, 100, 250, 500]

# ── comparison metric specification ────────────────────────────────────────
# (dot-path, label, lower_is_better | None)
# None = informational, never classified as improvement/regression.
METRICS: List[Tuple[str, str, Optional[bool]]] = [
    ("single_pass.requests_processed", "requests processed", False),
    ("single_pass.shared_trips", "shared trips", False),
    ("single_pass.individual_trips", "individual trips", None),
    ("single_pass.unassigned_count", "unassigned", True),
    ("single_pass.trips.batching_rate_pct", "batching rate %", False),
    ("single_pass.trips.avg_utilization_pct", "avg vehicle util %", False),
    ("single_pass.trips.total_fuel_l", "total fuel L", True),
    ("single_pass.trips.fuel_saved_l", "fuel saved L", False),
    ("single_pass.trips.co2_emitted_kg", "CO2 emitted kg", True),
    ("single_pass.trips.co2_saved_kg", "CO2 saved kg", False),
    ("single_pass.trips.co2_reduction_vs_internal_baseline_pct",
     "CO2 reduction %", False),
    ("single_pass.trips.total_distance_km", "total distance km", True),
    ("single_pass.trips.avg_travel_time_min", "avg travel min", True),
    ("single_pass.trips.avg_waiting_min", "avg waiting min", True),
    ("single_pass.trips.avg_delay_min", "avg delay min", True),
    ("single_pass.trips.requests_completed", "requests completed", False),
    ("single_pass.trips.requests_failed", "requests failed", True),
    ("single_pass.drivers.driver_pool_utilization_pct",
     "driver pool util %", False),
    ("single_pass.batches.avg_requests_per_batch", "avg req/batch", False),
    ("single_pass.batches.max_requests_per_batch", "max req/batch", False),
    ("waves.completion_rate_pct", "waves completion %", False),
    ("waves.total_distance_km", "waves distance km", True),
    ("waves.total_fuel_l", "waves fuel L", True),
    ("timing.avg_processing_ms_per_request", "avg proc ms/req", True),
    ("timing.batch_formation_total_s", "batch formation s", True),
    ("timing.route_optimization_total_s", "route optimisation s", True),
    ("timing.driver_selection_total_s", "driver selection s", True),
    ("timing.pipeline_total_s", "pipeline total s", True),
    ("timing.sql_queries", "SQL queries", True),
    ("timing.learning_total_s", "learning total s", True),
]

# metrics that have a fallback path when the canonical key is absent in
# legacy (pre-Phase-7) result files
FALLBACKS: Dict[str, str] = {
    "single_pass.trips.batching_rate_pct": "computed",
    "single_pass.trips.avg_delay_min": "single_pass.trips.avg_waiting_min",
}


def _dig(obj: Dict, path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        cur = cur[part]
    return cur


def _metric_value(payload: Dict, path: str) -> Any:
    try:
        return _dig(payload, path)
    except (KeyError, TypeError):
        pass
    fb = FALLBACKS.get(path)
    if fb == "computed":
        try:
            shared = _dig(payload, "single_pass.trips.shared_trips")
            total = _dig(payload, "single_pass.trips.trips")
            if total:
                return round(shared / total * 100.0, 1)
        except (KeyError, TypeError):
            pass
    elif fb:
        try:
            return _dig(payload, fb)
        except (KeyError, TypeError):
            pass
    return None


def _delta_pct(static: Any, adaptive: Any) -> Optional[float]:
    if static is None or adaptive is None:
        return None
    try:
        s, a = float(static), float(adaptive)
    except (TypeError, ValueError):
        return None
    if s == 0.0:
        return 0.0 if a == 0.0 else None
    return round((a - s) / abs(s) * 100.0, 2)


def _verdict(delta: Optional[float], lower_better: Optional[bool]) -> str:
    if delta is None or lower_better is None:
        return "n/a"
    eps = 0.5  # |delta| below this is considered neutral
    if abs(delta) <= eps:
        return "neutral"
    improved = (delta < 0) if lower_better else (delta > 0)
    return "improvement" if improved else "regression"


# ── repeatability aggregation (Step 5) ────────────────────────────────────

REPEAT_METRICS: List[str] = [
    "single_pass.trips.batching_rate_pct",
    "single_pass.trips.avg_utilization_pct",
    "single_pass.trips.avg_delay_min",
    "single_pass.trips.total_fuel_l",
    "single_pass.trips.fuel_saved_l",
    "single_pass.trips.co2_saved_kg",
    "single_pass.trips.co2_emitted_kg",
    "single_pass.trips.total_distance_km",
    "single_pass.trips.avg_travel_time_min",
    "single_pass.trips.requests_completed",
    "single_pass.trips.requests_failed",
    "single_pass.drivers.driver_pool_utilization_pct",
    "waves.completion_rate_pct",
    "timing.avg_processing_ms_per_request",
    "timing.pipeline_total_s",
    "timing.sql_queries",
]


def _aggregate(values: List[float]) -> Dict[str, float]:
    return {
        "mean": round(statistics.mean(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "std": round(statistics.stdev(values), 3) if len(values) > 1 else 0.0,
    }


def run_repetitions(
    workload: int, mode: str, reps: int, force: bool = False
) -> Dict[str, Any]:
    """
    Run one workload N times with distinct seeds, cache per-seed payloads
    and return the aggregates + per-seed runs.
    """
    path = os.path.join(RESULTS_DIR, "admfe_repetitions.json")
    cached: Dict[str, Any] = {}
    if os.path.exists(path):
        try:
            cached = json.load(open(path))
        except Exception:
            cached = {}

    key = f"{workload}:{mode}:r{reps}"
    if not force and key in cached and len(cached[key].get("runs", [])) == reps:
        print(f"[reps] {key} cached — skipping", flush=True)
        return cached[key]

    print(f"[reps] workload={workload} mode={mode} reps={reps} ...", flush=True)
    runs: List[Dict[str, Any]] = []
    for i in range(reps):
        seed = 1000 + workload + i * 97
        print(f"[reps]   seed={seed} ...", flush=True)
        runs.append(run_workload(workload, mode=mode, seed=seed))
        print(f"[reps]   seed={seed} done", flush=True)

    aggregates: Dict[str, Dict[str, float]] = {}
    for path_ in REPEAT_METRICS:
        vals = [_metric_value(r, path_) for r in runs]
        vals = [v for v in vals if isinstance(v, (int, float))]
        if vals:
            aggregates[path_] = _aggregate(vals)

    out = {
        "workload": workload,
        "mode": mode,
        "reps": reps,
        "seeds": [1000 + workload + i * 97 for i in range(reps)],
        "aggregates": aggregates,
        "runs": runs,
    }
    cached[key] = out
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(cached, fh, indent=2)
    print(f"[reps] workload={workload} mode={mode} reps={reps} done", flush=True)
    return out


# ── load / run / cache helpers ────────────────────────────────────────────

def load_or_run(workload: int, mode: str, results: dict,
                force: bool = False) -> dict:
    """Run a workload in the given mode (cached in the per-mode file)."""
    path = os.path.join(RESULTS_DIR, f"admfe_{mode}_experiments.json")
    if not force and workload in results:
        print(f"[{mode}] workload={workload} cached — skipping", flush=True)
        return results
    print(f"[{mode}] workload={workload} ...", flush=True)
    results[workload] = run_workload(workload, mode=mode)
    with open(path, "w") as fh:
        json.dump({str(k): v for k, v in results.items()}, fh, indent=2)
    print(f"[{mode}] workload={workload} done", flush=True)
    return results


# ── comparison output ─────────────────────────────────────────────────────

def load_repetition_means() -> Dict[str, Dict[str, float]]:
    """Read admfe_repetitions.json and return {(workload, mode): {metric: mean}}."""
    path = os.path.join(RESULTS_DIR, "admfe_repetitions.json")
    out: Dict[str, Dict[str, float]] = {}
    if not os.path.exists(path):
        return out
    try:
        cached = json.load(open(path))
    except Exception:
        return out
    for key, entry in cached.items():
        if ":" not in key:
            continue
        w, mode, _r = key.split(":")
        try:
            int(w)
        except ValueError:
            continue
        out[(int(w), mode)] = {
            mpath: agg.get("mean") for mpath, agg
            in (entry.get("aggregates") or {}).items()
        }
    return out


def build_comparison(static: dict, adaptive: dict) -> Dict:
    repeat_means = load_repetition_means()
    comparison: Dict[str, Any] = {}
    for n in WORKLOADS:
        if n not in static or n not in adaptive:
            continue
        rows: Dict[str, Any] = {}
        for path, label, lower_better in METRICS:
            sv = _metric_value(static[n], path)
            av = _metric_value(adaptive[n], path)
            rmean_s = repeat_means.get((n, "static"), {}).get(path)
            rmean_a = repeat_means.get((n, "adaptive"), {}).get(path)
            if rmean_s is not None and rmean_a is not None:
                sv, av = rmean_s, rmean_a
            delta = _delta_pct(sv, av)
            rows[label] = {
                "path": path,
                "static": sv,
                "adaptive": av,
                "delta_pct": delta,
                "lower_is_better": lower_better,
                "verdict": _verdict(delta, lower_better),
            }
        comparison[str(n)] = rows
    return comparison


def write_research_summary(static: dict, adaptive: dict) -> None:
    """Step 13 — concise research summary table (workload × mode)."""
    cols = [
        ("single_pass.trips.batching_rate_pct", "Batching %"),
        ("single_pass.trips.avg_utilization_pct", "Util %"),
        ("single_pass.trips.avg_delay_min", "Delay min"),
        ("single_pass.trips.total_fuel_l", "Fuel L"),
        ("single_pass.trips.co2_saved_kg", "CO2 saved kg"),
        ("single_pass.trips.total_distance_km", "Dist km"),
        ("waves.completion_rate_pct", "Completion %"),
        ("timing.avg_processing_ms_per_request", "Proc ms/req"),
    ]
    lines = ["# A-DMFE Research Summary", ""]
    lines.append("| Workload | Mode | " + " | ".join(c[1] for c in cols) + " |")
    lines.append("|---|--" + "|--" * len(cols) + "|")
    for n in WORKLOADS:
        for mode, data in (("Static", static), ("Adaptive", adaptive)):
            if n not in data:
                continue
            cells = [str(n), mode]
            for path, _label in cols:
                v = _metric_value(data[n], path)
                cells.append(fmt(v))
            lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("_Values from a single deterministic run per mode (seed = "
                 "1000+workload). See admfe_repetitions.json for repeated-"
                 "seed aggregates._")
    path = os.path.join(RESULTS_DIR, "research_summary.md")
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {path}")


def fmt(x, digits=1):
    try:
        return f"{x:,.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def print_comparison(comparison: Dict[str, Any]) -> None:
    print()
    print("=" * 110)
    print("A-DMFE vs static DMFE — side-by-side (verdict: improvement/regression/neutral)")
    print("=" * 110)
    header = (f"{'metric':<34}{'wload':>6}{'static':>14}"
              f"{'adaptive':>14}{'delta':>10}  verdict")
    print(header)
    print("-" * 110)
    for n in WORKLOADS:
        rows = comparison.get(str(n))
        if not rows:
            continue
        for label, row in rows.items():
            delta = (f"{row['delta_pct']:+.1f}%" if row["delta_pct"] is not None
                     else "-")
            print(f"{label:<34}{n:>6}{fmt(row['static']):>14}"
                  f"{fmt(row['adaptive']):>14}{delta:>10}  {row['verdict']}")


def run_learning_ab(workloads: List[int], force: bool = False) -> None:
    """
    Learning A/B (Step 11): the same adaptive workload with the closed
    loop (trips completed through complete_trip) and learning ON vs OFF.

    Cached in results/admfe_learning_ab.json per workload.
    """
    from framework import run_learning_workload

    path = os.path.join(RESULTS_DIR, "admfe_learning_ab.json")
    cached: dict = {}
    if os.path.exists(path):
        try:
            cached = json.load(open(path))
        except Exception:
            cached = {}

    off: dict = {}
    on: dict = {}
    for n in workloads:
        for flag, key, label in (
            (False, f"{n}:off", "OFF"), (True, f"{n}:on", "ON")
        ):
            if not force and key in cached:
                continue
            print(f"[learning] workload={n} learning={label} ...", flush=True)
            cached[key] = run_learning_workload(n, learning=flag)
            with open(path, "w") as fh:
                json.dump(cached, fh, indent=2)
            print(f"[learning] workload={n} learning={label} done", flush=True)
        off[n] = cached.get(f"{n}:off")
        on[n] = cached.get(f"{n}:on")

    print()
    print("=" * 110)
    print("Learning A/B (adaptive, closed loop): learning ON vs OFF")
    print("=" * 110)
    for n in workloads:
        lrn = (on.get(n) or {}).get("learning") or {}
        wv = (on.get(n) or {}).get("waves") or {}
        off_wv = (off.get(n) or {}).get("waves") or {}
        if not on.get(n):
            continue
        print(f"\n[learning] workload={n} (ON arm) learned state:")
        print(f"  outcomes     : {json.dumps(lrn.get('state_summary', {}).get('outcomes', {}))}")
        print(f"  factor_bias  : {json.dumps(lrn.get('state_summary', {}).get('factor_bias', {}))}")
        print(f"  corridors    : {json.dumps(lrn.get('state_summary', {}).get('corridor_multipliers', {}))}")
        print(f"  util bias    : {json.dumps(lrn.get('state_summary', {}).get('corridor_utilization_bias', {}))}")
        print(f"  drivers track: {lrn.get('drivers_tracked')}")
        print(f"  refit fired day: {wv.get('refit_fired_day')}")
        print(f"  completion (off/on): {off_wv.get('completion_rate_pct')}% / "
              f"{wv.get('completion_rate_pct')}%")
        print(f"  fuel L (off/on): {off_wv.get('total_fuel_l')} / {wv.get('total_fuel_l')}")
        print(f"  learning time (s): {wv.get('learning_total_s')} "
              f"({wv.get('learning_calls')} calls)")
        for d in wv.get("per_day", []):
            print(
                f"    day {d['day']}: trips={d['trips']} waves={d['waves']} "
                f"outcomes={d.get('outcomes')} refit={d.get('refit_count')} "
                f"delay_mults={json.dumps(d.get('corridor_delay_multipliers'))}"
            )


def main() -> None:
    global WORKLOADS
    reps = 1
    force = False
    args = [a for a in sys.argv[1:]]
    if "--force" in args:
        force = True
        args.remove("--force")
    if "--reps" in args:
        idx = args.index("--reps")
        try:
            reps = int(args[idx + 1])
            del args[idx:idx + 2]
        except (ValueError, IndexError):
            sys.exit("usage: --reps N (integer)")
    if args:
        WORKLOADS = [int(a) for a in args]

    static_path = os.path.join(RESULTS_DIR, "admfe_static_experiments.json")
    adaptive_path = os.path.join(RESULTS_DIR, "admfe_adaptive_experiments.json")
    static: dict = {}
    adaptive: dict = {}
    if os.path.exists(static_path):
        static = {int(k): v for k, v in json.load(open(static_path)).items()}
    if os.path.exists(adaptive_path):
        adaptive = {int(k): v for k, v in json.load(open(adaptive_path)).items()}

    for n in WORKLOADS:
        static = load_or_run(n, "static", static, force)
    for n in WORKLOADS:
        adaptive = load_or_run(n, "adaptive", adaptive, force)

    # Step 5 — repeated-seed runs (aggregates written separately)
    if reps > 1:
        for n in WORKLOADS:
            run_repetitions(n, "static", reps, force)
            run_repetitions(n, "adaptive", reps, force)

    comparison = build_comparison(static, adaptive)
    print_comparison(comparison)
    with open(os.path.join(RESULTS_DIR, "admfe_comparison.json"), "w") as fh:
        json.dump({
            "meta": {
                "workloads": WORKLOADS,
                "reps": reps,
                "metrics_defined_in": "run_admfe_experiments.py (METRICS)",
            },
            "comparison": comparison,
        }, fh, indent=2)
    print(f"wrote {os.path.join(RESULTS_DIR, 'admfe_comparison.json')}")

    write_research_summary(static, adaptive)
    run_learning_ab(WORKLOADS, force)


if __name__ == "__main__":
    main()
