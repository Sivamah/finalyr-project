# A-DMFE Master Audit — current-state verification

**Date:** 15 August 2026
**Method:** every claim below was re-derived from the bytes currently on disk at `D:\rapidoproject`. Nothing was carried over from the earlier reports without re-checking.

---

## 0. What I could not execute — read this before the rest

| Capability | Status |
|---|---|
| `git` on your machine | **Unavailable.** `device_bash` (the local Linux workspace) returns *"Workspace unavailable… failed to start"* on every call. No `git status`, no commit, no push. |
| `pytest`, `ortools`, `uvicorn`, `npm` in this sandbox | **Unavailable.** pypi, npm and github all return `403`. `fastapi`, `sqlalchemy`, `ortools`, `pytest` cannot be installed here. |
| Push to GitHub | **Impossible from here**, twice over: no shell on your machine, and the sandbox git proxy refuses your remote. |

So **Phase 0 was done by reading `.git` metadata directly**, and **Phase 10 and Phase 13 are yours to run.** Nothing below is marked PASS unless there is actual output behind it — either from my sandbox, or from your own `VERIFY_RESULTS.md` run, which I read and cite by section.

---

## 1. PHASE 0 — BASELINE (read from `.git`, not from `git status`)

```
branch          main
HEAD            fe7b9bb5fd443d266986f979f1c4c3174114b919
HEAD subject    feat(dmfe): implement Demo Mode isolation and fix stale trips auto-release
prior commit    daf01ad1cd10db29782ca9d4be7d6f8b2d4d0b58
```

### ⚠️ You have two remotes, and `origin` is not the repo you named

```
[remote "origin"]   url = https://github.com/Sivamah/RapidoProject.git
[remote "finalyr"]  url = https://github.com/Sivamah/finalyr-project.git
```

Your brief names the repository as **`Sivamah/finalyr-project`** — that is the **`finalyr`** remote. A `git push -u origin fix/dmfe-dispatch-correctness` would push this work to **RapidoProject** instead. Decide which is intended before pushing; the commands in §9 use `finalyr`.

### Working tree vs `fe7b9bb`

I compared every file mtime and size under `backend/app`, `backend/tests`, `backend/scripts` and `frontend/src` against my own write timestamps. **No file has been edited by anyone else since my last write.** The working tree is exactly `fe7b9bb` plus these 13:

```
M  README.md
M  backend/.env.example
M  backend/requirements.txt          <- new this pass
M  backend/app/api/deps.py
M  backend/app/core/middleware.py
M  backend/app/dmfe/decision_engine.py
M  backend/app/dmfe/driver_selection.py
M  backend/app/dmfe/optimizer.py
M  backend/app/dmfe/pipeline.py
M  backend/app/main.py
M  frontend/src/services/api.js
A  backend/scripts/verify_all.py
A  backend/tests/test_pipeline_accounting.py
```

Untracked and **not** to be committed: `backend/VERIFY_RESULTS.md`, `docs/FIX_REPORT_v2.md`, `docs/AUDIT_REPORT_v3.md` (this file). `.gitignore` already covers `*.db`, `*.db-shm`, `*.db-wal`, `*.log`, `.env`, `__pycache__`, `.venv`, `node_modules`. `backend/seed_users.py` exists on disk — check whether it is tracked and whether it contains credentials before staging anything with `git add -A`.

---

## 2. CURRENT STATUS OF ALL 19 FINDINGS

Verification levels: **RUNTIME** = your `VERIFY_RESULTS.md` run against real ortools/SQLAlchemy · **STRUCTURAL** = AST/source assertion in my sandbox · **HARNESS** = stubbed before/after reproduction · **NONE**.

