# A-DMFE — Final Pass Report

**Date:** 15 August 2026 · **Scope:** evaluation reporting corrections only. No engineering, no features, no research-logic changes.

---

## Final Changes Made

| ID | Area | Change | Evidence | Verification | Research Impact | Status |
|---|---|---|---|---|---|---|
| F1 | `evaluation/framework.py` | `avg_waiting_min` now explicitly assigned from `avg_delay_min` with a comment stating it is an alias; key retained so existing result JSONs still parse | `:562-574` | `py_compile` OK; consumers in `analyze_unified.py` / `final_validation.py` still resolve | None — same value as before | Done |
| F2 | `evaluation/framework.py` | `collect_metrics` completion counter unified to `("Assigned", "Completed")`, matching the three wave counters | `:523` was `== "Assigned"` only | `compileall` OK | Changes `requests_completed` / `requests_failed` → **regeneration required** | Done |
| F3 | `make_admfe_report.py` | `"Avg waiting (min)"` removed from `METRIC_LABELS`; `LOWER_BETTER` entry removed | duplicate of `"Avg delay (min)"` | guard C1 | Removes a duplicate published result | Done |
| F4 | `make_admfe_report.py` | Rows relabelled: `Requests dispatched` / `Requests undispatched` / `Waves dispatch rate (%)` | `:47-57` | guard C2 | Honest terminology; values unchanged by the rename itself | Done |
| F5 | `make_admfe_report.py` | `avg_waiting_min` column dropped from `admfe_per_workload.csv`; header and row both 29 fields | AST check: `header=29 row=29 ALIGNED` | AST field-count check | Removes duplicate column | Done |
| F6 | `make_admfe_report.py` | Baseline-comparison tuple `("avg_waiting_min", …)` replaced with `("avg_delay_min", …)` | `:290` | `py_compile` OK | Removes duplicate row | Done |
| F7 | `make_admfe_report.py` | `graphs/waiting_time.json` retitled "Average Trip Delay", series sourced from `avg_delay_min`; filename kept so existing consumers do not break | `:570-578` | `py_compile` OK | Plot now named for what it plots | Done |
| F8 | `final_validation.py` | `MOBILITY / waiting` row removed | `:54` carried identical values to the `delay` row | `py_compile` OK | Removes duplicate | Done |
| F9 | `analyze_unified.py` | Row reading `waves.mean_delay_error_min` relabelled "Delay prediction error (min)"; the `avg_waiting_min` row relabelled "Avg delay (min)" | `:18-25` | `py_compile` OK | Two mislabels corrected; no value change | Done |
| F10 | `docs/04_IEEE_Paper_Draft.md` | Table 1 row `Avg waiting Δ` → `Avg delay Δ`; Table 2 notes it is the same measure | `:44-48` | grep: no `avg waiting` remains | Removes the duplicate claim | Done |
| F11 | `docs/04_IEEE_Paper_Draft.md` | Table 4 and Conclusion: "100% completion" → "100% dispatch rate", with an explicit note that it is dispatch success, not trips run to completion | `:52`, `:69` | grep | Corrects an over-claim | Done |
| F12 | `docs/04_IEEE_Paper_Draft.md` | Two limitations added: waiting time is not independently measured; reported rates are dispatch rates | Limitations section | grep | Discloses both corrections | Done |
| F13 | `scripts/check_results_consistency.py` (new) | Guard: C1 duplicate value series, C2 forbidden labels, C3 paper figures traceable to CSVs, C4 result staleness vs engine mtimes | smoke-run against current results | `ruff` clean, `py_compile` OK | Prevents recurrence | Done |

`compileall` passes. `ruff --select F,E9,B` is **54**, unchanged from the state DeepSeek left; my edits added zero findings.

---

## Evaluation Metric Corrections

**Item 1 — `avg_waiting_min` ≡ `avg_delay_min`.** Treatment chosen: **remove the duplicated metric from the reported comparison.**

The alternative — defining a genuinely distinct waiting time — was rejected on evidence, not convenience. A passenger waiting time (dispatch → pickup arrival) is not reconstructible from the current schema: `Trip.eta_min` stores the route duration, not the driver's ETA to the first pickup, and that ETA is only ever written into the batch reason text. Persisting it would need a new `Trip` column — a schema change, which is a hard stop. Inventing a metric merely to have two numbers is exactly what your brief forbids, so the honest treatment is to report one measurement once and disclose the limitation. That disclosure is now in the paper.

