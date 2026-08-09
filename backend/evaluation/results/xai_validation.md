# STEP 7 — XAI VALIDATION

Workloads: 60 requests, seed 1060 — adaptive then static mode.  Every contribution shown is recomputed from the stored factor scores and the stored SystemConfig weights; recomputed CS must reproduce the recorded score.

## ADAPTIVE DECISIONS

### 1. Accepted batch — `BATCH-0020-0027`
- Decision: **Compatible** | CS 90.90 vs θ_eff 70.20
- Confidence (recomputed): 68.00 | BQS (recomputed) 0.85 vs θ_bqs 0.55
- **Attribution audit**: stored CS 90.90 vs recomputed 90.70 → MATCH
- Factor scores (stored): `{"pickup": 0.899, "route": 0.948, "time": 0.952, "capacity": 1.0, "priority": 0.6}`
- Signed contributions a_f = w_f·(f_f−0.5): `{"pickup": 0.1197, "route": 0.112, "time": 0.0904, "capacity": 0.075, "priority": 0.01}`
- Top contributors: pickup: +0.12, route: +0.11, time: +0.09
- Stored reason: ✓ Pickup distance is small (504 m — within acceptable range); ✓ Trips share a similar route and direction; ✓ Route overlap is High; ✓ Request time difference is acceptable (1.0 min); ✓ Vehicle capacity: Capacity ample (<=50% utilised); ✓ Estimated additional delay is minimal (1.0 min); ✓ Same provider — optimal; ✓ Combined request priority is Medium; ℹ️ A-DMFE: BATCHED — CS 90.9% ≥ θ_eff 69.9%, BQS 0.81 ≥ θ_bqs 0.55; ℹ️ Factor 'route' contributed +0.126; ℹ️ Factor 'pickup' contributed +0.114; ℹ️ Factor 'time' contributed +0.091; ℹ️ Decision confidence 72.2% (margin over θ_eff + factor agreement + delay headroom); ✓ Dispatched: driver #49 (Driver 49), vehicle #49 (Car), ETA 1.3 min, driver score 1.229, actual delay 6.3 min, utilization 50%, fuel 0.41 L, CO₂ saved 0.73 kg, confidence 98%

### 2. Rejected batch — `TRIP-0003`
- Decision: **Individual** | score 0.00 vs recomputed 0.00 | θ_eff 70.20
- Stored reason: Solo trip — no compatible batch found; ✓ Dispatched: driver #8 (Driver 08), vehicle #8 (Bike), ETA 2.5 min, driver score 1.208, actual delay 2.0 min, utilization 100%, fuel 0.12 L, CO₂ saved 0.00 kg, confidence 97%

### 3. Selected driver — trip `BATCH-0020-0027`
- **Recorded**: driver 49 Driver 49 | vehicle 49 (Car)
- Recomputed DriverSelector pick: driver 43 (total 1.223) → DIFFERENT — probe runs after the workload; the recorded pick is authoritative
- Factor scores: proximity 0.945, type 1.0, workload 1.0, fairness 1.0, history 1.0 | ETA 1.6 min
- Weights used: {'proximity': 0.5, 'type': 0.3, 'workload': 0.2, 'fairness': 0.1, 'history': 0.15}
- Adaptive proximity bump: +0.000

### 4/5. Adaptive vs static rationale
- resolve_mode(db) = **adaptive** | base θ 70.00 → θ_eff 70.20
- build_adaptive_reasons(...) with mode **adaptive** yielded 5 term(s):
  - ℹ️ A-DMFE: BATCHED — CS 90.9% ≥ θ_eff 70.2%, BQS 0.85 ≥ θ_bqs 0.55
  - ℹ️ Factor 'pickup' contributed +0.120
  - ℹ️ Factor 'route' contributed +0.112
  - ℹ️ Factor 'time' contributed +0.090
  - ℹ️ Decision confidence 68.0% (margin over θ_eff + factor agreement + delay headroom)

## STATIC DECISIONS

### 1. Accepted batch — `BATCH-0020-0027`
- Decision: **Compatible** | CS 90.70 vs θ_eff 70.20
- Confidence (recomputed): 68.00 | BQS (recomputed) 0.85 vs θ_bqs 0.55
- **Attribution audit**: stored CS 90.70 vs recomputed 90.70 → MATCH
- Factor scores (stored): `{"pickup": 0.899, "route": 0.948, "time": 0.952, "capacity": 1.0, "priority": 0.6}`
- Signed contributions a_f = w_f·(f_f−0.5): `{"pickup": 0.1197, "route": 0.112, "time": 0.0904, "capacity": 0.075, "priority": 0.01}`
- Top contributors: pickup: +0.12, route: +0.11, time: +0.09
- Stored reason: ✓ Pickup distance is small (504 m — within acceptable range); ✓ Trips share a similar route and direction; ✓ Route overlap is High; ✓ Request time difference is acceptable (1.0 min); ✓ Vehicle capacity: Capacity ample (<=50% utilised); ✓ Estimated additional delay is minimal (1.0 min); ✓ Same provider — optimal; ✓ Combined request priority is Medium; ✓ Dispatched: driver #49 (Driver 49), vehicle #49 (Car), ETA 1.3 min, driver score 1.229, actual delay 6.3 min, utilization 50%, fuel 0.41 L, CO₂ saved 0.73 kg, confidence 98%

### 2. Rejected batch — `TRIP-0003`
- Decision: **Individual** | score 0.00 vs recomputed 0.00 | θ_eff 70.20
- Stored reason: Solo trip — no compatible batch found; ✓ Dispatched: driver #8 (Driver 08), vehicle #8 (Bike), ETA 2.5 min, driver score 1.208, actual delay 2.0 min, utilization 100%, fuel 0.12 L, CO₂ saved 0.00 kg, confidence 97%

### 3. Selected driver — trip `BATCH-0020-0027`
- **Recorded**: driver 49 Driver 49 | vehicle 49 (Car)
- Recomputed DriverSelector pick: driver 49 (total 1.162) → SAME as recorded selection
- Factor scores: proximity 0.957, type 1.0, workload 0.686, fairness 0.967, history 1.0 | ETA 1.3 min
- Weights used: {'proximity': 0.5, 'type': 0.3, 'workload': 0.2, 'fairness': 0.1, 'history': 0.15}
- Adaptive proximity bump: +0.000

### 4/5. Adaptive vs static rationale
- resolve_mode(db) = **static** | base θ 70.00 → θ_eff 70.20
- build_adaptive_reasons(...) with mode **static** yielded 0 term(s):
  - (empty — static mode writes no adaptive language)
