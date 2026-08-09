# A-DMFE Pipeline Performance Profile

Per-stage wall-clock (total s) and share of the single-pass pipeline wall time.  Route optimisation and driver selection run inside dispatch (nested), so stage shares are not additive.

## Workload 50

| Stage | Static (s) | Static % | Calls | Adaptive (s) | Adaptive % | Calls |
|---|---|---|---|---|---|---|
| Batch formation | 0.01 | 1.80 | 1 | 0.11 | 12.10 | 1 |
| Route optimisation | 0.04 | 5.20 | 35 | 0.03 | 3.50 | 34 |
| Driver selection | 0.03 | 3.90 | 35 | 0.05 | 5.10 | 34 |
| Decision gate | 0.00 | 0.00 | 15 | 0.00 | 0.00 | 15 |
| Persistence (commit) | 0.07 | 7.70 | 37 | 0.07 | 8.00 | 36 |
| Learning | 0.00 | 0.00 | 0 | 0.00 | 0.00 | 0 |
| Dispatch+assignment | 0.19 | 22.60 | 35 | 0.20 | 21.40 | 34 |
| **Pipeline wall** | 0.84 | 100.0 | - | 0.92 | 100.0 | - |

## Workload 100

| Stage | Static (s) | Static % | Calls | Adaptive (s) | Adaptive % | Calls |
|---|---|---|---|---|---|---|
| Batch formation | 0.04 | 3.90 | 1 | 0.19 | 14.20 | 1 |
| Route optimisation | 0.09 | 7.70 | 59 | 0.09 | 7.00 | 57 |
| Driver selection | 0.05 | 4.10 | 59 | 0.07 | 5.20 | 57 |
| Decision gate | 0.00 | 0.00 | 41 | 0.00 | 0.00 | 41 |
| Persistence (commit) | 0.11 | 9.90 | 61 | 0.12 | 8.70 | 59 |
| Learning | 0.00 | 0.00 | 0 | 0.00 | 0.00 | 0 |
| Dispatch+assignment | 0.33 | 28.80 | 59 | 0.36 | 27.10 | 57 |
| **Pipeline wall** | 1.13 | 100.0 | - | 1.33 | 100.0 | - |

## Workload 250

| Stage | Static (s) | Static % | Calls | Adaptive (s) | Adaptive % | Calls |
|---|---|---|---|---|---|---|
| Batch formation | 0.34 | 17.10 | 1 | 0.94 | 35.80 | 1 |
| Route optimisation | 0.11 | 5.50 | 60 | 0.09 | 3.20 | 60 |
| Driver selection | 0.36 | 17.60 | 134 | 0.38 | 14.40 | 132 |
| Decision gate | 0.00 | 0.00 | 116 | 0.00 | 0.00 | 116 |
| Persistence (commit) | 0.14 | 6.80 | 62 | 0.14 | 5.20 | 62 |
| Learning | 0.00 | 0.00 | 0 | 0.00 | 0.00 | 0 |
| Dispatch+assignment | 0.69 | 34.10 | 134 | 0.69 | 25.90 | 132 |
| **Pipeline wall** | 2.02 | 100.0 | - | 2.64 | 100.0 | - |

## Workload 500

| Stage | Static (s) | Static % | Calls | Adaptive (s) | Adaptive % | Calls |
|---|---|---|---|---|---|---|
| Batch formation | 1.25 | 31.50 | 1 | 4.26 | 57.90 | 1 |
| Route optimisation | 0.09 | 2.30 | 60 | 0.10 | 1.40 | 60 |
| Driver selection | 0.89 | 22.50 | 264 | 1.00 | 13.60 | 262 |
| Decision gate | 0.00 | 0.00 | 236 | 0.00 | 0.00 | 237 |
| Persistence (commit) | 0.18 | 4.50 | 62 | 0.19 | 2.60 | 62 |
| Learning | 0.00 | 0.00 | 0 | 0.00 | 0.00 | 0 |
| Dispatch+assignment | 1.25 | 31.30 | 264 | 1.38 | 18.70 | 262 |
| **Pipeline wall** | 3.98 | 100.0 | - | 7.36 | 100.0 | - |

## Identified bottleneck

Batch formation is the dominant cost in the adaptive pipeline (58%% of wall time at workload 500; 36%% at 250): corridor-multiplier scoring inflates its cost relative to static mode. Dispatch+assignment and driver selection are secondary (19-34%% combined). Route optimisation is minor (1-8%%) because per-batch request clusters are small. Decision and learning inference cost are negligible (<0.1%% when arm disabled in these single-pass runs).