`avg_waiting_min` is still emitted by the framework so old result files remain parseable, but it is published nowhere.

**Item 2 — completion vs dispatch.** Renamed honestly throughout, as you preferred. `"Assigned"` means the request was given a driver and vehicle; trip execution in the harness is simulated, so completion is not an independently observed outcome. Every published label now says dispatch. The underlying counter was also made self-consistent (F2) — `collect_metrics` counted `"Assigned"` only while the three wave counters counted `("Assigned", "Completed")`, so one key name carried two definitions in a single table.

---

## P0-3 Regenerated Results

**NOT REGENERATED — I cannot execute it.** `ortools` and `sqlalchemy` cannot be installed in this sandbox (pypi, npm and github all return `403`), and `device_bash` — the shell on your machine — has failed on every call for this entire session. There is no path from here to running the evaluation harness.

Everything is staged for you to run it in one sitting:

```bat
cd D:\rapidoproject\backend
.venv\Scripts\activate

REM 1. preserve the pre-fix results as a separate, clearly-labelled set
mkdir evaluation\results_prefix_p0_3
xcopy /E /I evaluation\results evaluation\results_prefix_p0_3

REM 2. regenerate with the corrected implementation
python -m evaluation.run_admfe_experiments
python -m evaluation.make_admfe_report
python -m evaluation.final_validation

REM 3. verify
python scripts\check_results_consistency.py
```

Two things to hold to when the numbers come back:

- **Do not reconcile against the old 4.3–5.4 min delays.** If the corrected relaxed-route path changes them, the new values are the authoritative ones and the old ones were wrong. That is the entire point of P0-3.
- **Keep the two sets apart.** `results_prefix_p0_3/` above exists so nothing pre-fix is silently mixed into a post-fix table.

One piece of real evidence on exposure: `qa/server_err.log` (485 lines, a genuine backend session) contains **zero** occurrences of `"no solution with time dimension"`. That is the first runtime evidence the relaxed path was not taken — but it is one session, not the original experiment runs, so it does not excuse regeneration.

---

## IEEE Paper Consistency

Verified statically; the numeric cross-check must be re-run after regeneration.

The new guard's C3 already flags what will need hand-editing. Against the current tables:

```
paper percentages traceable to the generated tables — 83% traceable (23 distinct figures)
quoted in the paper but not found in the CSV: 31.5, 57.9, 68.0, 7.7
```

Those four are the stage-share figures (Table 3) and the XAI confidence value — they come from sources other than `admfe_comparison_metrics.csv`. After regeneration, re-read §V and update every quoted figure by hand. Prose does not regenerate itself, and C3 is the check that tells you when it has drifted.

**One finding I did not fix, because it is instrumentation rather than labelling.** The guard's C1 caught a second duplicate I had not identified:

```
DUPLICATE: Decision gate == Learning
      ('50',  '0.00', '0.00', '0.00', '0.00')
      ('100', '0.00', '0.00', '0.00', '0.00')
      ('250', '0.00', '0.00', '0.00', '0.00')
      ('500', '0.00', '0.00', '0.00', '0.00')
```

`decision_total_s` and `learning_total_s` both report 0.00 across every workload and both arms. Table 3 of the paper discusses stage share. Either those stages are genuinely sub-millisecond, or their timers are not attached. **Check this after regeneration** — "learning costs zero time" is a claim an examiner will probe, and I did not want to touch the timing instrumentation on a freeze pass.

---

## Research-Sensitive Logic Verification

Confirmed unchanged by empty diff against the validated handoff state:

```
dmfe/scoring.py            dmfe/adaptive/decision.py     dmfe/adaptive/learning.py
dmfe/score_engine.py       dmfe/adaptive/context.py      dmfe/adaptive/weights.py
dmfe/batch_generator.py    dmfe/adaptive/factors.py      dmfe/adaptive/batching.py
db/models.py               core/security.py              api/routes/auth.py
```

