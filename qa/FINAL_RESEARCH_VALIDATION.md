# A-DMFE — Final Research Validation

**Role:** research validator / integration reviewer · **Date:** 15 August 2026
**Method:** every finding below is derived from the bytes currently on disk and from `qa/server_err.log`, a real backend run. Nothing is taken from the DeepSeek report on trust.

---

## 0. Scope of what I could execute

| | |
|---|---|
| Static review, diff audit, formula analysis, log forensics | **Done** |
| Live E2E (§6 of your brief) | **NOT PERFORMED.** `list_connected_browsers` → `[]`, so there is no browser automation. `device_bash` (shell on your machine) has failed on every call this session, and this sandbox cannot reach your localhost or install `ortools`/`pytest`. |

I did not run `verify_all.py`, `pytest`, `e2e_test.py`, `npm run lint` or `npm run build`. Where I cite runtime behaviour it comes from `qa/server_err.log` — a real 485-line backend session — or from your own earlier `VERIFY_RESULTS.md`.

**One correction to the premise.** `docs/A-DMFE_MANUAL_LIVE_QA_REPORT.md` is not a report of fixes applied. Its §21 is a *handoff list* ("MUST FIX / SHOULD FIX / DO NOT TOUCH"). DeepSeek did make 16 file edits, but they are engineering-only — none of the two MUST FIX items were implemented. Good, because the first one should never be implemented (R1).

---

## 1. Findings

| ID | Severity | Area | Evidence | Decision | Research Impact | Status |
|---|---|---|---|---|---|---|
| **R1** | **Critical (refuted)** | Adaptive threshold | `qa/server_err.log`: θ_eff took only **70.0 / 70.1 / 70.2 / 73.0** against base 70. 128 accepted vs 88 rejected. Every rejected score 41.3–61.3. | **DO NOT APPLY** the "threshold starvation" MUST FIX | Applying it would have altered the core A-DMFE contribution and invalidated every experiment | Refuted, no change |
| **R2** | Medium | `driver_scarcity` direction | `adaptive/decision.py:55` — `+3.0·driver_scarcity` raises θ_eff, while `−4.0·demand_pressure` lowers it | Design question, not a defect | None if justified; must be defensible in viva | Documented, no change |
| **R3** | **High** | Evaluation metrics | `framework.py:550` `avg_waiting_min` and `:527` `avg_delay_min` are the **same expression**. `ieee_tables.md` L45–48 and L86–89 are numerically identical row-for-row | Correct the tables/paper | Duplicate metric presented as two results **in the submitted paper** | Open — needs your action |
| **R4** | **High** | Evaluation metrics | `framework.py:523` `completed = sum(1 for s in status_map.values() if s == "Assigned")` | Relabel | "Waves completion 100.00%" is a **dispatch** rate, not a completion rate | Open — needs your action |
| **R5** | Medium | Simulation clock | Old: `created_at − request_timestamp` mixed wall-clock with simulated time. New: `Trip.completed_at − created_at`, wall-clock consistent | Accept the fix | **A — technically correct, not research-correct.** No impact on published results (see §3) | Fixed by DeepSeek |
| **R6** | Low | Completion semantics | DeepSeek changed live dashboard to `status == "Completed"`; `framework.py` still counts `"Assigned"` | Document the divergence | Live dashboard and paper now use different definitions of "completed" | Open |
| **R7** | Low | Simulation anchor | `mock_adapters.py` `base_time` moved from `utcnow() − 0..5 min` to `− 50..60 min` | Verified safe | Single RNG draw, constant offset → pairwise time deltas identical → every time-window gate decision preserved | Verified |
| **R8** | Medium | Run attribution | `decision_engine.py` blanket `analysis_run_id IS NULL` back-fill replaced with an explicit id list | Genuine correctness win | Pipeline-created batches are no longer misattributed to an analysis run. Aggregate run stats unaffected (counted in-loop) | Fixed by DeepSeek |
| **R9** | Low | Lint | ruff `F,E9,B` 52 → **54**; both new findings are `B904` in `orchestration.py:47,52` | Cosmetic | None | Open, non-blocking |

---

## 2. R1 — the adaptive threshold claim, refuted

DeepSeek's §20 calls this **CRITICAL** and its §21 MUST FIX says *"Adjust the threshold scaling logic… It is starving the batching system by raising θ_eff excessively."* That would mean editing `adaptive/decision.py` — a hard stop, and the heart of your contribution. It is not warranted.

### The formula cannot inflate

`backend/app/dmfe/adaptive/decision.py:51-57`

```python
θ_eff = clamp(base + 2.0·traffic_index − 4.0·demand_pressure + 3.0·driver_scarcity, 55.0, 85.0)
```

All three inputs are normalised to `[0, 1]` (`_clamp01` in `context.py`). So for `base = 70`:

