# Fix Report v2 — `rapidoproject` (A-DMFE)

**Date:** 15 August 2026
**Working tree:** `D:\rapidoproject` (files written in place, CRLF preserved)
**Patch applied:** `dmfe-dispatch-correctness` (`807b5de`) + 2 new files
**Not committed / not pushed** — see §8.

---

## 0. Environment — what was and was not runnable

This session had two execution surfaces and both were constrained:

| Surface | Status |
|---|---|
| Cloud sandbox (where I work) | **No package egress.** `pypi.org`, `files.pythonhosted.org`, `registry.npmjs.org` and `github.com` all return `403`. `fastapi`, `sqlalchemy`, `ortools`, `pytest`, `bcrypt`, `jose` cannot be installed. |
| Linux workspace on your machine | **Failed to start.** `device_bash` returns *"Workspace unavailable… The isolated Linux environment on this device failed to start."* on every call. No shell, therefore **no git and no pytest on your side either.** |

What that leaves: I can read and write files on your disk, and I can run
`python3`, `ruff` and `node` in the sandbox against source that needs no
third-party imports.

So the split is:

- **Verified here:** patch application, compile, ruff baseline, ES-module parse, 24 source assertions, 6 logic harnesses.
- **You must run:** anything needing `ortools`/`sqlalchemy`/`pytest`. Your `backend/.venv` already has them. `backend/scripts/verify_all.py` does all of it in one command.

Your gate was *"push only after the entire verification suite passes."* It has
not, here. I did not commit and did not push.

---

## 1. Bugs fixed

| ID | Sev | File | Bug |
|----|-----|------|-----|
| P0-1 | Critical | `dmfe/pipeline.py` | High-priority requests dropped from the run |
| P0-2 | Critical | `dmfe/pipeline.py` | `rollback()` discarded dispatch metadata of committed trips |
| P0-3 | Critical | `dmfe/optimizer.py` | Relaxed re-solve wrote `duration=0` and negative delays to `Trip` |
| P1-5 | High | `dmfe/driver_selection.py` | Stale cutoff force-completed running trips |
| P1-6a | High | `dmfe/decision_engine.py` | Adaptive context built from a different request set than analysed |
| — | Medium | `dmfe/pipeline.py` | Non-`ValueError` dispatch failure aborted the entire run |
| — | Medium | `dmfe/pipeline.py` | Adaptive-threshold failure silently swallowed |
| — | High | `core/middleware.py` | CSP blocked Swagger UI / ReDoc |
| — | Medium | `main.py` | Seed ran on a closed session, leaking a connection |
| — | Medium | `api/deps.py` | `db` possibly unbound in `finally` |
| — | High | `.env.example` | Documented setup made the backend unusable |
| — | Medium | `frontend/services/api.js` | Cache served pre-mutation state; unbounded; shared mutable payloads |
| — | Low | `README.md` | Setup and testing sections described things that don't exist |

**New in this pass:**

- `backend/tests/test_pipeline_accounting.py` — the accounting-invariant
  regression test, the one that would have caught P0-1 on day one. Four tests:
  mixed queue, Gate-D fall-through, no-driver control, repeated run. Counts
  **actual request ids**, so triples don't break it.
- `backend/scripts/verify_all.py` — one-command verification runner (§3).

**P1-4, P1-6b and the `SECRET_KEY`/admin-seed item are NOT applied** — §6.

---

## 2. Root causes

**P0-1 — one dictionary carrying two meanings.** `covered_ids` was written with
both `"shared"` and `"high_priority_reject"`, but the individual-dispatch loop
tested `req.id in covered_ids` — membership, not value. Gate-D rejects were
treated as "already handled": never dispatched, never appended to
`result.unassigned`. `requests_processed` counted them and nothing else did.
Because Gate D only fires on High-priority batches, the requests that vanished
were the most urgent ones.
*Fix:* `covered_ids.get(req.id) == "shared"`.