| # | Finding | Current state | Verified |
|---|---|---|---|
| 1 | P0-1 high-priority requests dropped | **FIXED** — `covered_ids.get(req.id) == "shared"` | RUNTIME + STRUCTURAL + HARNESS |
| 2 | P0-2 rollback erases dispatch metadata | **FIXED** — `db.commit()` after each `_record_dispatch` (2/2 loops) | STRUCTURAL + HARNESS — *no runtime test exercises the multi-batch rollback path* |
| 3 | P0-3 relaxed solve writes duration=0 / negative delay | **FIXED** — arrival clock reconstructed | RUNTIME + STRUCTURAL + HARNESS |
| 4 | P1-4 `SetCumulVarSoftUpperBound` argument | **FIXED this pass** — `d_idx` | STRUCTURAL — runtime probe pending re-run |
| 5 | P1-5 stale-trip cutoff | **FIXED** — floor + own planned duration + grace | RUNTIME + STRUCTURAL + HARNESS |
| 6 | P1-6a context/analysis request-set mismatch | **FIXED** — single `pending` fetch | STRUCTURAL |
| 7 | non-`ValueError` aborts whole run | **FIXED** — recorded as unassigned, run continues (2/2 loops) | STRUCTURAL |
| 8 | adaptive threshold failure swallowed | **FIXED** — `logger.exception` | STRUCTURAL |
| 9 | CSP blocks Swagger | **FIXED** | RUNTIME (`/api/docs` 200, CSP=None; `/api/dashboard/stats` CSP present) |
| 10 | `main.py` session lifecycle | **FIXED** — seed@553 before close@739 | STRUCTURAL |
| 11 | `api/deps.py` unbound `db` | **FIXED** | STRUCTURAL |
| 12 | README/.env.example push a fresh clone to Postgres | **FIXED** | STRUCTURAL |
| 13 | frontend cache stale / mutable / unbounded / session-sensitive | **FIXED** — invalidate on mutation, clone on store *and* read, `MAX_CACHE_ENTRIES=200`, `noCache`, `getCache.clear()` on 401/403 | HARNESS + ES-module parse — **`npm run lint` / `npm run build` never run** |
| 14 | README claims frontend tests that don't exist | **FIXED** | STRUCTURAL |
| 15 | silent exception swallowing | **NOT CHANGED** — audited and classified, §4 | STRUCTURAL |
| 16 | dead/unreachable modules | **NOT CHANGED** — zero-import proof in §5 | STRUCTURAL |
| 17 | unused dependencies | **`requests` ADDED** (was missing, blocked `e2e_test.py`); `slowapi` proven unused but left | STRUCTURAL |
| 18 | remaining lint findings | **NOT CHANGED** — 52 under `F,E9,B`, identical to the pre-work baseline | STRUCTURAL |
| 19 | minor type annotations | **NOT CHANGED** | NONE |

**Correction to the earlier audit:** it reported 16 silent handlers and claimed `app/engine/optimizer.py` was among the dead modules. Both are wrong — see §4 and §5.

---

## 3. PHASE 9 — DEMO MODE (verified, and one real defect found)

Demo Mode lives in exactly two places, and both are **read-only display filters**:

- `backend/app/api/routes/simulation.py` `/queue` — `demo_only: bool = False`
- `backend/app/api/routes/dmfe_v2.py` `/batches` — `demo_only: bool = Query(False)`

Both select on `SimulationRequest.pickup_address.like("[A-DMFE Demo Scenario]%")`.

**Verdict: scientifically clean.** Demo Mode does not touch thresholds, gates, weights, scoring or batch creation. It filters what the dashboard *displays* after the real pipeline has run. `POST /dmfe/analyze` and `POST /dmfe/dispatch` have no `demo_only` parameter at all — there is no code path by which the toggle can influence a decision. When it is off, both endpoints take the original `else` branch, byte-identical to pre-Demo-Mode behaviour. No artificially lowered thresholds, no bypassed gates, no fabricated batches or scores.

### Defect found (not on your list) — unbounded query in the demo path

`dmfe_v2.py::list_batches`, `demo_only=True` branch:

```python
all_batches = q.order_by(DMFEBatch.created_at.desc()).all()   # ← no .limit()
filtered_batches = []
for b in all_batches:
    ...
    if len(filtered_batches) >= limit:
        break
```

`limit` caps the **output**, not the query. Every `DMFEBatch` row is loaded into memory and JSON-decoded on each poll. `DMFEDashboard.jsx` polls this endpoint twice (Pending + Rejected) whenever `lastResult` or `demoMode` changes. Your `dmfe_dev.db` is already 11 MB. This is the exact endpoint you would have open during a viva.

**Proposed fix — HARD STOP–free, but not applied** (it changes a query, and I cannot run the API to confirm the response shape is unchanged):

```python
if demo_only:
    demo_req_ids = {...}                       # set, not list — the `rid in` test is O(1)
    q = q.order_by(DMFEBatch.created_at.desc()).limit(max(limit * 20, 500))
    batches = [b for b in q.all()
               if any(rid in demo_req_ids for rid in json_loads(b.request_ids_json, []))][:limit]
```

