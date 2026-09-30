# FINAL BACKEND ACCEPTANCE REPORT — A-DMFE

**Audit target:** `D:\rapidoproject\backend` (FastAPI + A-DMFE adaptive engine, OR-Tools)
**Date:** 2026-09-22
**Mode:** Independent, evidence-first read-mostly audit. HTTP probes ran against an **isolated copy** of the dev DB (`audit.db`). Engine internals were exercised against fresh in-memory SQLite. No project code was modified.
**Audit baseline (git):** `main @ 2d3b06a`; pre-existing dirty: `backend/VERIFY_RESULTS.md`, `orchestration.py`, `evaluation/results/unified_validation.json`, `frontend/...`.

---

## BACKEND READINESS: 74.2%

**Verdict: READY WITH WARNINGS** — the core A-DMFE pipeline (compatibility → BQ-gated batching → decision → OR-Tools routing → dispatch → completion) is functional, idempotent in the current code, and covered by a passing 112-test suite. Release is acceptable only after addressing the **assignment-request-status guard** (HIGH), **XAI fidelity for historical requests** (HIGH), and confirming the **batch-formation scaling** plan.

| Category | Weight | Score | Rationale |
|---|---|---|---|
| Core | 30% | 78% | Full engine chain verified live (dispatch/completions); one HIGH assignment-integrity defect; minor orchestration gate-mislabel. |
| Research | 20% | 65% | Adaptive formulas/weights/BQS real and cross-checked bit-exact; XAI recompute-at-query contradicts stored history; several 0-assert verification scripts. |
| Data | 15% | 75% | Datasets/sim/notifications all PASS; shipped DB still contains historical duplicates / Busy-leaks (not reproduced by current code). |
| API/Security | 10% | 75% | Auth 9/9 PASS; robustness mostly clean; 2 confirmed defects (driver-id string match, dup-id → 500); no rate-limiting exercised. |
| Testing | 15% | 80% | 112 pytest PASS / 0 fail / exit 0; runtime HTTP-layer coverage exists only via ad-hoc scripts (weak asserts); verify_all.py is sound. |
| Performance | 10% | 70% | Scoring ~10ms, OR-Tools ≤44ms (excellent); E2E 110ms/req; **batch formation 33s@25 → 41s@50, >10min @100 (super-linear)**. |

**Weighted total = 0.30×78 + 0.20×65 + 0.15×75 + 0.10×75 + 0.15×80 + 0.10×70 = 74.2%**

---

## Confirmed Defects (current code)

1. **HIGH — `/api/dmfe/assign/driver` dispatches requests whose status is not Pending.** `AssignmentEngine.create_assignment` (`driver_selection.py:650`) checks driver-availability and capacity only; it never validates request status. Evidence:
   - Re-dispatching already-`Assigned` 6560+6561 created a **second** Active trip 4453 while original trip 4441 was still Active (2 Active trips per request).
   - Dispatching `Completed` request 6562 created a new Active trip 4454, reverting the request to `Assigned` and re-grabbing a driver/vehicle.
   - Same defect class as the historical TOCTOU double-dispatch found in Phase 2 data.
2. **HIGH — XAI explanations recompute the decision at query time** instead of replaying the stored dispatch. `xai_service.py` pairs each request against the **20 most recent** requests (`_MAX_PARTNERS=20`) and re-scores. For historical request #12 the stored trip is shared (`BATCH-0012-0013`) yet its explanation says "Standalone Direct Routing … A-DMFE REJECTED … time diff 27225.7 min" and pairs it with demo request 6585 (seeded ~19 days after dispatch) — anachronistic and contradictory. Fresh requests (e.g., 6574 → "Compatible for Batching … share a vehicle with #6575") match perfectly; only historical explanations drift.
3. **MEDIUM — `/api/dmfe/compatibility-score` and `/optimize/route` return HTTP 500 for duplicate `request_ids`** (`[6572,6572]`). `compute()` raises unhandled `ValueError("Need at least 2 requests …")` because the SQL `IN (6572,6572)` collapses to one row. Regression risk is input-level only (no data corruption).
4. **MINOR — `/api/drivers/{id}` matches by string** (`driver_service.get_drivers(search=str(id))`): `GET /api/drivers/1` → driver 61, `GET /api/drivers/-5` → driver 66.
5. **MINOR — orchestration `failed_gate` mislabels rejected results** (32/40 sampled): keyword scan picks the informational "…BQS 0.83 ≥ θ_bqs…" line as the failed gate instead of the real "✗ No feasible driver…". Underlying `reason_json` is correct; UI-only impact.
6. **MINOR — XAI timeline timestamps are synthetic** (created_at+2s/+4s/+6s), contradicting the docstring "actual lifecycle timestamps"; the no-partner fallback fabricates factor scores (50/50/50/90/60) and fixed confidence 70.0.
7. **Performance risk — batch formation `BatchGenerator.create_feasible_batches` is super-linear.** Measured in-process: 33.2s (median) @ 25 pending, 40.9s @ 50, >10 min @ 100 (timed out). Contribution dominates the A-DMFE adaptive matrix stage; single-request/pair ops are sub-15ms.

