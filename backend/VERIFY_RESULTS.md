# DMFE verification run

Generated 2026-08-15 20:45:49 by `scripts/verify_all.py`

```
DMFE verification suite — 2026-08-15 20:45:49
python      : 3.14.5  (D:\rapidoproject\backend\.venv\Scripts\python.exe)
backend     : D:\rapidoproject\backend
scratch db  : sqlite:///C:/Users/SIVASU~1/AppData/Local/Temp/dmfe_verify_5hj035vh/verify.db
ortools     : 9.15.6755

==============================================================================
A. STATIC CHECKS
==============================================================================
$ D:\rapidoproject\backend\.venv\Scripts\python.exe -m compileall -q app tests evaluation scripts
  [PASS] compileall (app, tests, evaluation, scripts)  — exit=0
$ D:\rapidoproject\backend\.venv\Scripts\python.exe -c import app.main; print('import ok')
    import ok
  [PASS] import app.main  — exit=0
$ ruff check --select F,E9,B .
  [SKIP] ruff F,E9,B  — ruff not installed
$ D:\rapidoproject\backend\.venv\Scripts\python.exe -m pytest tests/ -q
    ....................................................................     [100%]
    ============================== warnings summary ===============================
    <frozen importlib._bootstrap>:491
      <frozen importlib._bootstrap>:491: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute
    
    <frozen importlib._bootstrap>:491
      <frozen importlib._bootstrap>:491: DeprecationWarning: builtin type SwigPyObject has no __module__ attribute
    
    <frozen importlib._bootstrap>:491
      <frozen importlib._bootstrap>:491: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
    
    -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
  [PASS] pytest tests/  — exit=0

==============================================================================
B. DMFE RUNTIME SCENARIOS
==============================================================================

-- scenario_1_normal -------------------------------------------
    result: 4 processed, 1 shared, 1 individual, 1 unassigned
  [PASS] scenario 1 — normal run, accounting closes  — processed=4 shared=1 individual=1 unassigned=1 accounted=4

-- scenario_1b_gate_d ------------------------------------------
    High-priority ids [1, 2]; accounted ids [1, 2, 3, 4]
  [PASS] scenario 1b — Gate-D rejects accounted for (P0-1)  — processed=4 shared=1 individual=2 unassigned=0 accounted=4
  [PASS] scenario 1b — High-priority requests left a trace

-- scenario_2_minimal ------------------------------------------
    2 compatible requests, 1 driver -> shared=1 individual=0 unassigned=0
  [PASS] scenario 2 — minimal feasible (2 requests, 1 driver)  — processed=2 shared=1 individual=0 unassigned=0 accounted=2

-- scenario_3_no_driver ----------------------------------------
  [PASS] scenario 3 — no-driver control, accounting closes  — processed=3 shared=0 individual=0 unassigned=2 accounted=3
  [PASS] scenario 3 — every request in `unassigned` with a reason  — unassigned=[1, 2, 3] reasons_missing=0
      reason: No available driver/vehicle for trip with 2 request(s)
      reason: No available driver/vehicle for trip with 1 request(s)

-- scenario_4_stale_trip ---------------------------------------
    12 min old, 35 min planned -> released=0, still active=1/1
  [PASS] scenario 4 — running trip survives the 10 min cutoff (P1-5)  — released=0
    90 min old, 20 min planned -> released=1
  [PASS] scenario 4b — genuinely stuck trip is still released  — released=1 of 1

-- scenario_5_relaxed_route ------------------------------------
    relaxed path taken: True  (solver calls: 2)
    Trip VERIFY-RELAXED: total_duration_min=9.5 eta_min=9.5 max_delay_min=4.2
    stop arrival_min sequence: [0.0, 2.3, 9.0, 9.5]
  [PASS] scenario 5 — relaxed route: total_duration_min > 0 (P0-3)  — =9.5
  [PASS] scenario 5 — relaxed route: max_delay_min >= 0 (P0-3)  — =4.2
  [PASS] scenario 5 — relaxed route: arrivals non-decreasing  — [0.0, 2.3, 9.0, 9.5]

-- scenario_5b_normal_path_unchanged ---------------------------
    normal solve: duration=9.5 max_delay=4.2 relaxed_path=False
  [PASS] scenario 5b — normal solve still produces sane metrics  — duration=9.5 delay=4.2
  [PASS] scenario 5b — normal solve did NOT take the relaxed path

-- scenario_6_repeated_run -------------------------------------
  [PASS] scenario 6 — first run accounting  — processed=2 shared=1 individual=0 unassigned=0 accounted=2
    second run: processed=0 shared=0 individual=0 (pending before second run: 0)
  [PASS] scenario 6 — second run dispatches nothing new  — pending_before=0
  [PASS] scenario 6 — completed trips not reopened  — 0 -> 0

==============================================================================
C1. P1-4 PROBE — SetCumulVarSoftUpperBound with a delay penalty active
==============================================================================
    vrp_delay_penalty_per_min = 5.0; dispatching one shared trip...
    dispatch SUCCEEDED: PROBE-P1-4 duration=9.5 max_delay=4.2 distance=2.29
  [PASS] P1-4 — no TypeError with the delay penalty active  — SetCumulVarSoftUpperBound accepted the routing index
  [PASS] P1-4 — shared-trip route still solves with the penalty on  — is_shared=True duration=9.5 max_delay=4.2

==============================================================================
C2. CSP / Swagger UI
==============================================================================
    GET /api/docs -> 200  CSP=None
  [PASS] CSP absent on /api/docs  — CSP=None
    GET /api/openapi.json -> 200  CSP=None
  [PASS] CSP absent on /api/openapi.json  — CSP=None
    GET /api/dashboard/stats -> 401  CSP="default-src 'self'"
  [PASS] CSP still applied to normal API responses  — CSP="default-src 'self'"

==============================================================================
D. RELAXED-PATH HISTORY (does evaluation/results/ need regenerating?)
==============================================================================
    no *.log files containing the marker were found.
    Note: absence of log files is not proof the path was never taken.
  [INFO] relaxed OR-Tools path in logs  — not found in any log file on disk

==============================================================================
SUMMARY
==============================================================================
  PASS  compileall (app, tests, evaluation, scripts)  — exit=0
  PASS  import app.main  — exit=0
  SKIP  ruff F,E9,B  — ruff not installed
  PASS  pytest tests/  — exit=0
  PASS  scenario 1 — normal run, accounting closes  — processed=4 shared=1 individual=1 unassigned=1 accounted=4
  PASS  scenario 1b — Gate-D rejects accounted for (P0-1)  — processed=4 shared=1 individual=2 unassigned=0 accounted=4
  PASS  scenario 1b — High-priority requests left a trace
  PASS  scenario 2 — minimal feasible (2 requests, 1 driver)  — processed=2 shared=1 individual=0 unassigned=0 accounted=2
  PASS  scenario 3 — no-driver control, accounting closes  — processed=3 shared=0 individual=0 unassigned=2 accounted=3
  PASS  scenario 3 — every request in `unassigned` with a reason  — unassigned=[1, 2, 3] reasons_missing=0
  PASS  scenario 4 — running trip survives the 10 min cutoff (P1-5)  — released=0
  PASS  scenario 4b — genuinely stuck trip is still released  — released=1 of 1
  PASS  scenario 5 — relaxed route: total_duration_min > 0 (P0-3)  — =9.5
  PASS  scenario 5 — relaxed route: max_delay_min >= 0 (P0-3)  — =4.2
  PASS  scenario 5 — relaxed route: arrivals non-decreasing  — [0.0, 2.3, 9.0, 9.5]
  PASS  scenario 5b — normal solve still produces sane metrics  — duration=9.5 delay=4.2
  PASS  scenario 5b — normal solve did NOT take the relaxed path
  PASS  scenario 6 — first run accounting  — processed=2 shared=1 individual=0 unassigned=0 accounted=2
  PASS  scenario 6 — second run dispatches nothing new  — pending_before=0
  PASS  scenario 6 — completed trips not reopened  — 0 -> 0
  PASS  P1-4 — no TypeError with the delay penalty active  — SetCumulVarSoftUpperBound accepted the routing index
  PASS  P1-4 — shared-trip route still solves with the penalty on  — is_shared=True duration=9.5 max_delay=4.2
  PASS  CSP absent on /api/docs  — CSP=None
  PASS  CSP absent on /api/openapi.json  — CSP=None
  PASS  CSP still applied to normal API responses  — CSP="default-src 'self'"
  INFO  relaxed OR-Tools path in logs  — not found in any log file on disk

  24 passed, 0 failed, 1 skipped, 1 informational
```
