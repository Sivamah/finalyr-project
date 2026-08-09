# 11 — A-DMFE Experimental Evaluation

**Series note:** This document summarises the A-DMFE (adaptive) vs DMFE (static) experimental
evaluation. The full report, result files, CSVs, IEEE tables and graph datasets live under
`backend/evaluation/` (see Artifacts Index below).

## What was evaluated

| Workload | Static (Phase 9) | Adaptive (A-DMFE) |
|---|---|---|
| 50 requests | done | done |
| 100 requests | done | done |
| 250 requests | done | done |
| 500 requests | done | done |

Fleet: 60 vehicles/drivers · Mix: 40 % ride / 40 % food / 20 % parcel · Deterministic seeds ·
Haversine distance matrix (Google Maps disabled) · Fresh schema per run · Single pass + simulated
multi-wave full-day operation.

## Headline results

- **Vehicle utilisation:** adaptive 75.4–79.7 % vs static 74.3–76.1 % (+2.7 % mean, p = 0.001).
- **Customer waiting:** adaptive 2.76–4.24 min vs static 2.25–4.44 min (−16.5 % mean; −37.8 % at 100).
- **Full-day fuel:** −2.0 % (250) and −8.0 % (500) under adaptive.
- **CO2 vs no-DMFE baseline:** up to 44.8 % reduction (250) with adaptive.
- **Batch formation at 500 requests:** −67 % (matrix reuse vs greedy re-scoring).
- **Wave completion:** 100 % at every workload in both modes (prior experiment: 44 % / 22 % at 250/500).

## Key experimental observation

"No available driver/vehicle for trip with N request(s)" is **expected fleet-capacity behaviour**:
a 60-driver fleet dispatches at most ~60 trips per pass; remaining demand is queued and fully
served by subsequent waves (100 % completion). Not a defect; algorithm untouched.

## Verification

- A-DMFE suite (V1–V10): 53/53 passed.
- API smoke tests: all endpoints 200 OK; config PATCH audit-logged; dmfe/run + context functional.
- DB integrity: ok (eval.db, admfe_verify.db, api_verify.db).
- Backward compatibility: static mode regression (V9) passed.
- OR-Tools: 120+ isolated solves stable, no leak; relax-on-no-solution path exercised.
- Frontend: `npm run build` clean.

## Artifacts index

| Artifact | Location |
|---|---|
| Full report | `backend/evaluation/ADMFE_EXPERIMENT_REPORT.md` |
| Results JSON (static / adaptive) | `backend/evaluation/results/admfe_static_experiments.json`, `admfe_adaptive_experiments.json` |
| CSVs | `backend/evaluation/results/admfe_per_workload.csv`, `admfe_comparison_metrics.csv`, `admfe_baseline_comparison.csv` |
| IEEE tables | `backend/evaluation/results/ieee_tables.md`, `ieee_tables.tex` |
| Graph data | `backend/evaluation/results/graphs/*.json` |
| Runner / framework / verification | `backend/evaluation/run_admfe_experiments.py`, `framework.py`, `verify_admfe.py`, `make_admfe_report.py` |