---

## Phase-by-Phase Evidence

1. **Architecture** — Modular and sound: `routes → services → dmfe engine (decision_engine / batch_generator / compatibility / optimizer / driver_selection / pipeline)`. Layering verified by source review and live calls. PASS.
2. **DB integrity** — Current code is clean; the *shipped snapshot* carries historical issues: 637 duplicate un-dispatched batch rows; duplicate dispatch codes (BATCH-3325-3326 → trips 2236+2247; BATCH-3327-3328 → trips 2238+2248); a few Busy-without-active-trip drivers/vehicles (8 drivers / ~8 vehicles, pre-Sept-13). Not reproduced by Phase 6+ code. Data-15% context.
3. **AUTH** — `/api/auth/login`, `/profile`, `/logout`, all admin endpoints require bearer; 9/9 scenarios PASS (valid login/profile; wrong password 401; missing/invalid/expired token 401/403; admin-gated DMFE/XAI/dashboard endpoints reject anon).
4. **A-DMFE engine** — Live matrix: same-corridor pair CS 96.2 (Compatible), cross-corridor 66.1, far-pickup 53.0 (Individual), mixed-service 53.8, triple 75.7, budget-weight 87.6-110.7, A-DMFE threshold 60.7 for the demo context. **Cross-check: HTTP CS == engine `CompatibilityCalculator.compute` == serialized response (bit-exact 96.2 / BQS 0.8732 / conf 84.5).** Weights correctly adapt by context (0.2635/0.3025/0.1955/0.1509/0.0876 for in-pair; 0.2779/0.2646/0.2061/0.1591/0.0923 for cross). Missing id → 400; single id → 422. PASS.
5. **Idempotency** — Double `/analyze` produced +0 duplicate batches (runs 83→84→85; batches 7581→7591 then stable); `_find_existing_live_batch` dedupes. PASS.
6. **OR-Tools** — Verified single-request fast path (`TRIP-6572`, 2 stops, no OR-Tools dependency path) and PDP shared routes: pickup-before-drop invariant held, arrivals monotonic, capacity enforced (`Vehicle capacity 1 < combined demand 2` → 400), cost = distance-weighted + time + fuel, haversine fallback matrix. Error paths 400/404 correct. PASS.
7. **Assignment** — Dispatch works end-to-end (trip+assignment+history committed atomically; driver/vehicle Busy; batch Dispatched). Unit-class error paths fine. **But request-status guard is missing → Defect #1.** FAIL (guard) / PASS (mechanics).
8. **Lifecycle** — Complete releases 5-way (trip Completed / driver Available / vehicle Available / requests Completed / assignment+history Completed, verified per row). Already-completed → 200 (idempotent); missing → 404. Stale release correctly requires `age ≥ planned_duration + 15min grace` (trip 4449 dur 63.9min/service correctly retained; 5 genuinely stuck trips released). PASS.
9. **Orchestration** — `/results` with all/accepted/rejected filters (200), real accepted trips (BATCH-6564-6565, driver 10, co2 0.97), rejected have driver/vehicle None + no route + co2 0. Response keys `estimated_cost/eta_mins/distance_saved_km`. **Only `failed_gate` mislabel → Defect #5.** Minor.
10. **XAI** — `/overview`, `/explanations`, `/explanations/{id}` all 200 with real factors/trips for fresh requests; rejected/never-dispatched → 404 (no fabrication). **Historical fidelity broken by live recompute → Defect #2.** Synthetic timeline + formula fallback → Defect #6.
11. **Datasets/Simulation** — Datasets list/upload (CSV row-count, UTF-8 validation → 400 on binary)/delete; scenarios list/create/delete-preset-guard; saved sims list/dashboard/detail/compare (422 without params); simulation status/queue/history/analytics/advanced-analytics. All PASS.
12. **Analytics/Notifications** — Dashboard stats (6581 reqs / 7591 batches / 47.5% batch rate / 3004 kg CO2), provider breakdown, recent results; notifications stats/list/category/read-status/search/timeline + PATCH read (persisted to `system_notifications.is_read=1`) + bogus-id 404. clear-all intentionally NOT executed to preserve fixture. PASS.
13. **Robustness** — Clean 4xx/422 across ~30 error scenarios; two input-bug 500s: driver-id (Defect #4) and dup-id compatibility (Defect #3). No internal server trace on any other path.
14. **pytest** — `pytest -p no:warnings` → **112 passed, 0 failed, 0 skipped, exit 0, 55.9s**, in-memory isolated DB per test (no contamination). PASS.
15. **Performance** — Scoring medians 9.2/10.7/12.3ms (2/3/5 reqs); PDP 2.4/4.5/6.5/16.5/43.5ms (2/4/6/10/15 reqs); pipeline n=50 E2E 5.5s (110ms/req, 23 shared trips). **Batch formation regression → Defect #7.**
16. **E2E** — One controlled pass: analyze (run 86, 8 batches, avg CS 96.3) → batch/create → optimize — dispatch (trip 4455, shared) → complete → XAI 6574 correct → dashboard/history reflect. PASS (fresh requests).
17. **Research integrity** — `evaluation/framework.py` is a genuine baseline-comparison harness (per-stage probes, workload runner, DB metrics). However `verify_unified_scoring.py` (0 asserts, always exit 0), `test_stale_release.py` (FAIL is print-only, exit 0), `verify_xai_map.py` (0 asserts), `check_status.py` (informational), `verify_50_e2e.py`/`verify_demo.py`/`check_results_consistency.py` (0-2 asserts) do **not** gate on correctness; only `scripts/verify_all.py` (703 lines, PASS/FAIL accounting, non-zero exit) enforces. The trusted assertion layer is the pytest suite. WARNING.

---

## Full defect register
| # | Sev | Area | Defect | Evidence |
|---|---|---|---|---|
| 1 | HIGH | assignment | no request-status guard; re-dispatch of Assigned/Completed creates duplicate/wrong Active trips | trips 4453 (dup of 4441), 4454 (revived 6562) |
| 2 | HIGH | XAI | decision recomputed at query vs stored dispatch; historical explanations contradict ground truth | req 12: stored shared, explanation "Standalone/A-DMFE REJECTED" + partner 6585 (post-dispatch seed) |
| 3 | MED | robustness | dup request_ids → HTTP 500 on /compatibility-score, /optimize/route | `[6572,6572]` → 500, ValueError in compute |
| 4 | MINOR | drivers API | `{driver_id}` matched by string search | id 1 → driver 61; id -5 → driver 66 |
| 5 | MINOR | orchestration | failed_gate keyword scan mislabels (informational BQS line wins) | 32/40 rejected batches wrong gate; reason_json correct |
| 6 | MINOR | XAI | synthetic timeline offsets; fabricated fallback factor scores | docstring vs implementation |
| 7 | MED | perf | batch formation super-linear (33s→41s→>10min @ 25/50/100) | in-memory measurement |

## Unresolved historical (data-level, not current code)
- 637 duplicate non-dispatched batches (Phase 2 audit) — cleanup recommended.
- Older duplicate dispatch codes / Busy leaks date to pre-Sept-13 dispatch paths; not reproduced by current idempotent logic.

## Recommended before release
1. Add request-status (`Pending`, `not Assigned/Completed`, no other Active trip) guard in `create_assignment`; return 4xx.
2. Replay stored dispatch for XAI (link explanation to the actual Trip/batch), or drop historical explanations to a "not available" state; keep 404 for never-dispatched.
3. Deduplicate `request_ids` (and batch ids) at route/engine boundary → 400, never 500.
4. Fix `driver_id` lookup to numeric equality.
5. Profile/throttle `BatchGenerator.create_feasible_batches` (candidate-bucket reuse, or cap matrix with early BQ filter) to restore sub-second formation at ≥100 pending.
6. Convert remaining `verify_*.py` to assertion-gated scripts or fold into pytest; make `test_stale_release.py` FAIL exit non-zero.