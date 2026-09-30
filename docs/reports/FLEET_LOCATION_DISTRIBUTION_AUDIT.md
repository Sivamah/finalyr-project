# Fleet Location Distribution Audit — Clustered/Stacked Vehicle Markers

**Date:** 2026-09-24
**Scope:** Fleet Dashboard → Fleet Locations marker stacking; the shared
`/api/vehicles/locations` feed and its consumers (Overview, Live Operations,
AI Insights).
**Untouched:** no code changed. A-DMFE, DMFE, OR-Tools, compatibility,
thresholds, batching, XAI untouched. This report is read-only evidence.

---

## 1. Executive summary

The vehicles are **genuinely colocated in the backend data** — this is not a
frontend-only drawing bug and not a zoom artifact. ~100 of the 115 vehicles
entered the database via repeated CSV **dataset uploads**, and those CSVs are
extremely poor spatial models: many batches encode a near-solid grid of
coordinates around one anchor line (`lng = 76.9558`, `lat` stepped 0.0001° ≈
11 m), some batches reused the exact model default `(11.0168, 76.9558)` for
every vehicle, and one name family (`V0…V19`) exists **twice** — same name,
same coordinate — so the dedupe-by-name import did not prevent duplicated rows.
The result: 40 of 115 vehicles share an exact (lat, lng); 14 sit on the exact
map-center point; ≥65 vehicles have a peer within 100 m; the big green blob at
the centre of the Fleet Locations screenshot is `~48 vehicles within ~200 m of
the map centre`, almost all Available.

It is **not** an intentional hub model. The project's intended simulation
"hubs" are the 6 `SAMPLE_COORDINATES` in `driver_service.py` and the demand
areas in `mock_adapters.py` — the uploaded fleet data never went through them.

## 2. Data provenance

| Source | Rows | Names | Where they sit |
|---|---|---|---|
| `driver_service.seed_initial_data_if_needed` | 15 | `Vehicle 1 … Vehicle 15` | 6 `SAMPLE_COORDINATES` cycling (spread across city) |
| CSV dataset uploads (retained `backend/datasets/*.csv`) | ~40 | `V01 … V40` | lat/lng diagonal 10.984→11.08 × 76.944→76.96 (city-wide line) |
| CSV dataset uploads (retained) | ~10 | `CBE-V-001…` etc. | fixed-lat vertical strips lng 76.9415→76.9701 |
| CSV uploads, re-uploaded 50+ times | 2 names | `CBE-V-901/902` | fixed `(11.0132,76.9558)`, `(11.0216,76.9701)` |
| Origin not in retained CSVs / direct inserts | 20 duplicated | `V0…V19` (×2) | lat 11.0168→11.0187 × `76.9558` const (≈200 m line) |
| Origin not in retained CSVs / direct inserts | 10 | `V2-0 … V2-9` | **all** on the exact default `(11.0168, 76.9558)` |

`100` of `115` vehicles entered through the CSV upload path
(`orchestration.py /datasets/upload`). The upload logic reads optional
`latitude`/`longitude` columns and otherwise lets the **ORM column default
`(11.0168, 76.9558)`** apply (`models.py:58-59`) — so any fleet CSV without
(real, spread) coordinates lands every vehicle on one point.

## 3. Actual coordinate statistics (read directly from `backend/dmfe_dev.db`)

| Metric | Value |
|---|---|
| Total vehicles in DB | **115** |
| Vehicles with usable coords (= `/api/vehicles/locations` feed) | **115** (0 omitted) |
| Unique (lat, lng) pairs | **75** |
| Exact-duplicate coordinates (same 1e-6°) | **40 vehicles** (of 115) |
| Vehicles with a peer within 10 m | 65 |
| Vehicles with a peer within 50 m | 65 |
| Vehicles with a peer within 100 m | 65 |
| Largest exact-dup group | `(11.0168, 76.9558)` × **14** |
| Second group | `(11.0169…11.0187, 76.9558)` × 2 each (V-line, 11 m spacing) |
| Min lat / max lat | 10.998 / 11.080 (≈ 9.1 km N–S) |
| Min lng / max lng | 76.940 / 77.030 (≈ 8.9 km E–W) |
| Duplicate **names** (V0×2, V1×2 … V19×2) | 20 rows — same name twice |