Say the word and I'll apply it. Note `demo_req_ids` is currently a **list**, so `rid in demo_req_ids` is a linear scan inside a loop over every batch — O(batches × demo_requests). Making it a `set` is free.

**Robustness note (not a bug):** demo requests are identified by a magic prefix in a user-facing address field. A real request whose address happened to start with `[A-DMFE Demo Scenario]` would be misclassified. A dedicated boolean column would be cleaner, but that is a schema change — hard stop, not worth it.

---

## 4. PHASE 5 — SILENT FAILURE AUDIT

AST scan of `backend/app` for handlers whose entire body is `pass` (or a docstring): **14 handlers, not 16.**

### SAFE (11) — config reads with a documented default

| File:line | Fallback |
|---|---|
| `dmfe/adaptive/learning.py:189` | `learning_enabled` → `True` |
| `dmfe/adaptive/learning.py:199` | `max_bias` → `MAX_BIAS` |
| `dmfe/adaptive/learning.py:634` | `refit_enabled` → `True` |
| `dmfe/compatibility.py:274` | `resolve_mode` → `"adaptive"` |
| `dmfe/compatibility.py:107` | `setattr` on a session attribute cache — cosmetic |
| `dmfe/adaptive/context.py:213,215,228` | traffic multiplier → `TRAFFIC_MULTIPLIER_DEFAULT` |
| `services/simulation_service.py:195,201` | unparsable `start_date`/`end_date` filter simply not applied |
| `services/simulation_service.py:481` | notification logging on simulation start/resume |

These read `SystemConfig` and fall back to an explicit, documented constant. Nothing is fabricated. Leave them.

### SILENT-DANGEROUS (3) — these hide research-metric failures

**1. `dmfe/adaptive/context.py:197`**
```python
except Exception:
    pass  # learning must never break context building
```
The intent is right, but this swallows the failure to attach `learned_fuel_multiplier`, `learned_co2_multiplier`, `learned_utilization_factor`, `learned_delay_residual_mean_min` and `learned_driver_quality` to the context profile. If the learning state fails to load, the run silently reverts to un-learned values and **still reports itself as adaptive**. An A/B comparison could show "adaptive ≈ static" for this reason alone, and nothing in the output would say so.

**2. `dmfe/adaptive/learning.py:341`** — `_predicted_utilization` returns `0.0` on any parse failure. This is the same failure shape as P0-3: zero is not a missing-data marker, it flows onward as a real prediction.

**3. `services/xai_service.py:115`** — if `effective_threshold` raises, the XAI explanation silently uses the *static* threshold while the engine used the adaptive one. The dashboard would then explain a decision against the wrong threshold.

### Why I did not apply the logging

All three live in `dmfe/adaptive/*` or the XAI service. My research-integrity guarantee across this whole engagement rests on `dmfe/adaptive/` being provably untouched, and I cannot run `pytest` to confirm a change there is inert. Adding a `logger.warning` is behaviour-preserving in principle, but "in principle" is not the standard for the adaptive stack. **Proposed patch, ready to apply on your say-so:**

```python
# context.py:197
except Exception:
    logger.warning(
        "A-DMFE: learned multipliers unavailable — context profile built "
        "WITHOUT learning; this run is adaptive in name only",
        exc_info=True,
    )

# learning.py:341
except Exception:
    logger.warning("predicted utilization unavailable for batch %s; "
                   "returning 0.0 as a MISSING marker", getattr(batch, "id", "?"),
                   exc_info=True)

# xai_service.py:115
except Exception:
    logger.warning("effective_threshold failed; XAI is explaining against the "
                   "STATIC threshold while the engine used the adaptive one",
                   exc_info=True)
```

---

## 5. PHASE 8 — ZERO-REFERENCE PROOFS

Proven by AST/grep for actual `import` statements across `app`, `tests`, `evaluation`, `scripts`, `e2e_test.py`:

| Module / dep | Verdict |
|---|---|
| `app/engine/explainability.py` | **Zero imports.** The many "explainability" grep hits are the word in comments and docstrings elsewhere, not imports. Safe to delete. |
| `app/core/coimbatore.py` | **Zero imports.** The frontend has its own `src/utils/coimbatore.js`, unrelated. Safe to delete. |
| `app/engine/optimizer.py` | **NOT dead** — `api/routes/orchestration.py:8` imports `AIOrchestrator`. The earlier report was wrong. Keep. |
| `app/engine/distance.py` | **Heavily used** — 11 import sites including `compatibility`, `optimizer`, `batch_generator`, `driver_selection`. Keep. |
| `slowapi` | **Zero imports.** No `Limiter`, no rate-limit usage anywhere. Removable, but it is a deploy-surface change; left for you. |
| `psycopg2-binary` | **Zero direct imports** — this is correct and it must stay. SQLAlchemy loads it as the driver for `postgresql://` URLs. |
| `requests` | **Was imported but NOT declared** — `e2e_test.py` and `scripts/verify_fix.py`. **Fixed this pass.** |

The `requests` gap is the one that mattered: `python e2e_test.py` is a documented verification step in your Phase 10, and a fresh clone following `requirements.txt` would fail it with `ModuleNotFoundError`.

---

## 6. PHASE 11 — RESEARCH RESULT INVALIDATION

Every file in `backend/evaluation/results/` carries an mtime from the `fe7b9bb` checkout — **all of it predates every fix in this branch.**

### P1-4 delay penalty — provably NOT a contaminant

`admfe_static_experiments.json` records the full config per workload. Across all four workloads (50/100/250/500, seeds 1050/1100/1250/1500):

```
vrp_delay_penalty_per_min in recorded config: <ABSENT>
```

Absent means default, and the default is `0.0`. Independently: with the pre-fix code, any run at a non-zero penalty would have died with the `TypeError` — the feature was never successfully exercised. **Conclusion: all existing results are `penalty = 0.0` baselines and are unaffected by P1-4.** Any future run with the penalty active is a **separate experimental baseline** and must be labelled as such — with the fix in place, a non-zero penalty genuinely changes route selection.

### P0-3 relaxed path — exposure unknown, cannot be ruled out

`verify_all.py` §D found no `*.log` file containing `"no solution with time dimension"`. **This is not evidence of absence** — there are no log files on disk at all, so the marker had nowhere to appear. The framework does not record whether any trip took the relaxed path.

The aggregate delays in `research_summary.md` are 4.3–5.4 min and all positive, and completion is 100%, which is *consistent* with no relaxed-path trips — but averages could mask a small number of negative values.

**Recommendation:** regenerate `evaluation/results/` from the fixed code before submission. The cost is one experiment run; the alternative is a table you cannot defend if asked "were any of these trips recorded with a negative delay?"

Then add provenance to the framework so this question is answerable next time — record the git commit and the full `VRP_RULE_DEFAULTS` snapshot (including `vrp_delay_penalty_per_min`) into each results file, and count relaxed-path solves per run.

---

## 7. PHASE 12 — DIFF REVIEW

```
git diff --check                    clean (no trailing whitespace, no space-before-tab)
secrets in added lines              none
*.db / *.log / __pycache__ / .env   none staged
forbidden tokens in added lines     none
  (unified_scoring, SetArcCost, AddDimension, AddPickupAndDelivery,
   SetGlobalSpan, allow_origins, CORSMiddleware)
```

Untouched, confirmed by empty diff:

- `dmfe/scoring.py`, `dmfe/score_engine.py`, `dmfe/compatibility.py`
- `dmfe/adaptive/` — every module
- `db/models.py` — no schema change, drivers↔vehicles FK intact
- `core/security.py`, `api/routes/auth.py`
- the CORS block in `main.py`
- `unified_scoring_enabled` — never referenced in the diff, remains disabled

The only change inside `optimizer.py` beyond P0-3's `_build_route` post-processing is the single P1-4 argument. Objective callback, capacity/distance/time dimensions, pickup-and-delivery constraints, `SetGlobalSpanCostCoefficient` and search parameters are byte-identical.

`ruff --select F,E9,B .` → **52**, unchanged from the pre-work baseline. The two new files add zero findings.

---

## 8. HARD STOPS — REQUIRES REVIEW

### HS-1 · `/analyze` vs `/dispatch` request ordering (P1-6b)

