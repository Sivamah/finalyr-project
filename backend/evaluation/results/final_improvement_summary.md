# IMPROVEMENT CLASSIFICATION (Static vs Adaptive)

Δ % = (adaptive_mean / static_mean − 1) × 100 over repeated seeds. Verdict uses direction-aware rules: for metrics where higher is better (completion, batching rate, utilisation, fuel/CO2 saved) a positive Δ is IMPROVEMENT; where lower is better (distance, delay, waiting, fuel/CO2 emitted, processing time) a negative Δ is IMPROVEMENT. |Δ| ≤ 5.00% is NEUTRAL.

| Category | Metric | W | Δ % (means) | Verdict |
|---|---|---|---|---|
| REQUESTS | Total requests | 50 | +0.0% | NEUTRAL |
| REQUESTS | Requests completed | 50 | +0.0% | NEUTRAL |
| REQUESTS | Requests failed | 50 | - | - |
| REQUESTS | Unassigned (single pass) | 50 | - | - |
| REQUESTS | Completion rate (%) | 50 | +0.0% | NEUTRAL |
| BATCHING | Shared trips | 50 | -6.5% | REGRESSION |
| BATCHING | Individual trips | 50 | +6.1% | REGRESSION |
| BATCHING | Batching rate % | 50 | -6.1% | REGRESSION |
| BATCHING | Avg batch size | 50 | +4.9% | NEUTRAL |
| MOBILITY | Avg trip distance (km) | 50 | -2.1% | NEUTRAL |
| MOBILITY | Total distance (km) | 50 | -3.1% | NEUTRAL |
| MOBILITY | Avg travel time (min) | 50 | -1.8% | NEUTRAL |
| MOBILITY | Avg waiting time (min) | 50 | -12.0% | IMPROVEMENT |
| MOBILITY | Avg delay (min) | 50 | -12.0% | IMPROVEMENT |
| UTILIZATION | Avg vehicle utilisation % | 50 | -0.3% | NEUTRAL |
| UTILIZATION | Driver pool utilisation % | 50 | -1.2% | NEUTRAL |
| ENVIRONMENT | Fuel consumed (L) | 50 | -4.3% | NEUTRAL |
| ENVIRONMENT | Fuel saved (L) | 50 | +20.9% | IMPROVEMENT |
| ENVIRONMENT | CO2 emitted (kg) | 50 | -4.3% | NEUTRAL |
| ENVIRONMENT | CO2 saved (kg) | 50 | +20.9% | IMPROVEMENT |
| PERFORMANCE | Pipeline runtime (s) | 50 | +13.0% | REGRESSION |
| PERFORMANCE | Processing / request (ms) | 50 | +13.0% | REGRESSION |
| PERFORMANCE | Batch formation (s) | 50 | +557.3% | REGRESSION |
| PERFORMANCE | Routing (s) | 50 | -10.6% | IMPROVEMENT |
| PERFORMANCE | Driver selection (s) | 50 | +27.1% | REGRESSION |
| PERFORMANCE | Decision gate (s) | 50 | - | - |
| PERFORMANCE | Persistence (s) | 50 | +1.6% | NEUTRAL |
| PERFORMANCE | Learning (s) | 50 | - | - |
| REQUESTS | Total requests | 100 | +0.0% | NEUTRAL |
| REQUESTS | Requests completed | 100 | +0.6% | NEUTRAL |
| REQUESTS | Requests failed | 100 | -75.0% | IMPROVEMENT |
| REQUESTS | Unassigned (single pass) | 100 | -75.0% | IMPROVEMENT |
| REQUESTS | Completion rate (%) | 100 | +0.0% | NEUTRAL |
| BATCHING | Shared trips | 100 | -3.5% | NEUTRAL |
| BATCHING | Individual trips | 100 | +6.0% | REGRESSION |
| BATCHING | Batching rate % | 100 | -3.1% | NEUTRAL |
| BATCHING | Avg batch size | 100 | +2.9% | NEUTRAL |
| MOBILITY | Avg trip distance (km) | 100 | -2.9% | NEUTRAL |
| MOBILITY | Total distance (km) | 100 | -3.2% | NEUTRAL |
| MOBILITY | Avg travel time (min) | 100 | -2.6% | NEUTRAL |
| MOBILITY | Avg waiting time (min) | 100 | -10.4% | IMPROVEMENT |
| MOBILITY | Avg delay (min) | 100 | -10.4% | IMPROVEMENT |
| UTILIZATION | Avg vehicle utilisation % | 100 | -0.6% | NEUTRAL |
| UTILIZATION | Driver pool utilisation % | 100 | -0.3% | NEUTRAL |
| ENVIRONMENT | Fuel consumed (L) | 100 | -4.6% | NEUTRAL |
| ENVIRONMENT | Fuel saved (L) | 100 | +11.2% | IMPROVEMENT |
| ENVIRONMENT | CO2 emitted (kg) | 100 | -4.6% | NEUTRAL |
| ENVIRONMENT | CO2 saved (kg) | 100 | +11.2% | IMPROVEMENT |
| PERFORMANCE | Pipeline runtime (s) | 100 | +16.2% | REGRESSION |
| PERFORMANCE | Processing / request (ms) | 100 | +16.2% | REGRESSION |
| PERFORMANCE | Batch formation (s) | 100 | +297.5% | REGRESSION |
| PERFORMANCE | Routing (s) | 100 | +0.3% | NEUTRAL |
| PERFORMANCE | Driver selection (s) | 100 | +43.2% | REGRESSION |
| PERFORMANCE | Decision gate (s) | 100 | - | - |
| PERFORMANCE | Persistence (s) | 100 | +6.0% | REGRESSION |
| PERFORMANCE | Learning (s) | 100 | - | - |
| REQUESTS | Total requests | 250 | +0.0% | NEUTRAL |
| REQUESTS | Requests completed | 250 | +1.5% | NEUTRAL |
| REQUESTS | Requests failed | 250 | -1.1% | NEUTRAL |
| REQUESTS | Unassigned (single pass) | 250 | -3.4% | NEUTRAL |
| REQUESTS | Completion rate (%) | 250 | +0.0% | NEUTRAL |
| BATCHING | Shared trips | 250 | +0.0% | NEUTRAL |
| BATCHING | Individual trips | 250 | +0.0% | NEUTRAL |
| BATCHING | Batching rate % | 250 | +0.0% | NEUTRAL |
| BATCHING | Avg batch size | 250 | +1.6% | NEUTRAL |
| MOBILITY | Avg trip distance (km) | 250 | +1.9% | NEUTRAL |
| MOBILITY | Total distance (km) | 250 | +1.8% | NEUTRAL |
| MOBILITY | Avg travel time (min) | 250 | +1.8% | NEUTRAL |
| MOBILITY | Avg waiting time (min) | 250 | -6.4% | IMPROVEMENT |
| MOBILITY | Avg delay (min) | 250 | -6.4% | IMPROVEMENT |
| UTILIZATION | Avg vehicle utilisation % | 250 | +1.8% | NEUTRAL |
| UTILIZATION | Driver pool utilisation % | 250 | +0.0% | NEUTRAL |
| ENVIRONMENT | Fuel consumed (L) | 250 | +1.3% | NEUTRAL |
| ENVIRONMENT | Fuel saved (L) | 250 | +10.7% | IMPROVEMENT |
| ENVIRONMENT | CO2 emitted (kg) | 250 | +1.3% | NEUTRAL |
| ENVIRONMENT | CO2 saved (kg) | 250 | +10.7% | IMPROVEMENT |
| PERFORMANCE | Pipeline runtime (s) | 250 | +137.7% | REGRESSION |
| PERFORMANCE | Processing / request (ms) | 250 | +137.7% | REGRESSION |
| PERFORMANCE | Batch formation (s) | 250 | +424.0% | REGRESSION |
| PERFORMANCE | Routing (s) | 250 | +47.6% | REGRESSION |
| PERFORMANCE | Driver selection (s) | 250 | +111.1% | REGRESSION |
| PERFORMANCE | Decision gate (s) | 250 | - | NEUTRAL |
| PERFORMANCE | Persistence (s) | 250 | +68.7% | REGRESSION |
| PERFORMANCE | Learning (s) | 250 | - | - |
| REQUESTS | Total requests | 500 | +0.0% | NEUTRAL |
| REQUESTS | Requests completed | 500 | +0.9% | NEUTRAL |
| REQUESTS | Requests failed | 500 | -0.3% | NEUTRAL |
| REQUESTS | Unassigned (single pass) | 500 | -1.0% | NEUTRAL |
| REQUESTS | Completion rate (%) | 500 | +0.0% | NEUTRAL |
| BATCHING | Shared trips | 500 | +0.0% | NEUTRAL |
| BATCHING | Individual trips | 500 | +0.0% | NEUTRAL |
| BATCHING | Batching rate % | 500 | +0.0% | NEUTRAL |
| BATCHING | Avg batch size | 500 | +1.0% | NEUTRAL |
| MOBILITY | Avg trip distance (km) | 500 | +1.3% | NEUTRAL |
| MOBILITY | Total distance (km) | 500 | +1.3% | NEUTRAL |
| MOBILITY | Avg travel time (min) | 500 | +1.3% | NEUTRAL |
| MOBILITY | Avg waiting time (min) | 500 | -0.1% | NEUTRAL |
| MOBILITY | Avg delay (min) | 500 | -0.1% | NEUTRAL |
| UTILIZATION | Avg vehicle utilisation % | 500 | +8.0% | IMPROVEMENT |
| UTILIZATION | Driver pool utilisation % | 500 | +0.0% | NEUTRAL |
| ENVIRONMENT | Fuel consumed (L) | 500 | +2.7% | NEUTRAL |
| ENVIRONMENT | Fuel saved (L) | 500 | +6.7% | IMPROVEMENT |
| ENVIRONMENT | CO2 emitted (kg) | 500 | +2.7% | NEUTRAL |
| ENVIRONMENT | CO2 saved (kg) | 500 | +6.7% | IMPROVEMENT |
| PERFORMANCE | Pipeline runtime (s) | 500 | +77.6% | REGRESSION |
| PERFORMANCE | Processing / request (ms) | 500 | +77.6% | REGRESSION |
| PERFORMANCE | Batch formation (s) | 500 | +226.2% | REGRESSION |
| PERFORMANCE | Routing (s) | 500 | +13.8% | REGRESSION |
| PERFORMANCE | Driver selection (s) | 500 | +4.7% | NEUTRAL |
| PERFORMANCE | Decision gate (s) | 500 | - | NEUTRAL |
| PERFORMANCE | Persistence (s) | 500 | +5.2% | REGRESSION |
| PERFORMANCE | Learning (s) | 500 | - | - |