```
maximum possible rise   = +2.0 + 3.0 = +5.0   →  θ_eff ≤ 75.0
maximum possible fall   = −4.0               →  θ_eff ≥ 66.0
```

It is a **pure function of the current context**. There is no accumulator, no integral term, no feedback of θ_eff into its own inputs. "Artificially inflated over time" is not a behaviour this function can exhibit.

### The real run contradicts the claim

From `qa/server_err.log`, every threshold that actually fired:

```
     83  >= 70.1        43  < 70.1
     30  >= 70.2        14  < 70.2
     15  >= 70.0         7  < 70.0
                         7  < 73.0
```

θ_eff never left `[70.0, 73.0]` — a maximum excursion of **+3.0** from base, and mostly **+0.1**.

```
accepted: 128
rejected:  88          →  59% acceptance, not "near 100% rejection"
```

Every rejected score, deduplicated:

```
41.3  41.4  41.6  41.7  43.9  44.1  53.3  53.5  55.6  56.6
56.9  57.0  57.7  58.4  58.5  59.9  61.3
```

The closest rejection is **61.3 against 73.0** — 11.7 points short. There is not one borderline case in the entire log. These pairs are genuinely incompatible, and the compatibility engine is correctly saying so.

### The cited example disproves itself

DeepSeek: *"Pairs with 69.5% compatibility were rejected because the threshold θ_eff was 69.9%."*

`min_compatibility_score` is **70.0**. A θ_eff of 69.9 is **0.1 below base** — at that instant the adaptive layer was making batching *easier*, not harder. A 69.5 pair failing a ~70 threshold is the system working exactly as designed. (That line does not appear in the log I have, so I cannot confirm it was ever observed.)

### What actually starves the engine

The single largest rejection reason in the log:

```
16 × rejected: No driver is currently Available (all busy)
```

That is **Gate E fleet starvation** — 15 drivers against a queue of hundreds — not the threshold. The correct response is a larger fleet or a smaller workload, not a weaker decision rule.

**Verdict: NO CHANGE to `adaptive/decision.py`. The MUST FIX is based on a misdiagnosis and would have damaged the research.**

---

## 3. Simulation clock analysis (your §3 — the decisive question)

### The two clocks

| Field | Meaning |
|---|---|
| `SimulationRequest.request_timestamp` | **simulated** arrival time (e.g. 08:50 scenario time) |
| `SimulationRequest.created_at` | **wall-clock** DB insert time |
| `Trip.completed_at` | **wall-clock** completion time |

**Before:** `processing_time = created_at − request_timestamp` — wall-clock minus simulated time. Dimensionally meaningless; that is the 30 773 s (8.5 h) artefact.

**After:** `processing_time = Trip.completed_at − created_at` — wall-clock minus wall-clock, via the new `completed_at_map()` helper.

### Verdict: **A — technically correct, not research-correct**

- **Technically correct.** It removes a genuine unit error and is now internally consistent. Accept it.
- **Not research-correct.** The quantity it now measures is *how long a row sat in the database before a human clicked "Run A-DMFE"*, plus whatever `complete_stale_trips` did. It is an operational property of your demo session, not a mobility-domain waiting time. It will change if you take a coffee break mid-run.
- A research-grade waiting time would need a **simulated** completion clock. The schema has no such column. Adding one is a schema change → **HARD STOP — REQUIRES REVIEW**. My recommendation is not to add it: you do not need it (see below).

### Why it does not matter for the paper

`backend/evaluation/framework.py` contains **zero references** to `simulation_service`, `simulation_engine`, `get_analytics`, `count_completed` or `completed_at_map`. Verified by grep. It computes every published metric itself:

| Published metric | Source in `framework.py` |
|---|---|
| `avg_delay_min`, `avg_waiting_min` | `mean(trip.max_delay_min)` — the OR-Tools model quantity |
| `avg_processing_ms` | `time.perf_counter()` around the engine call |
| `batching_rate_pct` | `len(shared) / len(trips)` |
| `completion_rate_pct` | its own `wave_completed` counter |

**Therefore: none of the clock changes touch a single number in `evaluation/results/`.** The broken metric lived only on the live dashboard, which is not an experimental surface.

**Pre-fix and post-fix results are comparable with respect to the clock fix.** They are not comparable with respect to P0-3 (see §7).

---

## 4. XAI validation

`xai.py` and `xai_service.py` changed; the explanation *logic* did not.

