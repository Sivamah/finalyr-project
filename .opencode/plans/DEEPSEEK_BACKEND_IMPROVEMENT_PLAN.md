# DeepSeek Backend Improvement Plan (Stage 1)

> Companion to `docs/reports/FINAL_BACKEND_ACCEPTANCE_REPORT.md`.
> Stage 1 = fresh source verification of the 7 audit findings.
> Stage 2 = implementation in this plan's priority order.

## 1. Executive Summary

A-DMFE backend readiness: **74.2%** (verdict READY WITH WARNINGS in audit).
All 7 audit findings were re-verified against current source. Every finding is
**CONFIRMED present**; none refuted and none already fixed. Fixes are small,
additive (nullable columns / new response flags), and preserve all research,
compatibility, route and orchestration semantics. Non-negotiable guards: no
redesign, no frozen-formula changes, no reviewer-experiment edits, no fabricated
historical values, smallest-safe-change per fix.

## 2. Baseline (74.2%)

| Area | Weight | Score |
|---|---|---|
| Core DMFE | 30% | 78 |
| Research | 20% | 65 |
| Data | 15% | 75 |
| API/Security | 10% | 75 |
| Testing | 15% | 80 |
| Performance | 10% | 70 |

Re-audit uses the SAME 7 areas and same weights, measured BEFORE/AFTER with
per-area evidence. No target percentage is assumed; fixes optimize the project.

## 3. Confirmed Problems (fresh verification)

| # | Severity | Problem | Evidence in current code |
|---|---|---|---|
| 1 | HIGH | Re-dispatch of Assigned/Completed requests succeeds | `app/dmfe/driver_selection.py:650` `create_assignment` checks driver status + capacity only, never request status; `app/api/routes/dmfe_engine.py:270` `/assign/driver` has no request-status guard. Live evidence: duplicate Active trip 4453 (re-dispatch of 4441) and trip 4454 reviving Completed request 6562. |
| 2 | HIGH | XAI recomputes decision at query time, contradicting stored dispatch | `app/services/xai_service.py:245-252` recomputes against latest-20 partners; deployed decisions already stored on `dmfe_batches` (per `pipeline.py:266,335`). Live evidence: historical request 12 explained as incompatible while stored dispatch was shared. |
| 3 | MED | Duplicate `request_ids` → HTTP 500 | `app/api/routes/dmfe_engine.py:100-117` `/compatibility-score` has no try/except; `_load_requests` SQL `IN(6572,6572)` returns one row → `ValueError("Need at least 2 requests")` escaped as 500. |
| 4 | MINOR | `/api/drivers/{id}` resolves by substring search | `app/api/routes/drivers.py:69` `search=str(driver_id)`; id 1 returned driver 61. PATCH/DELETE use exact PK. |
| 5 | MINOR | `failed_gate` mislabeled on rejected batches | `app/api/routes/orchestration.py:365-371` keyword scan; capacity/weight/no-driver rejections fall through to "rejected"/"bqs" keyword hits (32 of 40 sampled mislabeled). |
| 6 | MINOR | Synthetic XAI timeline + fabricated fallback values | `xai_service.py:305-319` no-partner factors 50/50/50/90/60 and `:335` confidence `70+overall*0.35`; timeline uses `created_at+2/4/6s` forever (`:342-370`). |
| 7 | MED | Batch formation slow: 33.2s@25 / 40.9s@50 / >10min@100 | `app/dmfe/adaptive/matrix.py:115-205` per-pair adaptive `compute()` repeats geodesic/trip-metric work the static path already shares (`batch_generator.py:207-216`). Exact hotspot to be located by cProfile in Phase E. |

## 4. Root Cause per Problem

1. No lifecycle guard — dispatch contract checks only driver/vehicle availability.
2. No stored-decision replay — XAI re-runs the engine instead of reading the persisted decision record that every dispatched request already has.
3. Unvalidated input and uncaught `ValueError` on the only public compute endpoint.
4. Driver-ID resolved through the fuzzy `search` filter instead of the primary key.
5. `failed_gate` derived from free-text keywords instead of the real gate, which is already encoded as the first `✗` reason in stored `reason_json`.
6. Placeholder timestamps and values hard-coded to give the UI forward-looking shape.
7. The adaptive matrix loop redoes heavy per-call work per pair instead of reusing precomputed values.

## 5. Risk Classification

- **High** — #2: alters XAI output; must preserve live evaluation for un-evaluated requests and pass existing static-mode tests.
- **Medium** — #1: guard lives in shared `dispatch_trip`; must not break the pipeline (only Pending/Evaluated ever routed).
- **Low** — #3..#7: isolated, additive, revert-safe.

## 6. Recommended Fix (smallest safe) per finding

1. Add request-status guard in `dispatch_trip`: legal statuses `Pending`/`Evaluated`; otherwise raise `ValueError("request #x already <status>")` → `/assign/driver` surfaces as **409**. Endpoint pre-validates duplicate ids.
2. See §7.
3. `/compatibility-score`: reject duplicate ids **422**; fewer than 2 unique **400**; wrap compute (`ValueError`→422, other→500). `/assign/driver` duplicate ids → **400**.
4. `drivers.py` GET → `Driver.id == driver_id` primary key lookup; 404 when missing.
5. `_batch_to_result`: `failed_gate = next((r for r in reasons if r.startswith("✗")), "Incompatible constraints")`. Deterministic, no schema change.
6. See §7.
7. Phase E: profile first; apply provably-equivalent optimizations only (§10).