- **Current:** `decision_engine.run_analysis` reads `SimulationRequest.created_at.desc()`; `PipelineRunner.run` reads `.asc()`. Both `LIMIT 200`.
- **Impact:** above 200 pending, the two act on disjoint sets — the XAI dashboard explains decisions about requests the pipeline will never touch.
- **Recommended common ordering:** `created_at.asc()` (FIFO) on **both**, so `/analyze` explains what `/dispatch` will actually do.
- **Research impact:** `generate_candidates` sorts by `(-score, i, j)` where `i, j` are indices into `pending`. Changing the queue order changes greedy tie-breaking among equal-score pairs, so batch composition can shift even when the request *set* is identical.
- **Must results be regenerated?** Yes, if changed — treat it as a deliberate re-baseline, not a bug fix.
- **Not applied.**

### HS-2 · Auth bootstrap — SECRET_KEY and default admin

- `core/config.py:23` — `SECRET_KEY` falls back to `"aiorch-dev-secret-change-me-in-production"`, a value public in this repository. A production deploy that forgets to set the env var boots with a **predictable JWT signing secret**: anyone can forge an admin token. A warning is logged, but the app starts.
- `main.py:19-28` — seeds `admin@aiorch.com` / `admin123` unconditionally, production included.
- **Both are reachable in production today.**
- **Recommendation.** Development: keep the fallback, but behind an explicit `APP_ENV=development` opt-in. Production: raise at import time when `SECRET_KEY` is unset or equals the dev value, and gate the admin seed behind `SEED_DEFAULT_ADMIN=true` with the password read from the environment.
- **Not applied** — changes startup behaviour and auth bootstrapping.
- This is the item most likely to be probed in a viva, given the README's "Security Hardening Report" and "98/100 Production Ready" claims.

### HS-3 · Adaptive-stack logging (§4)

Three SILENT-DANGEROUS handlers in `dmfe/adaptive/*` and `xai_service.py`. Patch drafted, **not applied**, to keep `dmfe/adaptive/` provably untouched while I cannot run the test suite.

---

## 9. PHASE 10 + 13 — WHAT YOU NEED TO RUN

```bat
cd D:\rapidoproject\backend
.venv\Scripts\activate
pip install -r requirements.txt          REM picks up the new `requests`

python -m compileall -q app tests evaluation scripts
python -c "from app.main import app; print('app.main import OK')"
python -m pytest tests/ -q
python scripts\verify_all.py             REM expect 24 passed, 0 failed

REM needs the server running in another terminal:
REM   uvicorn app.main:app --reload
cd ..
python e2e_test.py

cd frontend
npm install
npm run lint
npm run build
```

`verify_all.py` covers normal / Gate-D / minimal-feasible / no-driver / stale-trip / relaxed-route / repeated-run / **active delay-penalty**. The last one is §C1 and now asserts `PASS`/`FAIL` instead of `INFO`:

```
[PASS] P1-4 — no TypeError with the delay penalty active
[PASS] P1-4 — shared-trip route still solves with the penalty on
```

Then, **only if all of that is green:**

```bat
cd D:\rapidoproject
git checkout -b fix/dmfe-dispatch-correctness
git status
git diff --check

git add README.md backend/.env.example backend/requirements.txt backend/app ^
        backend/tests/test_pipeline_accounting.py backend/scripts/verify_all.py ^
        frontend/src/services/api.js
git status                               REM confirm no .db / .log / .env / __pycache__
git commit -F docs\commit_message.txt

REM NOTE: `finalyr`, not `origin` — origin points at RapidoProject
git push -u finalyr fix/dmfe-dispatch-correctness
```

---

## 10. FINAL STATUS

**Bugs fixed this pass:** P1-4 (`d_idx`), plus the missing `requests` dependency. Everything else on the list was already fixed in the working tree and was re-verified against current bytes rather than taken on trust.

**Runtime verification:** 22/0/1 from your own run, covering P0-1, P0-3, P1-5, CSP and all six DMFE scenarios. P1-4 and the two new assertions are pending your re-run. `pytest` reported 63 tests passing. `npm run lint` / `npm run build` and `e2e_test.py` have **never been run** in this engagement.

**Research integrity:** scoring, compatibility, adaptive learning, the OR-Tools objective and search model, the schema, the drivers↔vehicles FK, auth and CORS are all provably untouched; `unified_scoring_enabled` remains disabled.

**Git:** branch `main`, HEAD `fe7b9bb5fd443d266986f979f1c4c3174114b919`, 13 files changed, **not committed, not pushed** — I have no shell on your machine.

**I am not claiming "all bugs fixed."** Three findings (#15, #16, #19) are audited but deliberately unchanged, three hard stops are open, and `evaluation/results/` should be regenerated before this is defensible as research output.