### Status-wise distribution (snapshot A vs B, a few minutes apart — statuses are dynamic)

| Status | Snapshot A | Snapshot B | Unique coords (B) | Within 200 m of centre (B) | Within 1 km (B) |
|---|---|---|---|---|---|
| Available (green) | 82 | **88** | 67 | **36** | 55 |
| Busy (blue) | 33 | **27** | 17 | 12 | 15 |
| Maintenance / Offline | 0 | 0 | — | — | — |

(The running DMFE simulation flips vehicles Available↔Busy as trips assign and
complete, so exact split drifts. `complete_stale_trips` at backend startup
releases stuck Busy vehicles.)

### Geographic spread

The fleet genuinely spans the Coimbatore urban core (~9 km × ~9 km). The Busy
set is carried mostly by the seeded `SAMPLE_COORDINATES` rows and the `V01…V40`
diagonal — i.e. spread out. The Available set is instead loaded onto the
centre: ~36 of ~88 Available are within 200 m of the map centre.

## 4. The marker blob

At the default zoom (MapContainer `zoom={12}`), 0.0001° ≈ 0.3 px, so the
entire ~200 m `V0…V19` line plus the 14-at-centre stacks render as a few-pixel
solid dot sitting exactly on `COIMBATORE_CENTER (11.0168, 76.9558)`. That is
the visual: one dense green centre with the thin Busy scatter beyond it.

`VehicleLocationMap.jsx` renders **flat, unclustered markers** (one
`LeafletMarker` per location, `zoom=12`). By contrast, `LiveMapContainer` +
`FleetLayer` feed the **same** coordinates through a count-badge cluster
(`clusterFleet: true` in all three MODE_CONFIGs), which is why Overview / Live
Operations / AI Insights *look* acceptable on identical data.

## 5. Whether clustering is intentional or a defect

**Not intentional and not physically meaningful.** Expected behaviour is
"simulated/ last-known positions around Coimbatore, not live GPS". A city-wide
spread (~9 km) is appropriate; but 65/115 vehicles within 100 m of a peer is an
**ingestion artifact**, caused by:

1. **ORM default on insert** (`models.py:58-59`) — any CSV row without coords
   (or a fleet generator that forgets them) lands on `(11.0168, 76.9558)`.
2. **Grid-style upstream CSVs** — 0.0001°/0.004° linear lat/lng steps are a
   spreadsheet grid, not a fleet distribution; they produce collinear marker
   streaks.
3. **Repeated uploads** of the same small CSVs and duplicated name families
   (`V0…V19` ×2) — the by-name dedupe in `orchestration.py:95` only stops
   rows whose `name` matches an existing row; the doubled `V*` rows prove a
   second insert path (provenance not in the retained CSVs) bypassed it.
4. **No spatial spread/jitter anywhere** in fleet ingestion (unlike
   `mock_adapters.py` which jitters demand pickups).

## 6. Files responsible

| File | Role |
|---|---|
| `backend/app/db/models.py:58-59` | `Vehicle.current_lat/lng` default `11.0168 / 76.9558` (insert-time silent colocation) |
| `backend/app/api/routes/orchestration.py:90-128` | CSV import: optional coords, by-name dedupe, no spread, no jitter |
| `backend/app/services/driver_service.py:11-18, 83-106` | Seeder: 15 vehicles on 6 `SAMPLE_COORDINATES` (fine, but tiny) |
| `backend/datasets/tmp*.csv` | The uploaded fleet grids (many batches, collinear coords) |
| `frontend/src/components/drivers/VehicleLocationMap.jsx:85-123` | Renders 115 flat markers, no clustering (amplifies, not causes) |
| `frontend/src/hooks/useOperationalNetwork.js:48` | Shares the identical feed with Overview/Live Ops/AI Insights |

## 7. Same logic on other maps?