- `xai.py:44` — `get_explanations(db, search=str(request_id), limit=10)` → `get_explanations(db, request_id=request_id)`. **Real correctness fix.** The old substring search meant `/xai/1` could match requests 1, 10, 100, 1000… and then only find the right one if it fell inside the newest 10. Explanation-to-request mapping is now exact.
- `status="Evaluated"` previously filtered the raw status column for the literal string `"Evaluated"`, which no row ever has → the filter silently returned nothing. Now mapped to `status != "pending"`. **Real fix.**
- Post-filtered `search`/`decision` no longer have the SQL `LIMIT` applied first, so matches beyond the newest N are now reachable. **Real fix.**
- `_trip_metrics` request→trip lookup replaced a per-explanation `LIKE` query with a prefetched dict. Note the old query had `LIKE '%"{id}"%' OR LIKE '%{id}%'` — the second clause matched **any substring**, so request 12 could bind to a trip serving request 123. The new dict is keyed on parsed JSON ids. **Real correctness fix, not just a performance one.**

The threshold used in the explanation is still `_get_threshold(db)` adjusted by `effective_threshold(...)` — same value the decision used. **XAI explanation and A-DMFE decision remain consistent.** DeepSeek's own assessment ("Excellent, no text contradictions") matches what the code does, and its "DO NOT TOUCH — XAI explanation logic" was correctly respected.

---

## 5. Analytics validation

| Metric | Changed? | Effect |
|---|---|---|
| Waiting / processing / completion time | Yes | Dashboard only. See §3 — accept |
| Completion count | Yes — `status != "Pending"` → `== "Completed"` | Dashboard completed count will **drop**; in-flight `Assigned` requests now correctly stay in the pending bucket. More honest |
| RPM | Not in the diff | DeepSeek's B2 was **not fixed** |
| Utilization, batching rate, delay, fuel, CO₂ | No | Untouched — all derive from `Trip` rows |
| `active_drivers` / `active_vehicles` / `total_batches` | Added | B3/B4 fixed |

⚠️ On the new dashboard counters: DeepSeek defined **active = `status in ("available", "busy")`**, i.e. "not offline". So an entirely idle fleet will read as 100% active. If the demo narrative is "look, 15 drivers are actively working", that counter does not say that. Consider `busy` alone, or label it "Fleet online". Not a bug — a definitional choice you should be able to explain.

---

## 6. Research-sensitive review — what DeepSeek did and did not touch

Confirmed **UNCHANGED** by empty diff against my handoff:

```
scoring.py   score_engine.py   adaptive/decision.py   adaptive/weights.py
adaptive/learning.py   adaptive/context.py   adaptive/factors.py
adaptive/batching.py   adaptive/matrix.py
db/models.py   core/security.py   api/routes/auth.py
```

`compatibility.py` **was** touched — the only change is two `pass` statements replaced by log calls. No formula, no weight, no threshold. `driver_selection.py` — one `exc_info=True`. `optimizer.py` — untouched since my P1-4 fix; the OR-Tools objective, dimensions, pickup-and-delivery constraints and search parameters are intact.

**DeepSeek did not silently change any research behaviour.** All 16 edits are N+1 elimination, `joinedload`, filter correctness, exception logging, and the timestamp consistency work.

`compileall` passes on the current tree. Ruff `F,E9,B` went 52 → 54 (two `B904` in `orchestration.py`).

---

## 7. Evaluation results — KEEP or REGENERATE

| Change | Verdict | Reason |
|---|---|---|
| Simulation clock (R5) | **KEEP** | `framework.py` never used those code paths |
| Completion semantics (R6) | **KEEP** | `framework.py` has its own counter |
| `base_time` anchor (R7) | **KEEP** | Constant offset, identical pairwise deltas, same RNG consumption |
| P1-4 delay penalty | **KEEP** | `vrp_delay_penalty_per_min` absent from every recorded config → default 0.0. Pre-fix code would have thrown `TypeError` at any non-zero value, so no experiment ever exercised it |
| P0-1 dropped requests | **KEEP with caution** | Affects dispatch counts only under Gate-D rejection; `framework.py` drives the engine directly |
| **P0-3 relaxed route** | **REGENERATE** | `avg_delay_min`, `avg_waiting_min`, `avg_travel_time_min` are means of `trip.max_delay_min` / `total_duration_min` — exactly the fields P0-3 corrected |
| **R3 duplicate metric** | **CORRECT THE TABLES** | Not a regeneration issue — a labelling issue |
| **R4 completion rate** | **CORRECT THE TABLES** | Same |

New evidence on P0-3: `qa/server_err.log` contains **0** occurrences of `"no solution with time dimension"`. That is the first real runtime evidence the relaxed path was not taken — but it is one session, not the original experiment runs. I would still regenerate.

---

## 8. R3 and R4 — the two findings that matter most for your viva

Both are **pre-existing**, nothing to do with DeepSeek, and both are **in the paper**.

### R3 · "Average waiting time" and "average delay" are the same number

`backend/evaluation/framework.py`

```python
527:  avg_delay_min = avg([t.max_delay_min or 0 for t in trips])
...
550:  "avg_waiting_min": avg([t.max_delay_min or 0 for t in trips]),
551:  "avg_delay_min":   avg_delay_min,
```

