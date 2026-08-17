# A-DMFE Manual Live QA Report

## 1. Environment

- **OS**: Windows
- **Backend**: FastAPI (Python), Google OR-Tools, SQLite
- **Frontend**: React (Vite), Tailwind CSS
- **Test Execution**: Local manual execution using simulated data via `browser_subagent`.

## 2. Pages Tested

- `/dashboard` (Overview & Baseline Metrics)
- `/simulation-monitor` (Simulation Engine Control)
- `/dmfe` (A-DMFE Queue & Analysis)
- `/xai` (Explainability Dashboard)
- `/analytics` (Metrics & KPI Dashboard)
- `/drivers` (Fleet State)

## 3. Simulation Results

The simulation successfully generates realistic traffic.
- **Observations**: Requests spawn with pickup/drop locations, types, and priorities. Queue grows steadily.
- **Issues**: While requests enter the queue and trips are generated, the overall system metrics desynchronize from the simulation clock.

## 4. A-DMFE Engine Results

The DMFE Engine processes pairs but aggressively rejects them.
- **Candidates Generated**: Yes, thousands of candidates are assessed.
- **Batches Created**: Some batches form, but an overwhelmingly high percentage are rejected during adaptive scoring phases.

## 5. Rejection Analysis

The rejection rate is extremely high, starving the routing engine.
- **Primary Cause**: `θ_eff` (Effective Threshold) is climbing too high due to the Adaptive Learning module.
- **Example**: Pairs with 69.5% compatibility (CS) were rejected because the threshold `θ_eff` was 69.9%. In extreme cases, high 90%+ pairs were rejected if constraints broke.

## 6. Compatibility Results

Compatibility scoring mathematically functions correctly but faces overly aggressive thresholds.
- The `CS` metric calculates spatial/temporal proximity accurately.

## 7. Feasibility Results

Feasibility gates correctly block mathematically impossible pairs.
- **Observation**: Request #909 was correctly rejected because the time window difference (43.4 min) exceeded the system hard limit of 20 min.

## 8. Driver Selection

- **Issue**: Drivers are correctly marked as "Busy" in the `/drivers` (Fleet) view when assigned. However, the Main Dashboard reports `Drivers Active: 0`, completely failing to reflect driver assignment state.

## 9. Vehicle Selection

- **Issue**: Similar to drivers, 15 vehicles were correctly engaged (Busy) in the fleet view, but the Main Dashboard reports `Vehicles Active: 0`.

## 10. Routing

- **Observation**: When direct routing is chosen, XAI correctly cites "low route overlap or different directions".
- **Limitation**: Due to the aggressive adaptive threshold rejecting most batches, the VRP routing engine is starved of complex multi-stop routes to optimize.

## 11. Adaptive Learning

- **Observation**: The Adaptive Learning system dynamically adjusts `θ_eff`.
- **Bug / Research Issue**: The logic is flawed. The threshold becomes artificially inflated over time, making it nearly impossible for reasonable pairs to form batches.

## 12. XAI / Explainability

- **Explainability Accuracy**: Excellent. No text contradictions were found.
- **Evidence**: XAI clearly states "Score below effective threshold" when `CS < θ_eff`, and correctly identifies constraint violations (e.g., time window > 20 min).

## 13. Trip Lifecycle

- **Integration Break**: Data inconsistency between Simulation and Dashboard. The Trip transitions successfully to "Completed", but the dashboard aggregates (Active Drivers/Vehicles, Batches Created) freeze at 0.

## 14. Analytics

Multiple critical desynchronization bugs were observed on the `/analytics` page:
- **RPM (Requests per minute)**: Reports `0.1 req/m` despite processing >1000 requests in 8 minutes (should be ~125 RPM).
- **Average Queue Waiting Time**: Reports `30773.8 sec` (~8.5 hours) after only a few minutes of runtime. The system is incorrectly subtracting simulated morning timestamps (e.g., 8:50 AM) from the physical system wall-clock time (e.g., 2:26 PM).
- **Average Completion Time**: Same wall-clock vs simulation-clock calculation error (reports ~2 hours).