## Aggregate verdict (mean Δ over workloads)

| Category | Metric | Mean Δ % | Verdict |
|---|---|---|---|
| REQUESTS | Total requests | +0.0% | NEUTRAL |
| REQUESTS | Requests completed | +0.7% | NEUTRAL |
| REQUESTS | Requests failed | -25.5% | IMPROVEMENT |
| REQUESTS | Unassigned (single pass) | -26.5% | IMPROVEMENT |
| REQUESTS | Completion rate (%) | +0.0% | NEUTRAL |
| BATCHING | Shared trips | -2.5% | NEUTRAL |
| BATCHING | Individual trips | +3.0% | NEUTRAL |
| BATCHING | Batching rate % | -2.3% | NEUTRAL |
| BATCHING | Avg batch size | +2.6% | NEUTRAL |
| MOBILITY | Avg trip distance (km) | -0.5% | NEUTRAL |
| MOBILITY | Total distance (km) | -0.8% | NEUTRAL |
| MOBILITY | Avg travel time (min) | -0.3% | NEUTRAL |
| MOBILITY | Avg waiting time (min) | -7.2% | IMPROVEMENT |
| MOBILITY | Avg delay (min) | -7.2% | IMPROVEMENT |
| UTILIZATION | Avg vehicle utilisation % | +2.2% | NEUTRAL |
| UTILIZATION | Driver pool utilisation % | -0.4% | NEUTRAL |
| ENVIRONMENT | Fuel consumed (L) | -1.2% | NEUTRAL |
| ENVIRONMENT | Fuel saved (L) | +12.4% | IMPROVEMENT |
| ENVIRONMENT | CO2 emitted (kg) | -1.2% | NEUTRAL |
| ENVIRONMENT | CO2 saved (kg) | +12.4% | IMPROVEMENT |
| PERFORMANCE | Pipeline runtime (s) | +61.1% | REGRESSION |
| PERFORMANCE | Processing / request (ms) | +61.2% | REGRESSION |
| PERFORMANCE | Batch formation (s) | +376.3% | REGRESSION |
| PERFORMANCE | Routing (s) | +12.8% | REGRESSION |
| PERFORMANCE | Driver selection (s) | +46.5% | REGRESSION |
| PERFORMANCE | Persistence (s) | +20.4% | REGRESSION |