Identical expression. `evaluation/results/ieee_tables.md` prints them as two separate tables with identical values:

```
L45-48  | Avg waiting (min) | 50 | 4.41 | 4.53 | +2.7% |  ... 5.44/5.41 ... 4.72/4.47 ... 4.34/4.48
L86-89  | Avg delay   (min) | 50 | 4.41 | 4.53 | +2.7% |  ... 5.44/5.41 ... 4.72/4.47 ... 4.34/4.48
```

`docs/04_IEEE_Paper_Draft.md:46` carries the same deltas as a distinct "Avg waiting Δ" result.

An examiner comparing those two tables sees it immediately. Note the paper already says at line 63 that *"a previously duplicated metric was removed because it double-counted processing time"* — this is a second duplicate that survived.

**Fix:** either drop the waiting-time row, or define waiting genuinely (e.g. driver ETA at dispatch + queue time) and recompute. Do not simply rename it.

### R4 · "Completion rate" is a dispatch rate

```python
523:  completed = sum(1 for s in status_map.values() if s == "Assigned")
498:  "completion_rate_pct": round(wave_completed / len(requests) * 100.0, 1),
```

It counts requests that reached **Assigned** — dispatched — not requests that finished. That is why `ieee_tables.md` L74-77 reads `Waves completion (%) 100.00` for every workload and both modes: within a wave, every request that gets a driver is counted, and the harness dispatches everything it can.

**Fix:** relabel to "dispatch rate (%)", or count `status == "Completed"` and regenerate. Relabelling is honest and costs nothing; recounting changes a headline number.

Note the irony: DeepSeek made the *live dashboard* strict (`== "Completed"`) while the *evaluation harness* still counts `"Assigned"`. The two surfaces now disagree by design — R6.

---

## 9. High compatibility vs zero batches (your §2)

Yes, it can legitimately happen, and the log shows the chain working:

```
Compatibility → θ_eff → Gate-D → BQS → Driver → Vehicle → Capacity → Time window → Route → Batch
```

- **Threshold** rejected only pairs scoring 41–61 against ~70. Legitimate.
- **Feasibility** correctly blocked request #909 at a 43.4 min time-window gap against a 20 min limit. Legitimate.
- **Gate E** produced 16 `"No driver is currently Available (all busy)"` rejections. Legitimate — that is fleet exhaustion, and the correct dashboard story is "the fleet is saturated", which is itself a result worth showing.

So high pairwise compatibility with zero *dispatched* batches is entirely possible when the fleet is busy: the batch forms and then fails at driver selection. That is the system being honest. **Do not lower thresholds to increase batch counts.**

---

## 10. Live E2E and regression

**Not performed.** No browser automation, no shell on your machine, no localhost route, no `ortools`/`pytest` in this sandbox. Your brief's §6 and §7 need to be run by you:

```bat
cd D:\rapidoproject\backend
.venv\Scripts\activate
pip install -r requirements.txt
python -m compileall -q app tests evaluation scripts
python -m pytest tests/ -q
python scripts\verify_all.py
REM with uvicorn running in another terminal:
cd .. && python e2e_test.py
cd frontend && npm install && npm run lint && npm run build
```

Because DeepSeek changed `serializers.batch_to_dict` (new `request_by_id` path) and `xai_service.get_explanations` (new filter logic), the two things most worth watching are `/api/dmfe/batches` and `/api/xai/explanations`. One shape check: the prefetch path adds `weight_kg` to each request summary while the fallback path (`batch_requests_summary`, still used by `/dmfe/batches/{id}`) may not — worth confirming the two responses agree.

---

## 11. Final readiness

| Dimension | Status |
|---|---|
| Engineering fixes did not damage research validity | **Confirmed.** Scoring, adaptive stack, OR-Tools model, schema, auth, CORS all provably unchanged |
| A-DMFE decision logic | **Sound.** The "threshold starvation" finding is refuted by the formula and by the real log |
| XAI ↔ decision consistency | **Confirmed**, and materially improved by the request-id and trip-mapping fixes |
| Live E2E | **Unverified** — must be run on your machine |
| Experimental integrity | **Two open issues (R3, R4) in the submitted paper.** Both are labelling problems, both are fixable without re-running anything |
| Results regeneration | Required for P0-3-affected delay/duration metrics |

**Not ready to submit as-is** — R3 and R4 are the blockers, and they are in the paper rather than the code. Everything else is either verified sound or waiting on a test run you can do in ten minutes.

The most important outcome of this pass is a negative one: **the change DeepSeek marked as the single most critical fix should not be made.** Had it been applied, you would have altered the adaptive decision rule that is your contribution, invalidated every experiment, and done so to solve a problem the logs show does not exist.
