# Fleet Locations Map — "API KEY REQUIRED" Basemap Root-Cause Report

**Date:** 2026-09-24
**Scope:** Fleet Dashboard → Fleet Locations basemap only.
**Untouched:** A-DMFE, DMFE, OR-Tools, compatibility rules, thresholds,
batching, vehicle assignment, provider logic, simulation, XAI. No decision,
weight, threshold or constraint was altered.

---

## 1. Problem summary

Vehicle markers render correctly on the Fleet Locations map, but the basemap is
covered in repeated diagonal text — "API KEY REQUIRED" with a
`carto.com/basemaps/…` reference. The marker layer is fine; the tile layer is
visually broken.

## 2. Exact reproduction result

Fleet → Fleet Locations tab (`/drivers`). Vehicle markers render over a
watermarked basemap. No console errors, no JavaScript exceptions, no failed
network requests. The tiles are served successfully — the watermark is *inside*
the downloaded tile images.

## 3. Exact failing URL / provider

```
Provider: CARTO (basemaps.cartocdn.com)
URL:      https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png
Key:      none appended
```

The screenshot text "carto.com/basemaps/positron" could not be traced to any
string in the repository (the only CARTO style used is `voyager`; the current
watermark reference page is `carto.com/basemaps/apikey`). It is treated as a
paraphrase of the watermark's provider URL; it does not change the diagnosis.

## 4. Browser / network evidence

Sampled directly over HTTP from this environment:

| Request | Status | Content-Type | Size | Watermark in pixels |
|---|---|---|---|---|
| `a.basemaps.cartocdn.com/rastertiles/voyager/12/2924/1921.png` | 200 | image/png | 17,276 B | YES (diagonal band) |
| `a.basemaps.cartocdn.com/dark_all/12/2924/1921.png` | 200 | image/png | 7,995 B | YES (same treatment) |
| `a.basemaps.cartocdn.com/light_all/12/2924/1921.png` | 200 | image/png | 12,835 B | YES (same treatment) |
| `a.tile.openstreetmap.org/12/2924/1921.png` | 200 | image/png | 39,451 B | NO (clean) |

The CARTO PNGs were decoded and their pixels contain a rotated text band; the
OSM tile does not. This is therefore a **provider-generated error/notice tile**,
not a frontend overlay, not a CSS layer, not CORS, not a 401/403, and not a
broken token (no token is sent at all).

## 5. Source-code trace

```
AdminLayout.jsx:19 (nav "Fleet")  →  route /drivers
DriverDashboard.jsx:159          →  tab "Fleet Locations" (id: 'map')
DriverDashboard.jsx:294-296      →  <VehicleLocationMap locations onRefresh>
VehicleLocationMap.jsx:80-83     →  <TileLayer url=…basemaps.cartocdn.com/
                                        rastertiles/voyager/{z}/{x}/{y}{r}.png/>
                                   (hardcoded; no key, no env var, no fallback;
                                    attribution claims OSM while URL is CARTO)
```

The URL has been hardcoded since the file was introduced (git blame, `455c702`);
it has never read an environment variable.

Second, lesser-known occurrence of the same defect: the AI dashboard's
Orchestration details drawer mini-map (`OrchestrationDetailsDrawer.jsx:646-648`)
hardcodes `dark_all` with no key — it carries the same watermark whenever that
drawer opens.

## 6. Configuration trace

- `frontend/.env` contains only `VITE_API_URL`. No `VITE_MAP_TILE_URL`, no
  `VITE_GOOGLE_MAPS_API_KEY`, no CARTO key.
- `VehicleLocationMap.jsx` ignores environment variables entirely.
- `LiveMapContainer.jsx:30-37` (the working maps) reads `VITE_MAP_TILE_URL` /
  `VITE_MAP_TILE_ATTRIBUTION` / `VITE_MAP_TILE_SUBDOMAINS` and falls back to
  keyless OpenStreetMap.