**P0-2 — a commit boundary in the wrong place.** `dispatch_trip(commit=True)`
commits inside `create_assignment` (`driver_selection.py:695`). `_record_dispatch()`
then mutates the batch *after* that commit, leaving the write dirty until the
final `db.commit()`. Any later `ValueError` triggers `db.rollback()`, discarding
every earlier pending mutation — including `details["predicted"]`, which
`_record_dispatch`'s own docstring says must stay recoverable for the Phase 4.1
learning engine to separate prediction from actual outcome. It clusters under
driver starvation, so the loss is systematic, not random.
*Fix:* `db.commit()` immediately after each `_record_dispatch`.

**P0-3 — a sentinel that reads as a real measurement.** The relaxed re-solve sets
`time_dim = None` (`optimizer.py:763`). `_build_route` then defaulted
`arr_sec = 0.0` for every stop. Delay is `arrival − pickup − direct_time`, so
all-zero arrivals yield **negative** delays and zero duration, persisted verbatim
onto `Trip`. Zero is not a missing-data marker here: it feeds KPIs and the
learning engine as a real outcome, and it disables Gate D, because a negative
delay never exceeds the limit.
*Fix:* reconstruct the arrival clock by accumulating `matrix_s` along the solved
visit order, mirroring the model's transit definition (travel on the arc,
service charged on departure from a pickup). **Post-processing of the solution
only — the OR-Tools model is untouched.**

**P1-5 — a wall-clock cutoff standing in for trip progress.** `complete_stale_trips`
filtered purely on `created_at < now − max_age_min`. Callers pass 10 minutes
while the optimizer plans 20–40 minute routes, so live trips were marked
`Completed` and their drivers freed for re-dispatch mid-trip.
*Fix:* `max_age_min` becomes a floor; a trip must **also** outlive its own
`total_duration_min` plus a grace margin. Naive SQLite timestamps normalised to
UTC to avoid a `TypeError` on the new Python-side comparison.

**P1-6a — two queries where one was meant.** Context profile came from
`id.asc() LIMIT 200`; analysis from `created_at.desc() LIMIT 200`. Above 200
pending these are disjoint, so the adaptive threshold was derived from requests
the run never looked at.
*Fix:* fetch `pending` first, build the context from it. The empty-queue
early-return still sees the context-adjusted threshold.

---

## 3. Verification results

### 3a. Ran here — actual output

**Patch application** (after normalising your CRLF working tree to LF for
`git apply`; the files written back to disk are CRLF again, round-trip verified
byte-identical on all 12):

```
Checking patch README.md...
Checking patch backend/.env.example...
Checking patch backend/app/api/deps.py...
Checking patch backend/app/core/middleware.py...
Checking patch backend/app/dmfe/decision_engine.py...
Checking patch backend/app/dmfe/driver_selection.py...
Checking patch backend/app/dmfe/optimizer.py...
Checking patch backend/app/dmfe/pipeline.py...
Checking patch backend/app/main.py...
Checking patch frontend/src/services/api.js...
                                        (10/10 clean, no fuzz, no rejects)
```

**Static checks, before → after the patch:**

```
compileall (app tests evaluation scripts)   BEFORE: OK      AFTER: OK
ruff check --select F,E9,B .                BEFORE: 52      AFTER: 52   (no new findings)
ES-module parse of api.js (node v22.22.2)   AFTER : parse OK
ruff on the two NEW files                   All checks passed!
import app.main                             BLOCKED — ModuleNotFoundError: No module named 'fastapi'
```

The 52 ruff findings are the pre-existing baseline; the patch and the two new
files add none.

**Source assertions — 24/24 PASS** (`assert_source_patches.py`, AST + literal,
tying each harness back to the real file on disk):

