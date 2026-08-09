# FINAL METRICS — STATIC vs ADAPTIVE

Canonical single-run comparison (seed = 1000 + workload). Δ % is the relative change of adaptive over static.

## REQUESTS

| Metric | W | Static | Adaptive | Δ % |
|---|---|---|---|---|
| Total requests | 50 | 50 | 50 | +0.0% |
| Total requests | 100 | 100 | 100 | +0.0% |
| Total requests | 250 | 250 | 250 | +0.0% |
| Total requests | 500 | 500 | 500 | +0.0% |
| Requests completed | 50 | 50 | 50 | +0.0% |
| Requests completed | 100 | 100 | 100 | +0.0% |
| Requests completed | 250 | 110 | 112 | +1.8% |
| Requests completed | 500 | 110 | 111 | +0.9% |
| Requests failed | 50 | 0 | 0 | - |
| Requests failed | 100 | 0 | 0 | - |
| Requests failed | 250 | 140 | 138 | -1.4% |
| Requests failed | 500 | 390 | 389 | -0.3% |
| Unassigned (single pass) | 50 | 0 | 0 | - |
| Unassigned (single pass) | 100 | 0 | 0 | - |
| Unassigned (single pass) | 250 | 74 | 72 | -2.7% |
| Unassigned (single pass) | 500 | 204 | 202 | -1.0% |
| Completion rate (%) | 50 | 100.00 | 100.00 | +0.0% |
| Completion rate (%) | 100 | 100.00 | 100.00 | +0.0% |
| Completion rate (%) | 250 | 100.00 | 100.00 | +0.0% |
| Completion rate (%) | 500 | 100.00 | 100.00 | +0.0% |

## BATCHING

| Metric | W | Static | Adaptive | Δ % |
|---|---|---|---|---|
| Shared trips | 50 | 15 | 15 | +0.0% |
| Shared trips | 100 | 41 | 41 | +0.0% |
| Shared trips | 250 | 50 | 50 | +0.0% |
| Shared trips | 500 | 50 | 50 | +0.0% |
| Individual trips | 50 | 20 | 19 | -5.0% |
| Individual trips | 100 | 18 | 16 | -11.1% |
| Individual trips | 250 | 10 | 10 | +0.0% |
| Individual trips | 500 | 10 | 10 | +0.0% |
| Batching rate % | 50 | 42.90 | 44.10 | +2.8% |
| Batching rate % | 100 | 69.50 | 71.90 | +3.5% |
| Batching rate % | 250 | 83.30 | 83.30 | +0.0% |
| Batching rate % | 500 | 83.30 | 83.30 | +0.0% |
| Avg batch size | 50 | 2.00 | 2.07 | +3.5% |
| Avg batch size | 100 | 2.00 | 2.05 | +2.5% |
| Avg batch size | 250 | 2.00 | 2.04 | +2.0% |
| Avg batch size | 500 | 2.00 | 2.02 | +1.0% |

## MOBILITY

| Metric | W | Static | Adaptive | Δ % |
|---|---|---|---|---|
| Avg trip distance (km) | 50 | 12.12 | 12.40 | +2.3% |
| Avg trip distance (km) | 100 | 13.22 | 13.61 | +3.0% |
| Avg trip distance (km) | 250 | 13.56 | 14.37 | +6.0% |
| Avg trip distance (km) | 500 | 14.16 | 13.97 | -1.3% |
| Total distance (km) | 50 | 424.33 | 421.51 | -0.7% |
| Total distance (km) | 100 | 780.24 | 775.89 | -0.6% |
| Total distance (km) | 250 | 813.79 | 862.01 | +5.9% |
| Total distance (km) | 500 | 849.42 | 838.02 | -1.3% |
| Avg travel time (min) | 50 | 31.93 | 32.67 | +2.3% |
| Avg travel time (min) | 100 | 35.11 | 36.15 | +3.0% |
| Avg travel time (min) | 250 | 36.19 | 38.19 | +5.5% |
| Avg travel time (min) | 500 | 37.61 | 37.19 | -1.1% |
| Avg waiting time (min) | 50 | 4.41 | 4.53 | +2.7% |
| Avg waiting time (min) | 100 | 5.44 | 5.41 | -0.6% |
| Avg waiting time (min) | 250 | 4.72 | 4.47 | -5.3% |
| Avg waiting time (min) | 500 | 4.34 | 4.48 | +3.2% |
| Avg delay (min) | 50 | 4.41 | 4.53 | +2.7% |
| Avg delay (min) | 100 | 5.44 | 5.41 | -0.6% |
| Avg delay (min) | 250 | 4.72 | 4.47 | -5.3% |
| Avg delay (min) | 500 | 4.34 | 4.48 | +3.2% |

## UTILIZATION