- `compatibility.py` shows a diff, but it is DeepSeek's two `pass` → log-call replacements. No formula, no weight, no threshold.
- `optimizer.py` shows a diff limited to the P0-3 arrival-clock reconstruction and the P1-4 `d_idx` argument. Objective callback, capacity/distance/time dimensions, pickup-and-delivery constraints, `SetGlobalSpanCostCoefficient` and search parameters are byte-identical.
- The adaptive threshold formula, `driver_scarcity` sign, Gate-D semantics, batching and feasibility rules, CORS and `unified_scoring_enabled` are all untouched.
- The previously-suspected "threshold starvation" was **not** treated as a defect and nothing was lowered to increase batch counts.

---

## Tests Executed

| Check | Result |
|---|---|
| `python -m compileall app tests evaluation scripts` | **PASS** |
| `ruff check --select F,E9,B .` | **54** — unchanged; my edits added zero |
| `py_compile` on all five touched evaluation files | **PASS** |
| `ruff` on `check_results_consistency.py` | **clean** |
| Per-workload CSV header/row alignment (AST) | **29 == 29, ALIGNED** |
| Consistency guard, smoke-run against current results | Runs correctly; **3 of 4 FAIL as designed** (the failures are the pre-regeneration state it exists to detect) |
| `pytest tests/` | **NOT RUN** — no `pytest`/`sqlalchemy`/`ortools` here |
| `scripts/verify_all.py` | **NOT RUN** — same |
| `npm run lint` / `npm run build` | **NOT RUN** — npm registry returns 403 |

---

## Live E2E Result

**NOT EXECUTED.** Stating the exact limitation, as required:

- `mcp__claude-in-chrome__list_connected_browsers` returns `[]` — no browser automation is available, so no page, click, map, fullscreen, or console check was performed.
- `device_bash` returns *"Workspace unavailable — the isolated Linux environment on this device failed to start"* on every call, so I cannot start your backend or frontend, run `e2e_test.py`, or run `git`.
- This sandbox cannot reach your `localhost` and cannot install `ortools`, `sqlalchemy`, `fastapi` or `pytest` (registries return `403`).

**No claim is made about login, dashboard, fleet counts, map rendering, simulation, queue, A-DMFE analysis, batches, driver/vehicle assignment, trip lifecycle, XAI, analytics, replay, duplicate assignments, API 500s, or frontend errors.** The engineering pass reported those as passing; I did not re-verify them and I am not asserting them.

---

## Remaining Issues

1. **P0-3 regeneration outstanding** — the blocking item. Commands above.
2. **Paper figures need a hand pass after regeneration** — C3 currently flags 4 untraceable figures (31.5, 57.9, 68.0, 7.7).
3. **`decision_total_s` and `learning_total_s` both report 0.00** at every workload. Verify the timers are attached before defending Table 3.
4. **Live E2E unverified** in this session.
5. Two open hard stops from earlier passes, unchanged and deliberately not touched: the `/analyze` (`created_at.desc()`) vs `/dispatch` (`.asc()`) ordering split, and the public `SECRET_KEY` fallback plus unconditional `admin@aiorch.com` / `admin123` seed.
6. `ruff` 54 findings — pre-existing unused imports and loop variables, deliberately left.
7. Still **not committed and not pushed** — no shell on your machine. When you do push, use the `finalyr` remote; `origin` points at `RapidoProject`.

---

## Final Readiness

**NOT READY TO FREEZE.**

Your own freeze criteria require P0-3-affected results regenerated, paper tables matching generated results, regression tests passing, and live E2E passing or its limitation documented. Four of the five are satisfiable by me and are satisfied; the two that require execution — regeneration and testing — are not, and I will not certify them on inference.

| Freeze criterion | Status |
|---|---|
| Evaluation corrections complete | **Met** (F1–F13) |
| P0-3 affected results regenerated | **Not met** — cannot execute |
| Paper tables match generated results | **Blocked** on regeneration; guard in place to verify |
| Research-sensitive algorithms unchanged | **Met** — verified by empty diff |
| Regression tests pass | **Not run** |
| Live E2E passes, or limitation documented | **Limitation documented above** |

The repository is in a clean, self-consistent state and the remaining work is mechanical: run the four commands, confirm `check_results_consistency.py` reports 4/4 PASS, update the quoted figures in §V, then freeze.