```
[PASS] P0-1 guard uses covered_ids.get(...) == 'shared'
[PASS] P0-1 old blanket guard removed
[PASS] P0-2 db.commit() immediately follows _record_dispatch in both loops   found 2/2
[PASS] P0-2b unexpected failures recorded as unassigned, run continues        found 2/2
[PASS] P0-3 _build_route accepts service_sec
[PASS] P0-3 running clock accumulates matrix_s along the route
[PASS] P0-3 arr_sec seeded from the clock, not 0.0
[PASS] P0-3 no bare 'arr_sec = 0.0' fallback remains
[PASS] P0-3 call site passes service_sec
[PASS] P1-5 grace_min parameter added
[PASS] P1-5 guard compares age against the trip's own planned duration
[PASS] P1-5 naive SQLite timestamps normalised to UTC
[PASS] P1-6a separate id.asc() preview query removed
[PASS] P1-6a context built from the same `pending` list
[PASS] CSP exempts the docs routes
[PASS] session lifecycle: seed runs before db.close()          seed@553 close@739
[PASS] get_db: SessionLocal() constructed outside the try
[PASS] .env.example: DATABASE_URL commented out
[PASS] .env.example: POSTGRES_* commented out
[PASS] frontend: mutations invalidate the GET cache
[PASS] frontend: noCache opt-out supported
[PASS] frontend: cached data cloned on store and on read
[PASS] frontend: cache size bounded
[PASS] HARD STOP: SetCumulVarSoftUpperBound left unmodified
```

**Behavioural harnesses — before/after** (stubbed reimplementations of the exact
patched logic; they demonstrate the defect and the fix, they are *not* the real
app running):

*P0-1 — requests lost:*
```
CURRENT     requests_processed=4 shared=1 individual=0 unassigned=0
            request ids actually dispatched: [3, 4]
            requests accounted for: 2/4  -> LOST: [1, 2]     <- id 1 is High-priority
WITH FIX    requests_processed=4 shared=1 individual=2 unassigned=0
            request ids actually dispatched: [1, 2, 3, 4]
            requests accounted for: 4/4  -> OK
```

*P0-2 — metadata lost:*
```
CURRENT   BATCH-A status='Dispatched'  reason_json='[]'                        survived: False
WITH FIX  BATCH-A status='Dispatched'  reason_json='["OK Dispatched: ..."]'    survived: True
```

*P0-3 — bogus trip metrics:*
```
normal solve (unchanged)        duration_min=  25.0  max_delay_min=  7.0   per-request=[5.0, 7.0]   ok
relaxed re-solve  BEFORE fix    duration_min=   0.0  max_delay_min= -9.0   per-request=[-10.0, -9.0]  FAIL
relaxed re-solve  AFTER  fix    duration_min=  29.0  max_delay_min=  9.0   per-request=[9.0, 9.0]     ok

Gate D before the fix:  -9.0 > 20.0 -> False   (the gate could never fire)
```

*P1-5 — running trips preserved:*
```
BEFORE fix: force-completed 5 trip(s)   (including 2 still within their planned duration)
AFTER  fix: force-completed 3 trip(s)   (only the genuinely stuck ones)
  assertions: running trips preserved OK | stuck trips released OK | naive SQLite timestamp OK (no TypeError)
```

*Frontend cache:*
```
stale-after-mutation  BEFORE   server.dispatched=1  ui.shows=0   FAIL: UI shows pre-dispatch state
stale-after-mutation  AFTER    server.dispatched=1  ui.shows=1   ok
shared-mutable-data   BEFORE   second_reader_sees=[1,2,3]        FAIL: cache poisoned by in-place sort
shared-mutable-data   AFTER    second_reader_sees=[3,1,2]        ok
```

### 3b. Could NOT run here — run these yourself

```bat
cd D:\rapidoproject\backend
.venv\Scripts\activate
python scripts\verify_all.py
```

That one command covers everything that was blocked, and writes a transcript to
`backend\VERIFY_RESULTS.md`. It runs against a throwaway SQLite database in a
temp directory — **your `dmfe_dev.db` is not touched.**

| Section | What it runs |
|---|---|
| A. static | `compileall`, `import app.main`, `ruff --select F,E9,B`, `pytest tests/` |
| B. scenarios | the six DMFE scenarios, real OR-Tools + real SQLAlchemy |
| C. probes | the P1-4 OR-Tools probe and the CSP/Swagger check (report only) |
| D. history | scans for `"no solution with time dimension"` in logs |

Scenario coverage, mapped to your list:

1. **normal run** — mixed queue; asserts `dispatched ∪ unassigned == processed` by request id
   *plus* **1b** — Gate-D specific: `max_allowed_delay_min` driven to 0.01 with a High-priority pair, asserting those ids leave a trace (direct P0-1 reproduction against the real engine)
2. **minimal feasible** — 2 compatible requests, 1 driver
3. **no-driver control** — asserts every request lands in `unassigned` *with a reason*
4. **stale-trip** — dispatches, backdates to 12 min old with a 35 min plan, asserts still `Active`; **4b** control: 90 min old / 20 min plan is still released
5. **relaxed-route** — forces the fallback by making the *first* `SolveWithParameters` call return `None` (exactly what an infeasible time model does; the OR-Tools model, objective and search parameters are not modified), then asserts `total_duration_min > 0`, `max_delay_min >= 0`, arrivals non-decreasing; **5b** control: the normal path still produces sane metrics and does *not* take the relaxed branch
6. **repeated run** — second run dispatches nothing new and does not reopen completed trips

Frontend `npm run lint` / `npm run build` also could not run (npm blocked, 403).
Run them locally:

```bat
cd D:\rapidoproject\frontend
npm install
npm run lint
npm run build
```

---

## 4. Research logic confirmed untouched

Verified by `git diff --stat` returning empty for each:

- `dmfe/scoring.py`, `dmfe/score_engine.py`, `dmfe/compatibility.py` — **untouched**
- `dmfe/adaptive/` — all of weights, learning, context, decision, matrix, batching, factors, xai — **untouched**
- `db/models.py` — **untouched** (no schema, no drivers↔vehicles FK change)
- `core/security.py`, `api/routes/auth.py` — **untouched**
- CORS block in `main.py` — **untouched**

Grep across the full diff for `unified_scoring`, `SetArcCost`, `AddDimension`,
`AddPickupAndDelivery`, `SetGlobalSpan`, `SetCumulVar`, `allow_origins`,
`CORSMiddleware`: **no matches.**

The only change inside `optimizer.py` is in `_build_route`, which reads a
solution that already exists, plus one new keyword argument at the call site.
The objective callback, capacity/distance/time dimensions, pickup-and-delivery
constraints and search parameters are byte-identical.

**Behavioural note — read this before regenerating any results.** P0-3 changes
recorded values for trips that took the relaxed path: previously `duration=0`
and a negative delay, now real numbers. That is the point of the fix, but any
figure in `backend/evaluation/results/` produced from a run containing
relaxed-path trips is now inconsistent with the code. Section D of
`verify_all.py` greps for `"no solution with time dimension"`; note that absence
of log files is not proof the path was never taken. If in doubt, regenerate.

---

## 5. Remaining issues

1. **`/analyze` vs `/dispatch` ordering split** — `decision_engine` reads
   `created_at.desc()`, `pipeline` reads `created_at.asc()`. Above 200 pending
   they act on different requests. Deliberately not fixed — §6.
2. **`context_profile_dict`** — still assigned and unused in `decision_engine`
   (ruff `F841`). Looks intended for the XAI payload; surfacing it changes the
   API response shape.
3. **Dev `SECRET_KEY` fallback + auto-seeded `admin@aiorch.com` / `admin123`** —
   untouched by your instruction. Highest-value remaining item before a viva,
   given the README's "Security Hardening Report" and "98/100 Production Ready".
4. **Redundant adaptive context build in `pipeline.run`** — computed, used only
   in the log line; `create_feasible_batches` recomputes it. One extra context
   build and query per run.
5. **Frontend has no tests** — README now says so instead of claiming
   Vitest/Playwright suites.
6. **Dead modules** — `app/engine/explainability.py`, `app/core/coimbatore.py`
   unreachable from `app.main`; `slowapi` in `requirements.txt`, never imported.
7. **52 ruff findings** (25 unused imports, 4 unused locals, 4 missing
   `raise … from`) — left per your instruction not to clean cosmetics before
   correctness lands. `ruff check --fix` clears 32.
