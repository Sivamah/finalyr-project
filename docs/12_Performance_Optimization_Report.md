# Phase 12: Performance & Stability Optimization Report

Date: 2026-08-06 · Scope: AI-Powered Unified Mobility & Delivery System (A-DMFE)

---

## 1. Root Causes Found (with evidence)

### 1.1 OR-Tools time-dimension model was **always infeasible** — the biggest latency bug
`app/dmfe/optimizer.py::_solve_pdp` sized the time-dimension horizon from the
pickup→drop legs **only**:
```
horizon = (max_allowed_delay + Σ pickup→drop sec) * 60 + 60
```
The real route is depot→pickup→drop (+ service). Measured for a real request:
depot→pickup = 1,464 s, pickup→drop = 1,121 s, service = 120 s → 2,705 s total
vs. horizon 2,381 s. **Every solve was therefore infeasible by construction**:
OR-Tools burned the full 4 s proving infeasibility, then silently re-solved the
relaxed model — so the "maximum delay" constraint was never actually enforced,
and every `arrival_min` in results was 0.0.
**Fix:** horizon now covers the whole route (own-trip + delay budget for n=1;
worst-case route envelope for shared trips). Time model is feasible; `arrival_min`
values are now real (see sample: `[13.0, 31.9]` etc.).

### 1.2 GUIDED_LOCAL_SEARCH always burned the full time limit
Benchmark (same data, 2–4 request trips): GLS produced **byte-identical** routes
(objective + stop order) to the AUTOMATIC metaheuristic while always consuming the
entire 1–4 s window. GLS added pure latency with zero quality gain at this scale.
**Fix:** switch to `AUTOMATIC` (keeps a bounded safety time limit).

### 1.3 Driver selection N+1 (per-trip dispatch)
`app/dmfe/driver_selection.py::select` executed, **per available driver**:
`_active_trip_count` (2 queries) + `_fit_vehicle` (1–2 queries) + `_load_selector_rules`
(6 SystemConfig queries) + `_load_vrp_rules` (10 queries) — ~100+ queries per trip.
**Fix:** active-trip counts in 2 grouped queries, one pre-loaded vehicle pool,
15 s TTL caches for selector + VRP rules. Verified identical candidate selection.

### 1.4 AIOrchestrator N+1 + per-row writes
`app/engine/optimizer.py`: one Provider query per pending request, one per vehicle,
plus one SELECT+UPDATE per request when persisting "Optimized" status.
**Fix:** single provider map (2 queries total) + bulk `UPDATE ... WHERE id IN`.

### 1.5 Dashboard stats loaded the full Trip table
`app/api/routes/dashboard.py::/stats` did `Trip.query().all()` and summed in Python.
**Fix:** `COUNT/AVG/SUM` aggregates + one boolean-count query. Identical output.

### 1.6 Frontend polling firehose
`AdminLayout` polled `/notifications/stats` every 3 s; 8 dashboard pages polled every
2.5–3 s **unconditionally — even with the tab hidden or the browser minimized**.
**Fix:** notification poll → 15 s; all page polls gated on
`document.visibilityState === 'visible'` (zero network while hidden).

### 1.7 Dead code (audit item)
Unregistered routers (`routes/dmfe.py`, `routes/generator.py` + its schema),
unused services (`dataset_service`, `orchestration_service`, `provider_service`),
and frontend scaffold (`AdminDashboard.jsx`, `App.css`, unused SVG assets).
→ moved to `archive/2026-08-06/` (see manifest), never deleted.

---

## 2. Files Modified (this phase)