## 7. XAI Historical-Fidelity Design

Rule, data-driven:
- **Stored decision exists** (a `dmfe_batches` row references the request with status `Dispatched`/`Individual`/`Rejected`) → build the explanation from stored `compatibility_score`, `factor_scores_json`, `factor_details_json`, `reason_json`, `decision`, `estimated_delay_min`; partner = other ids in the batch. Batch index built in-memory alongside the existing trip index.
- **Trip exists, no batch** (legacy rows) → decision/partner from the stored Trip; factor values genuinely absent → **"Not recorded"**, never synthesized.
- **Neither** (un-evaluated / fresh) → keep current live compute (verified correct).

Confidence:
- Add nullable `decision_confidence` column to `dmfe_batches` (additive; same pattern as `predicted_utilization_pct`). Persist from `resolution.decision_confidence` in batch creation (`decision_engine._make_batch_row` and pipeline `_persist_batch`).
- When a stored engine value is absent (old rows / static mode): return the existing score-derived float **but add an additive response flag `confidence_fallback=True`** so the UI can label it "(estimated)". No response-model breaking change; existing static-mode test keeps passing.

Timeline:
- Real timestamps when stored: Request Generated = `req.created_at`; DMFE Evaluation = batch `created_at`; Trip Dispatched = `trip.created_at`; Completed = trip completion time. Synthetic `+2/4/6s` offsets only on the live-fresh path.

## 8. Files / Modules Affected

- `app/dmfe/driver_selection.py` (guard in `dispatch_trip`).
- `app/api/routes/dmfe_engine.py` (validations, error mapping).
- `app/api/routes/drivers.py` (exact PK lookup).
- `app/api/routes/orchestration.py` (`failed_gate`).
- `app/services/xai_service.py` (replay, timeline, fallback flag).
- `app/dmfe/models.py` (+`decision_confidence` column; created on `create_all`).
- `app/dmfe/decision_engine.py`, `app/dmfe/pipeline.py` (persist confidence).
- `app/dmfe/adaptive/matrix.py` (Phase E optimization).
- XAI response schema (additive flags only).
- `frontend/src` (additive display of fallback labels only).
- Verification scripts `verify_unified_scoring.py`, `verify_xai_map.py`, `test_stale_release.py` (real assertions).
- New tests in `backend/tests/`.

## 9. Tests Required (regression per fix)

- **Idempotency**: re-assign Assigned→409; re-assign Completed→409; no duplicate trips; batch re-dispatch guarded; completed requests never return to dispatch.
- **API**: duplicate ids → 422 (`/compatibility-score`) / 400 (`/assign/driver`); <2 unique → 400; `/drivers/{id}` exact match; numeric driver id; unknown id → 404.
- **failed_gate**: weight-limit, capacity, no-driver, gate-A score, BQS cases each map to the true `✗` reason.
- **XAI replay**: explanation decision == stored dispatch for shared AND individual AND rejected requests; confidence fallback flag set only when no engine value stored; timeline uses real stored timestamps; live path unchanged.
- **Perf equivalence**: identical batch output snapshot (adaptive) before/after optimization at n=50.

## 10. Performance Strategy (Phase E)

cProfile batch formation at 25/50/75/100 in adaptive mode. Allowed optimizations only:
- Share `precomputed` pickup distances and `request_metrics` trip lengths into `matrix.build` compute calls (identical geodesic values — exact equivalence).
- Precompute per-request best-partner lists once after matrix build (same ranked output).
- Memoize per-run effective/bqs thresholds.
- NO weight/threshold/formula/OR-Tools changes.

Prove decision equivalence with the §9 snapshot test before and after.

## 11. Frozen Research Logic

Weights, thresholds, 5-factor formulas, A-DMFE adaptive stack (context/weights/learning/BQS/attribution), reviewer experiment files under `evaluation/results/`, and the OR-Tools formulation are frozen. Guard: before any edit, ask — does this change research formulas / reviewer experiments / compatibility semantics / route semantics / breaking API behavior? If yes → document the conflict and choose the smallest non-breaking alternative.

## 12. Implementation Order

Phase A idempotency guard → Phase B XAI replay + confidence + timeline → Phase C API robustness (dup-ids, driver PK, failed_gate, fallback labels) → Phase D regression tests → Phase E performance → Phase F full regression + E2E → re-audit (same 7 areas/weights) → final remediation report.

## 13. Definition of Done

- Every fix implemented with a passing regression test; full pytest suite green (≥ current 112).
- E2E: zero duplicate trips, zero re-assignments, correct status codes on all validation probes.
- XAI: 100% of sampled historical explanations match stored dispatch decisions; no fabricated values; fallbacks explicitly labeled.
- Batch formation at n=100 measurably improved (baseline target set after profiling).
- All verify scripts run and recorded; E2E metrics (created/analyzed/shared/individual/assigned/active/completed/unassigned/duplicates/errors/elapsed) captured.
- Re-audit report with per-area BEFORE/AFTER and a final verdict: READY FOR FINAL PROJECT FREEZE / READY WITH NON-BLOCKING WARNINGS / NOT READY — FIX REQUIRED.

## Decisions (user-approved)

- XAI confidence when no stored engine value: keep the score-derived float and add additive `confidence_fallback=True` flag (UI labels "(estimated)").
- Weak verify scripts (`verify_unified_scoring.py`, `verify_xai_map.py`, `test_stale_release.py`) will be fixed to contain real assertions.
- Stage 2 implementation authorized.

## Approval

Plan approved; Stage 2 (implementation) authorized.