| Metric | W | Static | Adaptive | Δ % |
|---|---|---|---|---|
| Avg vehicle utilisation % | 50 | 74.28 | 77.33 | +4.1% |
| Avg vehicle utilisation % | 100 | 75.60 | 78.49 | +3.8% |
| Avg vehicle utilisation % | 250 | 75.31 | 77.81 | +3.3% |
| Avg vehicle utilisation % | 500 | 76.36 | 80.81 | +5.8% |
| Driver pool utilisation % | 50 | 58.30 | 56.70 | -2.7% |
| Driver pool utilisation % | 100 | 98.30 | 95.00 | -3.4% |
| Driver pool utilisation % | 250 | 100.00 | 100.00 | +0.0% |
| Driver pool utilisation % | 500 | 100.00 | 100.00 | +0.0% |

## ENVIRONMENT

| Metric | W | Static | Adaptive | Δ % |
|---|---|---|---|---|
| Fuel consumed (L) | 50 | 15.46 | 15.64 | +1.2% |
| Fuel consumed (L) | 100 | 39.76 | 38.61 | -2.9% |
| Fuel consumed (L) | 250 | 41.23 | 42.83 | +3.9% |
| Fuel consumed (L) | 500 | 41.00 | 42.93 | +4.7% |
| Fuel saved (L) | 50 | 3.40 | 3.97 | +16.8% |
| Fuel saved (L) | 100 | 15.28 | 16.09 | +5.3% |
| Fuel saved (L) | 250 | 30.86 | 34.94 | +13.2% |
| Fuel saved (L) | 500 | 32.01 | 35.14 | +9.8% |
| CO2 emitted (kg) | 50 | 35.56 | 35.97 | +1.2% |
| CO2 emitted (kg) | 100 | 91.45 | 88.80 | -2.9% |
| CO2 emitted (kg) | 250 | 94.83 | 98.51 | +3.9% |
| CO2 emitted (kg) | 500 | 94.30 | 98.74 | +4.7% |
| CO2 saved (kg) | 50 | 7.78 | 9.07 | +16.6% |
| CO2 saved (kg) | 100 | 35.15 | 36.98 | +5.2% |
| CO2 saved (kg) | 250 | 70.99 | 80.38 | +13.2% |
| CO2 saved (kg) | 500 | 73.56 | 80.81 | +9.9% |

## PERFORMANCE

| Metric | W | Static | Adaptive | Δ % |
|---|---|---|---|---|
| Pipeline runtime (s) | 50 | 0.84 | 0.92 | +9.4% |
| Pipeline runtime (s) | 100 | 1.13 | 1.33 | +18.4% |
| Pipeline runtime (s) | 250 | 2.02 | 2.64 | +31.0% |
| Pipeline runtime (s) | 500 | 3.98 | 7.36 | +84.9% |
| Processing / request (ms) | 50 | 16.75 | 18.34 | +9.5% |
| Processing / request (ms) | 100 | 11.26 | 13.33 | +18.4% |
| Processing / request (ms) | 250 | 8.08 | 10.57 | +30.8% |
| Processing / request (ms) | 500 | 7.96 | 14.72 | +84.9% |
| Batch formation (s) | 50 | 0.01 | 0.11 | +640.0% |
| Batch formation (s) | 100 | 0.04 | 0.19 | +339.5% |
| Batch formation (s) | 250 | 0.34 | 0.94 | +173.9% |
| Batch formation (s) | 500 | 1.25 | 4.26 | +240.5% |
| Routing (s) | 50 | 0.04 | 0.03 | -27.3% |
| Routing (s) | 100 | 0.09 | 0.09 | +6.9% |
| Routing (s) | 250 | 0.11 | 0.09 | -23.4% |
| Routing (s) | 500 | 0.09 | 0.10 | +8.6% |
| Driver selection (s) | 50 | 0.03 | 0.05 | +42.4% |
| Driver selection (s) | 100 | 0.05 | 0.07 | +50.0% |
| Driver selection (s) | 250 | 0.36 | 0.38 | +7.0% |
| Driver selection (s) | 500 | 0.89 | 1.00 | +11.9% |
| Decision gate (s) | 50 | 0.00 | 0.00 | - |
| Decision gate (s) | 100 | 0.00 | 0.00 | - |
| Decision gate (s) | 250 | 0.00 | 0.00 | - |
| Decision gate (s) | 500 | 0.00 | 0.00 | +0.0% |
| Persistence (s) | 50 | 0.07 | 0.07 | +12.3% |
| Persistence (s) | 100 | 0.11 | 0.12 | +2.7% |
| Persistence (s) | 250 | 0.14 | 0.14 | -0.7% |
| Persistence (s) | 500 | 0.18 | 0.19 | +6.1% |
| Learning (s) | 50 | 0 | 0 | - |
| Learning (s) | 100 | 0 | 0 | - |
| Learning (s) | 250 | 0 | 0 | - |
| Learning (s) | 500 | 0 | 0 | - |