Yes — every map consumes the **same** `/api/vehicles/locations` feed:
- **Fleet Locations** (`DriverDashboard` → `VehicleLocationMap`): flat markers → **blob visible**
- **Overview / Live Operations** (`LiveMapContainer` + `FleetLayer`): count-badge clustering → **blob hidden, same data**
- **Simulation map** (`LiveSimulationMap` → `LiveMapContainer`): clustered → hidden
- **XAI map** (`XaiMapPanel` → `LiveMapContainer`): clustered → hidden

So the underlying dataset issue is platform-wide; only the Fleet Locations
renderer lacks the mitigation the other maps already use.

## 8. Root cause

> **Backend data defect, not a frontend rendering bug.** The fleet was
> assembled by seeding 15 vehicles + bulk CSV imports whose coordinate
> columns encode near-solid grid/duplicate positions around one anchor
> (`76.9558` longitude, `(11.0168,76.9558)` centre), and the ORM default
> silently stacks any row that carries no coordinate onto that same centre.
> 40/115 vehicles share an exact coordinate and ≥65/115 cluster within 100 m;
> the green mass in the screenshot is that real, duplicated, centre-loaded
> data drawn by a marker renderer that (unlike the other map surfaces) does
> not cluster.

## 9. Safest fix (recommendation only — not yet implemented)

Must not "invent coordinates", must not touch A-DMFE/OR-Tools inputs, must
not change research logic.

1. **Frontend display clustering for `VehicleLocationMap.jsx` (safest, zero
   research impact).** Reuse the existing cluster pattern that the working maps
   already use: collapse co-located markers into a counted badge (dominant
   status colour) that dissolves on zoom-in. This is a **display-only**
   change — stored coordinates, distances, OR-Tools matrix inputs untouched.
   This alone restores legibility while preserving marker click/popup, center,
   zoom, filters, refresh.
2. **Backend ingestion guard (optional, for future imports).** In
   `/datasets/upload`, when many rows land on one coordinate, distribute them
   deterministically (e.g. the 6 SAMPLE_COORDINATES / area grid already used by
   the platform, with small fixed offsets) instead of piling every row onto the
   ORM default. This changes new imports only — **do not** rewrite existing
   `current_lat/current_lng` values, because `driver_selection.py`,
   `optimizer.py` and `adaptive/context.py` use those coordinates as depots /
   distance sources; rewriting them would alter DMFE inputs.
3. **Data hygiene (optional, low-risk).** Optionally de-duplicate the 20
   doubled `V0…V19` name rows (they are literal duplicates) via a one-off SQL
   against a documented snapshot.

## 10. Backend, seed data, or frontend?

- Primary defect: **backend data state** (imported fleet content + ORM
  default).
- Second: **frontend renderer** lacks the clustering its sibling maps use.
- Seed data (`driver_service` seeder) is **fine** — it is the only source that
  used the hub model.

## 11. A-DMFE / research logic affected?

**No.** No weight, formula, threshold, batch rule, OR-Tools constraint or XAI
calculation is changed by either fix above. Fix 1 is display-only. Fix 2
touches *new* imports. Any fix that rewrites existing stored coordinates would
in principle alter DMFE depot inputs and must be avoided (explicitly
out of scope).

---

## Verdict

FLEET LOCATION DATA:
INCORRECT

(Individually genuine recorded coordinates — nothing invented — but the
distribution is an ingestion artifact: 40 exact duplicates, 14 on one point,
~48 in a 200 m centre blob, a doubled `V0…V19` name family, and collinear CSV
grids. Not an intentional hub model.)

ROOT CAUSE:
CSV fleet imports + the ORM coordinate default sink every Available vehicle
onto a few centre coordinates around `(11.0168, 76.9558)`; 100/115 vehicles
arrived via those uploads, and the flat-marker renderer does not cluster like
the other maps' `FleetLayer` does.

FIX REQUIRED:
YES

Recommended order: (1) add the existing cluster/display de-collision to
`VehicleLocationMap.jsx`; (2) optionally harden `/datasets/upload` spread for
future imports; (3) optionally de-duplicate the `V0…V19` rows. Do **not**
re-randomise or rewrite existing stored coordinates.