| File | Change |
| --- | --- |
| `backend/app/dmfe/optimizer.py` | Time-dimension horizon fix; single-request deterministic fast path; `AUTOMATIC` metaheuristic; TTL-cached VRP rules |
| `backend/app/dmfe/driver_selection.py` | N+1 elimination (grouped counts, pooled vehicles); TTL-cached selector rules |
| `backend/app/dmfe/pipeline.py` | Uses cached VRP rules |
| `backend/app/engine/optimizer.py` | AIOrchestrator provider-map + bulk status updates |
| `backend/app/api/routes/dashboard.py` | SQL-aggregate stats instead of full-table load |
| `frontend/src/components/AdminLayout.jsx` | Notification polling 3 s → 15 s + visibility gate |
| `frontend/src/pages/{LiveSimulationMap,ExplanationDashboard,DatasetManagement,DriverDashboard,SimulationMonitoring,AnalyticsDashboard,NotificationCenter,DMFEDashboard}.jsx` | Visibility-gated polling |

Plus (stabilization work verified in this phase, from earlier sessions):
`backend/app/db/database.py` (WAL mode, busy_timeout), `backend/app/core/config.py`
(SECRET_KEY dev fallback), `backend/app/api/routes/orchestration.py` (results
endpoint field mapping), `backend/app/services/driver_service.py` +
`backend/app/main.py` (seed-once startup guard), `backend/app/services/xai_service.py`
+ `backend/app/dmfe/compatibility.py` (TTL caches, hoisted compute).

## 3. Files Archived
`archive/2026-08-06/` — `routes/dmfe.py`, `routes/generator.py`, `schemas/generator.py`,
`services/{dataset,orchestration,provider}_service.py`, `pages/AdminDashboard.jsx`,
`App.css`, `assets/react.svg`, `assets/vite.svg` (+ manifest README). Nothing deleted.

## 4. APIs Fixed
- `POST /api/orchestration/optimize` — was 500 "database is locked" → 200
- `GET /api/orchestration/results` — was 500 (nonexistent Trip fields) → 200
- `GET /api/drivers/stats`, `GET /api/vehicles/stats` — were `PendingRollbackError` → 200
- `POST /api/dmfe/run` — full pipeline 16.9 s → sub-0.25 s
- `GET /api/xai/overview`, `GET /api/xai/explanations` — 75 s / 7 s → sub-second cold, ms warm
- `GET /api/dashboard/stats` — O(n) in-memory → SQL aggregates
- Arrival times: previously always `0.0` in trip results (relaxed solve) → real minutes

## 5. Performance — Before / After (measured, same machine)
| Operation | Before | After |
| --- | --- | --- |
| `POST /api/dmfe/run` (5 reqs) | 16.86 s | 0.10–0.23 s (10–20 reqs) |
| `optimize_trip`, 1 request | 4.02 s | 0.005–0.009 s |
| Shared OR-Tools solve (2–4 reqs) | 4.01 s | 0.003–0.015 s |
| `GET /api/xai/overview` cold | 75.22 s | 1.02–1.09 s |
| `GET /api/xai/overview` warm | — | 0.08 s |
| `GET /api/xai/explanations?limit=20` cold | 7.17 s | 0.16 s |
| `GET /api/xai/explanations?limit=20` warm | — | 0.01–0.07 s |
| `GET /api/orchestration/results` | 500 | 0.02–0.05 s |
| `POST /api/orchestration/optimize` | locked | 0.10 s (12 pending reqs) |
| `GET /api/drivers/stats`, `vehicles/stats` | error | 0.03–0.05 s |
| `GET /api/dashboard/stats` | full-table load | 0.03 s |
| DriverSelector per trip | ~100 queries | 3 queries |
| Notification polling | every 3 s | every 15 s, zero when hidden |

## 6. Verification Report
- **API smoke test:** all 24 live endpoints → HTTP 200 (health, dashboard, providers,
  drivers/vehicles, simulation, analytics, notifications, config, DMFE (analyze/run/
  queue/trips/batches/statistics/context), scenarios, playback, XAI, orchestration).
- **Correctness of optimization output preserved:** identical distances & stop orders
  vs. old 4 s GLS solves (verified on n=2/3/4 trips: 36.23 / 54.71 / 56.92 km);
  arrival minutes now real instead of 0.0; seed logic no longer resets vehicle status
  (DMFE availability gate preserved); batching/priority gates unchanged.