## 15. Performance Observations

- UI performance is smooth and responsive.
- Wait times for A-DMFE analysis scale slightly as the queue grows, but no browser freezes occurred.

## 16. UI Problems

- **Dashboard Operations Summary**: Displays `0` for Drivers Active, Vehicles Active, and Batches Created, despite the fleet page showing 15 busy drivers/vehicles and telemetry showing 835 shared trips.
- **Dashboard Telemetry Contradiction**: Lists `Batches Created: 0` right next to `Shared Trips: 835`.

## 17. Unnecessary Features / Cleanup Candidates

- **Review**: The logic that calculates RPM in the analytics dashboard uses the wrong denominator (wall clock instead of simulation elapsed time).

## 18. Bugs

| ID | Severity | Screenshot | Location | Problem | Evidence | Suspected Cause | Recommended Fix |
|---|---|---|---|---|---|---|---|
| B1 | P1 | `11_error_analytics.png` | `/analytics` | Huge Queue Wait Times (8.5 hrs) | Dashboard shows `30773.8 sec` wait time. | Wall clock vs Simulation clock desync. | Use simulation elapsed time instead of `datetime.now()` for metrics. |
| B2 | P1 | `11_error_analytics.png` | `/analytics` | Incorrect RPM | RPM shows `0.1 req/m`. | Same clock desync issue. | Calculate RPM using simulation uptime. |
| B3 | P2 | `01_dashboard_baseline.png` | `/dashboard` | Active Fleet is 0 | Dashboard shows 0 active drivers/vehicles. | Dashboard UI not subscribing to fleet state updates. | Link Dashboard Overview to actual Fleet states. |
| B4 | P2 | `01_dashboard_baseline.png` | `/dashboard` | Contradictory Batch Stats | Batches Created: 0, Shared Trips: 835. | Incorrect aggregations in summary panel. | Fix batch count metric fetching. |

## 19. Optimization Recommendations

| ID | Area | Current Behavior | Evidence | Recommended Optimization | Risk |
|---|---|---|---|---|---|
| O1 | Analytics DB | Wall-clock dependence | Queue wait time > 8 hours on a 10 min test | Standardize all temporal metrics to use simulated timestamps. | Low |

## 20. Research-Sensitive Findings

**CRITICAL: Adaptive Threshold Starvation**
The A-DMFE Engine's adaptive module artificially inflates the effective threshold (`θ_eff`) too high, too fast. This causes a near 100% rejection rate for batching, even when compatibility scores are perfectly acceptable (e.g., rejecting 69.5% against a 69.9% threshold). This completely neuters the optimization engine and prevents OR-Tools from solving complex VRPs.

## 21. Claude Handoff

### MUST FIX
- **Adaptive Learning Formula**: Adjust the threshold scaling logic in the DMFE engine. It is starving the batching system by raising `θ_eff` excessively.
- **Simulation Clock Desync**: Fix the wait time, completion time, and RPM formulas. They are using physical system time instead of the simulation clock.

### SHOULD FIX
- **Dashboard Aggregations**: Fix the "Active Drivers", "Active Vehicles", and "Batches Created" counters on the main dashboard which are perpetually stuck at 0.

### OPTIMIZATION
- Consolidate time utilities to ensure the entire application strictly adheres to the simulation clock when tests are running.

### REMOVE / REVIEW
- Review the `Batches Created` vs `Shared Trips` definitions on the dashboard to ensure they do not visually contradict each other.

### DO NOT TOUCH
- **XAI Explanation Logic**: The explainability text generator is highly accurate and correctly reflects the underlying decision math.
- **Feasibility Constraints Gate**: The hard limits (e.g., 20-min time window) correctly block bad routes.

### NEEDS RE-TESTING
- After the Adaptive Learning threshold is fixed, the entire OR-Tools VRP routing flow must be re-tested (Part 9 & Part 10), as the current threshold starvation prevented a comprehensive routing audit.