8. **`sync_schema_columns` skips callable defaults** — a future column with a
   `datetime.utcnow` default lands `NULL` on existing rows.
9. **16 `except Exception: pass` blocks** — `dmfe/adaptive/learning.py`,
   `dmfe/adaptive/context.py`, `services/simulation_service.py`,
   `dmfe/compatibility.py`. Two of them (in `pipeline.run`) are now logged; the
   rest are not. In a system whose output is research metrics, an engine that
   half-fails and returns plausible numbers is worse than one that crashes.

---

## 6. Hard stops

### HARD STOP — `SetCumulVarSoftUpperBound` argument (P1-4)

`backend/app/dmfe/optimizer.py:739-743` — **left unmodified**, verified by source
assertion.

```python
t_dim.SetCumulVarSoftUpperBound(
    t_dim.CumulVar(d_idx),      # API expects a routing index, not the variable
    direct_sec + max_delay_sec,
    per_sec,
)
```

Google documents the signature as
`void SetCumulVarSoftUpperBound(int64_t index, int64_t upper_bound, int64_t coefficient)`.
The one-token fix is `d_idx`.

You asked me to run the probe first and report the actual exception. **I could
not — `ortools` is not installable here.** So the probe is built into
`verify_all.py` §C1: it sets `vrp_delay_penalty_per_min = 5.0`, dispatches one
shared trip, and reports the exception type and message (or that it succeeds),
**without changing any code**. Run it, paste me the output, and I'll apply the
`d_idx` fix and re-verify that dispatch succeeds with the penalty active.

It is dormant today — `vrp_delay_penalty_per_min` defaults to `0.0`, so the
branch never executes and nothing is currently broken. The risk is that raising
that config above zero would make every shared-trip optimization throw, and
`dispatch_trip` only documents `ValueError`, so a `TypeError` would escape the
pipeline's handlers. That last part is now mitigated regardless: the pipeline's
new `except Exception` records the batch as unassigned instead of 500-ing the
whole run.

### HARD STOP — `/analyze` vs `/dispatch` request ordering (P1-6b)

`/analyze` reads `created_at.desc()`, `/dispatch` reads `created_at.asc()`, so
above 200 pending the XAI dashboard explains decisions about requests the
pipeline will never touch.

Aligning them is not a safe edit: `generate_candidates` sorts candidates by
`(-score, i, j)` where `i, j` are indices into `pending`, so changing the queue
order changes greedy tie-breaking among equal-score pairs — which can shift
recorded experimental results even when the request *set* is identical.

**Recommendation:** move the analyzer to `asc()`, so `/analyze` explains what
`/dispatch` will actually do. But treat it as a deliberate re-baseline of your
experiments, not a silent edit — regenerate `evaluation/results/` afterwards.

### Deferred by your instruction — `SECRET_KEY` + default admin

`core/config.py:23` falls back to a key that is public in this repository, so
anyone can forge an admin JWT; `main.py` unconditionally seeds
`admin@aiorch.com` / `admin123`. The change would be: fail fast when
`SECRET_KEY` is unset outside development, and gate the seed behind an explicit
env flag with the password read from the environment. Left alone — it touches
authentication bootstrapping and changes startup behaviour.

---

## 7. Files changed on your disk

Written in place at `D:\rapidoproject`, original CRLF line endings preserved
(round-trip verified byte-identical for all 12):

```
README.md
backend/.env.example
backend/app/api/deps.py
backend/app/core/middleware.py
backend/app/dmfe/decision_engine.py
backend/app/dmfe/driver_selection.py
backend/app/dmfe/optimizer.py
backend/app/dmfe/pipeline.py
backend/app/main.py
backend/scripts/verify_all.py              (new)
backend/tests/test_pipeline_accounting.py  (new)
frontend/src/services/api.js
```

`1153 insertions(+), 60 deletions(-)`

Nothing else was touched. No `.env`, secrets, `.db`, `.log`, `__pycache__`,
`.pyc`, `node_modules` or temp files were written.

---

## 8. Commit and push