- **Full dispatch cycle:** simulate(15) → run → 20 requests → 6 shared + 7 individual
  trips, 1 legitimate unassigned; trip completion releases drivers/vehicles
  (verified 20 trips completed, fleet re-dispatches).
- **Frontend:** `npm run build` ✓ (857 ms, zero import errors).
- **Backend:** `from app.main import app` ✓ after all changes + archive.

## 7. Technical Debt (known, bounded)
- `xai/overview` cold path recomputes ~200 request explanations (≈1–5 s) when the
  30 s TTL expires; warm reads are ms. Candidate: persisted snapshot table.
- Simulation analytics load the full request table per chart (fine at demo scale;
  consider time-bucketed SQL for production).
- `slowapi>=0.1.9` sits unused in `requirements.txt` (verified never imported) —
  remove when cleaning dependencies.
- Both `OptimizationResult` (legacy) and `Trip` (current) store results; live
  dashboards read `Trip`, legacy writes remain in `/optimize` — consolidation candidate.
- SQLite dev DB with WAL is production-adjacent; PostgreSQL only adds pool tuning.
- Per-page 2.5 s polls remain while the tab is visible (intended for live views).

## 8. Recommendations
1. Move XAI overview to a background-computed, periodically refreshed snapshot.
2. Replace ad-hoc polling with SSE/WebSocket push for live dashboards.
3. Consolidate OptimizationResult into Trip; remove slowapi; pin requirements.
4. Add CI: backend import smoke test + `npm run build` gate.
5. Re-measure with the Google Maps Distance Matrix API enabled (real matrices).

## 9. Production Readiness Score: **8.4 / 10**
Stable, fast, verified end-to-end. Deductions: no automated test suite in-repo,
no rate limiting wired (slowapi unused), SQLite dev fallback, legacy table
duplication, cold XAI overview path.

## 10. IEEE Demo Readiness Score: **9.6 / 10**
All demo flows verified at interactive speed: login → dashboard (30 ms) →
simulate + optimize (0.1 s) → DMFE run (0.2 s, shared + individual trips with
real arrival times) → XAI explanations/overview (ms warm) → live map/playback/
scenarios/notifications. Deductions: warm-up of XAI cache on first page visit
(≤5 s) and 2.5 s live-view polling cadence by design.

---

# Supplement (2026-08-08): DMFE Pairwise-Scan Optimization

Follow-up phase — same correctness contract, faster pairwise evaluation.

## 1. Changes

### 1.1 `app/dmfe/batch_generator.py` — blind O(n²) pair scan → latitude-band scan
Both `create_feasible_batches()` (static mode) and `generate_candidates()` replaced
the nested `for i / for j` loop with a bucketized scan over latitude bands of width
= pickup radius (same bucketing as `CompatibilityMatrix`). Only same-band and
neighbouring-band pairs are visited, plus a cheap longitude quick-check
(`Δlng · 111 · cos(lat) > radius`) before the exact haversine gate — the exact
candidate set of the legacy scan, O(n·k) instead of O(n²).

Bit-identical output is preserved three ways:
- the same pre-check gates run on the same pairs in the same order;
- geodesic/time values computed by the gates are **shared** with the scoring via a
  `precomputed` dict (pickup distance, time diff) instead of recomputed inside
  `CompatibilityCalculator.compute()`;
- per-request trip lengths (`request_metrics`) are computed once for all pairs;
- the greedy assignment sort keeps an `(i, j)` tie-break, mirroring the stable
  scan order of the legacy loop so equal-score candidates claim in the same order.

### 1.2 `app/dmfe/score_engine.py` — metric mirrors
`estimated_delay_score()` and `request_times_within_window()` are now closed-form
mirrors of the compatibility metrics (pickup km at 30 km/h; absolute timestamp
difference) so every component computes the same numbers from the same inputs.

### 1.3 `app/dmfe/compatibility.py` — shared geodesic/time inputs + label mirrors
`compute()` accepts the optional `precomputed` / `request_metrics` inputs; when
present the distance/time metrics are reused verbatim instead of recomputed.
`factor_details` labels (`pickup_distance_m`, `destination_distance_m`,
`direction_similarity`, `route_overlap_*`, `time_diff_min`) are unchanged in
value and label — verified byte-identical.

