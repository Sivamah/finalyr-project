# A-DMFE — Feasibility Engine, Demo Mode & Orchestration Engine

Status of the three features, what was wrong, what changed, and how to verify.
Written to be usable as a prompt/brief for a follow-up agent as well as a record.

---

## Scope and hard stops

**In scope:** Demo Mode plumbing, the Orchestration Engine page, and the
request-queue contention between two optimizers.

**Hard stops — not touched, and not to be touched without separate evidence:**

- compatibility scoring formulas (`app/dmfe/compatibility.py`, `scoring.py`, `score_engine.py`)
- the adaptive threshold formula (`app/dmfe/adaptive/decision.py`)
- `driver_scarcity` sign and weighting
- the adaptive learning update rule (`app/dmfe/adaptive/learning.py`)
- Gate-D semantics (`app/dmfe/decision_engine.py`)
- the OR-Tools objective and constraints (`app/dmfe/optimizer.py`)
- DB schema, auth, CORS, `unified_scoring_enabled`

No change below alters a research number. All of it is plumbing: which endpoint
the UI calls, which table a route reads, and whether demo data exists at all.

---

## Finding 1 — Demo Mode could never populate (P0)

**Evidence.** Demo Mode filters on a marker in `pickup_address`:

```
app/api/routes/dmfe_v2.py:68     .like("[A-DMFE Demo Scenario]%")
app/api/routes/simulation.py:175 .like("[A-DMFE Demo Scenario]%")
```

Grepping the whole tree for that marker returns exactly one producer:
`backend/scripts/verify_demo.py` — a standalone script with no API route and no
UI affordance. Nothing in the running application ever writes a row carrying the
tag.

**Consequence.** Toggling Demo Mode On filtered both the Pending Queue and the
Candidate Batches down to a set that is empty by construction. The feature was
inert, not broken-looking — which is worse, because it reads as "no data yet".

**Secondary defect.** `verify_demo.py` places its requests at `(12.97, 77.59)` —
Bangalore. `app/core/coimbatore.py` bounds the service area to
lat `10.95–11.15`, lng `76.85–77.05`. Even if that script were run, the demo
requests would sit outside the map viewport and outside location validation.

**Change.**

- `POST /api/dmfe/demo/seed` — inserts a curated, fully deterministic six-request
  scenario, all inside the Coimbatore bounds. Idempotent: clears still-Pending
  demo rows first, so repeated clicks re-seed rather than accumulate.
- `DELETE /api/dmfe/demo/clear` — removes only still-Pending demo requests.
  Rows already consumed by a run are left intact, since deleting them would
  orphan the batch and trip rows referencing them and would retroactively alter
  recorded statistics.
- `DEMO_TAG` is now a named constant in `dmfe_v2.py` with a comment noting the
  three places it must stay in sync.
- The Demo Mode banner in `DMFEDashboard.jsx` gained **Seed demo scenario** and
  **Clear** buttons plus a live count, so the toggle is self-sufficient.

**Scenario design.** Deterministic — no randomness, so every demo run produces
the same decisions and the walkthrough is reproducible:

| # | Type | Pickup | Drop | Expected outcome |
|---|---|---|---|---|
| 1 | ride | Gandhipuram Bus Stand | Peelamedu | batches with 2 |
| 2 | ride | Gandhipuram Signal | Peelamedu Tech Park | batches with 1 |
| 3 | food | Race Course | R.S. Puram | batches with 4 |
| 4 | food | Race Course Road | R.S. Puram West | batches with 3 |
| 5 | parcel | Singanallur | Ondipudur | solo trip |
| 6 | ride | Kalapatti | Saravanampatti | solo trip |

Two compatible pairs and two solo trips — so the demo shows both a successful
batching decision and the solo-trip path in one run.

The seeded rows are ordinary `SimulationRequest` records. The engine scores them
through exactly the same code path as live traffic; nothing about the demo is
scripted or pre-decided.

---

## Finding 2 — The Orchestration Engine drained the A-DMFE queue (P0)

**Evidence.** `POST /api/orchestration/optimize` ran `AIOrchestrator`
(`app/engine/optimizer.py`) — a second optimizer entirely independent of
`app/dmfe/`. It selected every pending request:

```
app/engine/optimizer.py:19   .filter(SimulationRequest.status == "Pending")
```

and then marked them:

```
app/engine/optimizer.py:248  .update({"status": "Optimized"}, ...)
```

Grepping for `"Optimized"` across `backend/app/` returns **one hit — that write.**
Nothing reads it. The A-DMFE pipeline filters on `status == "Pending"`.