**Neither done.** `device_bash` is unavailable, so I have no shell on your
machine and cannot run `git` there. The sandbox git proxy also refuses your
remote (`Sivamah/finalyr-project is not in this session's authorized repository
set`), so even a sandbox-side push was never possible.

Run the suite first, then commit:

```bat
cd D:\rapidoproject
git checkout -b fix/dmfe-dispatch-correctness
git status
git diff

cd backend
.venv\Scripts\activate
python scripts\verify_all.py

REM only if it reports 0 failures:
cd ..
git add README.md backend/.env.example backend/app backend/tests/test_pipeline_accounting.py backend/scripts/verify_all.py frontend/src/services/api.js
git commit -F commit_message.txt
git push -u origin fix/dmfe-dispatch-correctness
```

Suggested commit message (root causes, not symptoms) — save as
`commit_message.txt`:

```
fix(dmfe): stop dispatch pipeline losing requests and writing bogus trip metrics

P0-1 High-priority requests were dropped from the run.
  Gate D marked them "high_priority_reject" in covered_ids, and the
  individual-dispatch loop skipped anything PRESENT in covered_ids rather
  than anything actually placed in a shared trip. They were never
  dispatched and never recorded in result.unassigned, despite the module
  contract stating a request is never skipped silently. Guard now tests
  the value.

P0-2 db.rollback() discarded dispatch metadata of committed trips.
  dispatch_trip() commits the Trip, then _record_dispatch() wrote the
  reason line and details["predicted"] snapshot as a dirty mutation that
  only landed at the final commit. Any later ValueError rolled back every
  earlier snapshot -- the same snapshot the Phase 4.1 learning engine
  needs to separate prediction from actual outcome. Now committed with
  the trip it describes.

P0-3 Relaxed OR-Tools re-solve wrote duration=0 and negative delays.
  When _solve_pdp falls back without the time dimension, time_dim is None
  and every arrival defaulted to 0.0, yielding total_duration_min = 0,
  eta_min = 0 and negative max_delay_min persisted onto the Trip row --
  which also disabled Gate D for those trips, since a negative delay
  never exceeds the limit. _build_route now reconstructs the arrival
  clock from the solved visit order, mirroring the model's transit
  definition. The OR-Tools objective, constraints and search parameters
  are unchanged.

P1-5 Stale-trip cutoff force-completed running trips.
  Callers pass max_age_min=10 while the optimizer plans 20-40 min routes,
  so live trips were marked Completed and their drivers freed for
  re-dispatch mid-trip. max_age_min is now a floor; a trip must also
  outlive its own planned duration plus a grace margin. Naive SQLite
  timestamps are normalised to UTC.

P1-6a Adaptive context was built from a different request set than the one
  analysed (id.asc() preview vs created_at.desc() analysis), so above 200
  pending the effective threshold came from disjoint requests.

Adds tests/test_pipeline_accounting.py: every processed request must be
dispatched or reported unassigned, counted by request id. This is the
regression guard for P0-1.

Adds scripts/verify_all.py: one-command verification of the static checks,
the six DMFE runtime scenarios, and the two report-only probes.

Also, without changing engine behaviour: unexpected (non-ValueError)
dispatch failures are recorded as unassigned instead of aborting the run;
adaptive-threshold failure is logged; CSP no longer blocks Swagger UI;
the driver/vehicle seed runs before the session is closed; get_db
constructs its session outside the try; .env.example defaults to SQLite;
the frontend GET cache is invalidated on mutation, cloned and bounded;
README setup and testing sections corrected.

Not changed (require review): OR-Tools SetCumulVarSoftUpperBound is passed
a CumulVar where the API expects a routing index; the /analyze vs
/dispatch created_at ordering split; the SECRET_KEY fallback and the
unconditional admin seed.
```

---

## What I need back from you

1. `backend\VERIFY_RESULTS.md` after running `verify_all.py` — particularly
   §C1, the P1-4 probe output.
2. Whether §D found `"no solution with time dimension"` in any log, which
   decides whether `evaluation/results/` needs regenerating.

With the probe output I can finish P1-4 properly instead of guessing.