## 2. Verification (equivalence, not just "same ballpark")

| Check | Result |
| --- | --- |
| Random-pair score equivalence (3,000 pairs, all 5 factors + details) | 0 mismatches |
| Static `create_feasible_batches` (500 pending, prof.db) vs. legacy reference loop | 236 = 236 batches, 0 mismatches (scores, factors, details) |
| Static `generate_candidates` (500 pending) vs. legacy reference loop | 248 = 248 groups, 0 mismatches |
| A-DMFE adaptive path (prof.db, `admfe.mode=adaptive`) | deterministic: 239 batches × 3 runs |
| `pytest` (tests/) | 14 passed |

## 3. Performance (same machine, static mode, synthetic 0.2° × 0.2° region)

| Pending requests | Legacy O(n²) pipeline | Bucketized pipeline | Speedup |
| --- | --- | --- | --- |
| 500 | 5.57 s | 0.31 s | **18.1×** |
| 1,000 | 11.37 s | 0.91 s | **12.5×** |

The gain is superlinear: the blind scan touches all n(n−1)/2 pairs for gate math;
the bucketized scan only touches pairs inside the pickup radius band (≈O(n·k)).

## 4. Production Readiness Score update: **8.8 / 10**
The "no automated test suite in-repo" deduction is retired — `backend/tests/`
(`test_compatibility.py`, `test_learning_engine.py`) now runs 14 passing tests
(via `pytest.ini`), including regression coverage for the mirrored scoring.

---

# Supplement (2026-08-08): Learning Hot-Path Optimization (Phase 4.1)

Follow-up phase — the A-DMFE learning engine's per-trip ingestion hot path,
with a full guardrail test suite to lock the contract.

## 1. Changes (backend/app/dmfe/adaptive/learning.py)

| Item | Before | After |
| --- | --- | --- |
| Corridor / batch lookups per trip | `_estimated_delay`, `_estimated_utilization`, `_expected_fuel` each re-queried the batch row; corridor query once | `_batch_row` fetched **once** per trip and threaded through all lookups (single-pass); `_trip_corridor` unchanged in behaviour |
| Refit work per trip | every ingestion re-scanned ring buffers and re-aggregated all corridors | aggregation runs **only on exact REFIT_INTERVAL multiples** (10 refits per 2,000 trips) — mid-window trips do a cheap `count % interval` check |
| Residual ring size | 500 per signal | `RESIDUAL_BUFFER_SIZE = 200` (= one refit window) — no sample needed for a refit is ever evicted, and the per-trip persisted payload (JSON load + save) shrinks ~2.5× |
| Refit observation window | ring blended up to 2.5 windows of history | each refit observes exactly the current window (cleaner signal; refits remain drift-damped) |

## 2. Measured (same machine, in-memory SQLite, engine-only hot path)

| Operation | Before | After |
| --- | --- | --- |
| State load + save per trip (2,000-trip history) | 4.73 ms | 2.52 ms (−46 %) |
| Engine-only ingestion, 2,000 trips | — | 5.96 ms/trip (168 trips/s), ring capped at 200, refits at exact multiples |

## 3. Guardrail tests (10 new, backend/tests/test_learning_phase4_1.py)

Ring bounds at the cap; factor clamping to [0.5, 2.0]; refit cadence only on
interval multiples; per-corridor min-sample gating; corridor isolation; delay
vs utilization signal separation; state durability across a session restart;
corrupt-state JSON fallback; no-actuals ingestion guard; wall-clock hot-path
budget (25 s for 2,000 trips — catastrophic-regression tripwire with 2× headroom).

Full suite: **54 passed** (was 44). Test expectations for the old 500-size ring
were updated in `test_learning_engine.py` / `test_learning_phase4.py` to the
documented cap contract (`min(samples, RESIDUAL_BUFFER_SIZE)`; damped refit
window = 1.5 at 2× ratio).
