# A-DMFE — Metric Definitions Reference

Single source of truth for what every displayed number means. Written after the
R3/R4 evaluation corrections so the **live dashboard**, the **evaluation
tables** and the **IEEE paper** cannot drift apart again.

Rule used throughout: *if the backend cannot supply a quantity honestly, the UI
omits it rather than approximating it.*

---

## 1. Live dashboard metrics (`GET /api/dashboard/stats`)

| Displayed label | Backend field | Exact definition | Notes |
|---|---|---|---|
| Total Requests | `total_requests` | Count of all `Request` rows | — |
| Shared Trips | `shared_trips` | `COUNT(Trip WHERE is_shared = true)` | **New field.** Previously this card read `total_optimizations`. |
| Batching Rate | `batch_rate` | `shared_trips / COUNT(Trip) x 100` | Previously mislabelled "Vehicle Util." — no fleet-utilisation aggregate exists. |
| Fuel Saved | `fuel_saved` | `SUM(Trip.fuel_saved_l)` | — |
| CO2 Reduction | `co2_reduction` | `SUM(Trip.co2_saved_kg)` | — |
| Avg Route Savings | `avg_route_savings` | `AVG(Trip.distance_saved_km)` | — |
| *(not displayed)* | `total_optimizations` | `COUNT(Trip)` — **all** trips, shared and individual | Name is historical; it is a trip count, not an optimisation count. |

## 2. Time metrics (`GET /api/simulation/advanced-analytics`)

Three distinct quantities that must never share the word "waiting":

| Displayed label | Backend field | Exact definition |
|---|---|---|
| Avg Queue Age (pending) | `avg_queue_waiting_time_sec` | `mean(now - created_at)` over requests **still Pending**. A live gauge that grows while the simulation idles. |
| Avg Completion Time | `avg_completion_time_sec` | `mean(Trip.completed_at - Trip.created_at)` over **completed** trips. |
| Avg Fulfilment Time *(playback)* | `SavedSimulation.avg_waiting_time_sec` | `mean(completed_at - created_at)` over **completed requests**. End-to-end turnaround. |

None of these is the research **delay** metric. The research delay is a
model-estimated detour penalty produced by the DMFE optimizer, not a wall-clock
measurement, and it is reported only in the evaluation tables.

## 3. Completion vs dispatch

| Context | Meaning |
|---|---|
| `completion_rate_pct` (live analytics) | `COUNT(status = 'Completed') / total x 100`. Genuine completion. |
| `SavedSimulation.completion_rate` (playback) | Same definition. Genuine completion. |
| **Evaluation tables / paper** | Report **dispatch rate**, not completion. A request counted there was *assigned to a trip*, not observed through to delivery. |

The live analytics pages and the evaluation tables therefore measure different
things under superficially similar names. When presenting, say "dispatch rate"
for anything sourced from `evaluation/`.

## 4. Feasibility Engine (`GET /api/dmfe/*`)

| Displayed | Definition |
|---|---|
| Avg Compatibility | Mean compatibility score across recorded analysis runs |
| Effective Threshold | `theta_eff` actually applied by the most recent run |
| Rejected Pairs | Candidate pairings scoring below `theta_eff` |
| Batches Created | `DMFEBatch` rows with `decision = 'Compatible'` |
| Solo trip / `N/A` | An `Individual` batch. `compatibility_score = 0.0` on these rows is a **not-applicable sentinel**, not a measured zero — a single request has no pairwise score. |

## 5. Deliberately omitted (no honest backend source)

| Was shown as | Why removed |
|---|---|
| Six `+12.5% vs yesterday`-style KPI trends | No period-comparison endpoint exists |
| `92.4%` "Optimization" ring | Hardcoded literal; now the real batching rate |
| `98.4%` "Adaptive engine" health bar | Hardcoded literal; no engine-health percentage is computed |
| Bar fills of `75` / `60` / `45` on the summary strip | Encoded nothing; bars now render only for true 0-100 proportions |
| "Prediction Accuracy", "Decision Confidence" | No aggregate exists. Confidence is per-batch; the learning engine tracks a delay *residual* (an error), not an accuracy |

---

## Open item — evaluation results are stale

Every file under `backend/evaluation/results/` still carries its original
timestamp, while `framework.py`, `make_admfe_report.py`, `final_validation.py`
and `analyze_unified.py` were all modified by the R3/R4 correction, and
`dmfe/optimizer.py` was modified by the P0-3 fix.

**The published tables therefore predate both corrections and must be
regenerated before the numbers are quoted anywhere.**

```
cd backend
python evaluation/run_admfe_experiments.py
python evaluation/make_admfe_report.py
python evaluation/final_validation.py
python scripts/check_results_consistency.py     # must exit 0
```

`check_results_consistency.py` enforces four invariants: no two published
metrics may carry an identical value series (C1), no withdrawn label may
reappear (C2), every paper figure must trace to a generated table (C3), and no
result file may be older than the engine source that produced it (C4). C4 is
the one currently failing.

One known issue to re-check after regeneration: `decision_total_s` and
`learning_total_s` both report `0.00` for every workload, which points at timer
instrumentation rather than at labelling. It was flagged, not fixed.