**Consequence.** Every click of "Run Optimization" permanently removed the entire
A-DMFE pending queue into a terminal status no component surfaces. The requests
vanished from the queue, never appeared in history, and were invisible to the
Feasibility Engine. This is a research-integrity hazard, not merely a UI bug:
whichever page you clicked last determined which engine got the data.

**Second, independent defect in the same feature.** The page wrote one table and
read another:

- `POST /optimize` wrote `OptimizationResult` rows and returned them
- `GET /results` read `Trip` rows (A-DMFE output) with `chosen_provider` hardcoded
  to the string `"DMFE"`
- `GET /results/{id}` queried `OptimizationResult` **by the id `GET /results`
  had returned from `Trip`** — so opening any row looked an id up in an
  unrelated table

Net effect in the UI: click Run, see one entity type; click Refresh, the table
silently swaps to a different dataset.

**Change — one engine.**

- `POST /api/orchestration/optimize` now returns **HTTP 410 Gone** with a message
  pointing at `POST /api/dmfe/analyze`. The `AIOrchestrator` class is left in the
  tree unmodified for reference; it simply has no caller.
- `AIDashboard.jsx` "Run Optimization" now calls `POST /api/dmfe/analyze` — the
  same engine the Feasibility Engine page drives — then re-reads results. It
  seeds synthetic demand via `/orchestration/simulate` **only when the queue is
  empty**, so a click can never inflate an in-progress simulation.
- `GET /results` and `GET /results/{id}` now share one serializer
  (`_trip_to_result`) over the `Trip` table, so list and detail agree.
- `chosen_provider` reports the driver's real provider, falling back to `"A-DMFE"`
  only when the driver or provider is unknown.
- The page description now states what it is: the **routing view** of the one
  engine, with scoring decisions shown on the Feasibility Engine page.

---

## The demo narrative this enables

Two pages, one engine, three minutes:

1. **Feasibility Engine** → Demo Mode On → **Seed demo scenario** → six requests
   appear in the Pending Queue.
2. **Run Analysis** → two compatible batches created, two solo trips, rejected
   pairs counted. Expand a batch → the 8-factor breakdown and the decision
   reasons for that specific pairing.
3. **Orchestration Engine** → the trips those batches produced, with the route,
   the assigned vehicle, distance saved and CO2 saved.

That is the "most important workflow" to lead with: scoring decision → routed
outcome, on data the audience watched you create.

---

## Verification

Nothing below was executed in the environment these edits were authored in.
Run it before relying on any of it.

**Static:**

```
cd backend
python -m compileall app/api/routes/dmfe_v2.py app/api/routes/orchestration.py
ruff check app/ --select F,E9,B
cd ../frontend && npm run lint && npm run build
```

**Behavioural — Demo Mode:**

1. Start the API and the frontend. Log in.
2. Feasibility Engine → Demo Mode **On** → banner shows "No demo requests yet".
3. Click **Seed demo scenario** → toast reports 6 created; Pending Queue shows 6,
   all with `[A-DMFE Demo Scenario]` pickups, all rendering inside Coimbatore.
4. Click **Seed demo scenario** again → still 6, not 12 (idempotency).
5. Click **Run Analysis** → expect 2 compatible batches + 2 solo trips.
6. Click **Clear** → pending demo rows go, already-processed ones are reported as
   kept.

**Behavioural — one engine:**

7. `curl -X POST .../api/orchestration/optimize` with a valid token → **410**,
   message pointing at `/api/dmfe/analyze`.
8. Note the pending-queue count. Orchestration Engine → **Run Optimization** →
   results populate, and the Feasibility Engine queue reflects a normal A-DMFE
   run rather than being emptied into nothing.
9. `GET /api/orchestration/results` then `GET /api/orchestration/results/{id}`
   using an id from that list → the detail matches the list row.

**Regression:** confirm no request ends the session with `status = "Optimized"`:

```sql
SELECT COUNT(*) FROM simulation_requests WHERE status = 'Optimized';
```

Pre-existing rows from earlier runs will still be there — they were stranded by
the old endpoint. Decide deliberately whether to reset them to `Pending` before
a demo or a results regeneration; that is a data decision, not a code one.

---

## Still open, unrelated to this change

- `backend/evaluation/results/` predates the R3/R4 and P0-3 corrections. The
  published tables must be regenerated before any number is quoted.
- `decision_total_s` and `learning_total_s` report `0.00` on every workload —
  timer instrumentation, flagged and not fixed.