- `frontend/.env.example` advertised CARTO dark tiles with an outdated
  `?api_key=` parameter (CARTO's current parameter is `?key=`).

Status confidence:
- **CONFIRMED** — CARTO watermarks keyless anonymous raster tiles (CARTO
  Basemap FAQ; CARTO Basemap Terms §"visible watermark"; Home Assistant
  #53800, Aug 2026; project's own `docs/reports/OPERATIONS_MAP_REBUILD_REPORT.md`.
  §Addendum:every anonymous dark tile stamped "API KEY REQUIRED").
- **CONFIRMED** — `VehicleLocationMap.jsx` sends keyless requests to that
  endpoint and has no fallback.
- **CONFIRMED** — the working maps use keyless OSM, which serves clean tiles.
- **UNVERIFIED** — the exact secondary text "positron" from the screenshot; no
  repository string matches it. Immaterial to the fix.

## 7. Comparison with working maps

| Surface | Component | Provider | Status |
|---|---|---|---|
| Overview (`/dashboard`) | `LiveMapContainer` | OSM (env-driven) | works |
| Live Operations (`/live-map`) | `LiveMapContainer` | OSM (env-driven) | works |
| AI Insights (`/xai`) | `LiveMapContainer` | OSM (env-driven) | works |
| **Fleet Locations (`/drivers`)** | **`VehicleLocationMap`** | **CARTO voyager (keyless)** | **fails** |
| AI drawer mini-map | `OrchestrationDetailsDrawer` | CARTO dark_all (keyless) | fails (same cause) |

Google Maps would be used by `LiveMapContainer` only when
`VITE_GOOGLE_MAPS_API_KEY` is set; it is not.

## 8. Root cause

External provider change. CARTO retired anonymous use of its raster basemaps and
now stamps every keyless tile request with a repeated diagonal
"API KEY REQUIRED" watermark. The Fleet Locations map was the one primary map
that bypassed the project's working provider (keyless OSM) by hardcoding the
CARTO voyager URL with no key and no fallback.

## 9. Why the current implementation fails

1. `VehicleLocationMap.jsx:82` hardcodes a CARTO basemap URL.
2. CARTO now requires an API key for raster basemap requests.
3. No key is attached (`?key=`), so CARTO returns 200 PNG tiles with the
   watermark baked in.
4. The component never consulted `VITE_MAP_TILE_URL` and has no OSM fallback,
   unlike the three working maps.

## 10. Classification

**External-provider issue**, surfaced by a **frontend hardcode** that bypassed
the app's own configurable, working provider. Not a backend issue, not a CSS
issue, not a token problem, not a Leaflet misconfiguration.

## 11. Recommended fix (implemented)

Share the working provider through one configuration point:

- New `frontend/src/utils/tileConfig.js` exporting `TILE_URL`, `TILE_ATTRIBUTION`,
  `TILE_SUBDOMAINS`, defaulting to keyless OpenStreetMap and read from
  `VITE_MAP_TILE_*` (mirrors `LiveMapContainer.jsx` exactly).
- `VehicleLocationMap.jsx` now renders `<TileLayer url={TILE_URL} …>`.
- `OrchestrationDetailsDrawer.jsx` (same root cause) switches to the same config.
- `frontend/.env.example` documents the `?key=` parameter and the watermark.

No API key required. All markers, popups, center/zoom, filters and refresh are
untouched (the marker layer is an independent SVG overlay).

## 12. Alternative fix

Keep CARTO: request a free publishable key from `carto.com/basemaps/apikey`,
then set
`VITE_MAP_TILE_URL=https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=YOUR_KEY`
(plus `VITE_MAP_TILE_SUBDOMAINS=abcd`, `VITE_MAP_TILE_TREATMENT=native`). This
also upgrades every map at once since all now read the same env vars.

## 13. Risk of each fix

| Fix | Risk | Notes |
|---|---|---|
| OSM default (recommended) | LOW | Provider already used and proven by the three working pages; single-line change per component; no secrets. Respect OSM tile usage policy for heavy production. |
| CARTO key alternative | MEDIUM | CARTO states raster basemaps are being **retired** ("see: migrate to vector"); key terms/attribution obligations; near-term lifecycle risk. A key is free within 5M tiles/month. |
| Vector-basemap rewrite (MapLibre) | HIGH | New architecture, new dependency, out of scope. |

## 14. Whether the fix affects other maps

No. `LiveMapContainer.jsx` (Overview / Live Operations / AI Insights) is
untouched and still resolves its own identical defaults. The only maps that
changed are the two that were actually broken.

## 15. Whether an API key is necessary

No. Keyless OpenStreetMap is proven working in this application. A CARTO key is
the *only* path that needs one — and CARTO's raster service is being retired, so
it is not recommended.

---

## Validation

| Check | Result |
|---|---|
| `VehicleLocationMap.jsx` tile URL resolves to keyless OSM / env override | ✓ |
| `OrchestrationDetailsDrawer.jsx` same | ✓ |
| Marker / popup / filter / refresh logic untouched | ✓ |
| `LiveMapContainer.jsx` untouched | ✓ |
| oxlint clean | ✓ |
| vite build clean | ✓ |