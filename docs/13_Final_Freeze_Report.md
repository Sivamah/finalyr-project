# Final Freeze Report — A-DMFE Platform

Status of every deliverable required for phase 8, with evidence. Freeze date:
2026-08-09. No further feature work; only bug fixes on report bugs if requested.

## Deliverable checklist

| # | Deliverable | Status | Evidence |
|---|---|---|---|
| 1 | Full test regression | DONE | `pytest tests/` — 59 passed, 0 failed (also `compileall` OK, `from app.main import app` OK after all edits) |
| 2 | Full repeated-seed A/B experiments | DONE | `evaluation/results/admfe_repetitions.json` (w:mode:rN, 50/100/250 x5 reps, 500 x3 reps, both modes) |
| 3 | Statistical summary | DONE | `results/final_statistical_summary.csv` (mean/std/min/max/n per metric), `results/final_metrics_table.md` |
| 4 | Improvement summary | DONE | `results/final_improvement_summary.md` (direction-aware, EPS=5%, <5ms absolute → NEUTRAL) |
| 5 | Final performance profile | DONE | `results/performance_profile.md` + `graphs/*.json` (stage shares; bottleneck = batch formation) |
| 6 | Learning validation | DONE | `results/learning_validation.md` (updates/refits, corridor multipliers, biases, day-1 vs day-5 error, ON vs OFF) |
| 7 | XAI validation | DONE | `results/xai_validation.md` (CS/confidence/BQS recomputed from stored state, attribution audit MATCH, signed contributions, reason storage) |
| 8 | Dashboard honesty fixes | DONE | `app/services/simulation_service.py` (real avg completion time from trips), `ReportExport.jsx` (`.xls` HTML export mislabeled as xlsx fixed) |
| 9 | Live-tracking audit | DONE | Static seeded positions over REST; not GPS, no push channel (documented, not "real-time GPS") |
| 10 | Dead-code cleanup | DONE | Removed unreferenced: debug_dataset.py, run_experiments.py, make_snapshot.py, stale CSVs/JSON/DBs, logs, __pycache__/pytest_cache |
| 11 | Structure snapshot | DONE | Final tree captured below; experiment pipeline, framework, tests, and all numbered docs retained |
| 12 | Reproducibility guide | DONE | `docs/Reproducibility_Guide.md` (env versions, seed scheme, pipeline order, output locations) |
| 13 | IEEE tables + paper update | DONE | `evaluation/results/ieee_tables.md` / `.tex` (4 tables, regenerated) + `docs/04_IEEE_Paper_Draft.md` updated with audited numbers, discussion and limitations |

## Final numbers (single source of truth)

Static vs adaptive DMFE, canonical seed 1000+W, deterministic simulation:

- Utilisation: +4.1 / +3.8 / +3.3 / +5.8 % (W=50/100/250/500)
- Fuel saved: +16.8 / +5.3 / +13.2 / +9.8 %
- CO2 saved: +16.6 / +5.2 / +13.2 / +9.9 %
- Unassigned: 0 / 0 / −2.7 / −1.0 %
- Avg waiting: +2.7 / −0.6 / −5.3 / +3.2 %
- On-arm delay error day1→day5 (learning): 1.41→0.34 (W50), 0.96→0.81 (W100), flat ≈1.0–1.1 (W250/500); completion 100% both arms, all workloads
- XAI audit: stored CS 90.90 vs recomputed 90.70 (tolerance 0.55 → MATCH), BQS 0.85 vs θ_bqs 0.55, decision confidence 68.0% as recorded
- Wall time: adaptive 0.92s (W50) → 7.36s (W500); batch formation 58% of wall time at W500 adaptive vs 31.5% static

## Final repository structure (relevant trees)

```
backend/
  app/                  # FastAPI app + dmfe engine (code, unchanged except Step-8 fix)
  tests/                # 59 tests
  evaluation/           # framework.py, run_admfe_experiments.py, final_validation.py,
                        # phase8_validation.py, make_admfe_report.py, verify_admfe.py,
                        # verify_unified_scoring.py, analyze_unified.py, run_feedforward.py,
                        # results/ (all generated artifacts + graphs/)
backend/requirements.txt
frontend/               # React app (Step-8 export fix)
docs/
  01..12 + Reproducibility_Guide.md
```

## Honesty ledger

- No significance claims: repeated seeds vary RNG; stats are descriptive.
- "Adaptive wins" apply at W=100–250; at W=500 gap narrows (static saturates),
  learning is flat, and adaptivity costs ~2x wall time (batch formation).
- Learning is inert below 60 drivers (W=50).
- Live-tracking map = seeded static positions (REST polling), not GPS.
- `results/` is 100% regenerable from the documented pipeline.