# Final Year Project Presentation Outline (v2 — final, frozen state)

> Updated 2026-09-25 to match the frozen engineering state (92.6/100 scorecard,
> FINAL_HARDENING_REPORT / FINAL_FREEZE_CHECK) and the verified research numbers
> in `docs/04_IEEE_Paper_Draft.md` / `backend/evaluation/results/ieee_tables.md`.
> Live UI refreshes via **HTTP polling (2.5–15 s)**, not WebSockets.

## Slide 1: Title Slide
- **Title**: AI-Powered Unified Mobility and Delivery System
- **Subtitle**: Optimizing Urban Logistics with a Dynamic Multi-Service Feasibility Engine (DMFE)
- **Visual**: High-quality screenshot of the live dashboard.
- **Speaker Notes**: Introduce yourself, the project, and the core concept — one engine batches ride-hailing, food, and parcel requests into a single optimized trip.

## Slide 2: Problem Statement
- **Content**:
  - Fragmentation in gig-economy apps (Uber vs. DoorDash).
  - High "deadhead" (empty) miles and duplicated fleet miles.
  - Increased congestion and carbon footprint.
- **Speaker Notes**: A driver drops off a passenger and drives back empty, unaware of a parcel on the return route.

## Slide 3: The Solution
- **Content**: One platform abstracts Ride + Food + Parcel into a unified geographic payload.
- **Visual**: Funnel graphic: Ride + Food + Parcel → DMFE → 1 optimized trip.
- **Speaker Notes**: Introduce the DMFE; the app merges silos into one efficient network while respecting each payload's SLA.

## Slide 4: System Architecture
- **Content**: Client (React) ↔ API (FastAPI) ↔ DB (PostgreSQL) + DMFE (Google OR-Tools).
- **Visual**: High-level block diagram; add the XAI layer as a box feeding the admin UI.
- **Speaker Notes**: FastAPI chosen for async capability; OR-Tools solves the route model; murature is two-phase (geospatial pre-filter → combinatorial optimization).

## Slide 5: The DMFE Algorithm (Core Innovation)
- **Content**:
  - Geospatial pre-filtering (Haversine bounding).
  - Combinatorial optimization (Vehicle Routing Problem via OR-Tools).
  - SLA constraints (food stays hot, passenger not delayed beyond its bound).
- **Speaker Notes**: Not "group things that are close" — the constraint model proves time bounds won't be violated.

## Slide 6: Explainable AI (XAI) Integration
- **Content**: Why XAI — algorithms are black boxes.
- **Visual**: Screenshot of the AI Insights tab: compatibility score, decision confidence, signed factor contributions, batch-quality vs threshold.
- **Speaker Notes**: Reproducible attribution, not decorative text; replayed decisions carry the threshold in force at decision time.

## Slide 7: Demonstration Flow (Live Demo)
- **Action**: Switch to browser (`http://localhost:5173`).
- **Flow** (login: seeded `admin@aiorch.com` / `admin123`):
  1. `/live-map` — show Active trips, routes, per-trip confidence (with "(estimated)" markers where applicable).
  2. `/xai` (AI Insights) — pick a dispatched trip; replay shows compatibility score, confidence, factor breakdown, and trip code.
  3. `/ai-orchestration` — run a fresh analysis: pending requests → batches → assigned trips; note HTTP 409 when re-assigning the same requests.
  4. `/dashboard` — utilization, fuel/CO2, batching-rate KPIs.
- **Note**: map data is seeded simulator positions pulled over REST polling (2.5–15 s) — no WebSocket.

## Slide 8: Experimental Evaluation & Results
- **Content** (from `ieee_tables.md`, static vs adaptive DMFE, W=50–500):
  - Vehicle utilization Δ **+3.3% to +5.8%**; fuel saved **+5% to +17%**; CO2 saved **+5% to +17%**.
  - Batching rate **42.9–83.3%** (adaptive +2.8–3.5% at low volume, parity at high volume).
  - Unassigned **reduced** (−0.0 to −2.7%); **100% dispatch rate** in closed-loop learning.
  - Avg delay: ±3 minutes (one workload +2.7% to +3.2%) — the honest trade-off.
- **Speaker Notes**: Emphasize the latency/adaptivity trade-off — batch formation is the bottleneck at high volume, not routing.

## Slide 9: Security, Performance & Engineering Validation (Frozen State)
- **Content**:
  - Security: JWT, bcrypt, RBAC, security-headers middleware (CSP verified on API paths).
  - Performance: XAI decision-filter view **>300 s → ≈1.2 s** (bounded scans); batch formation N=100 ≈0.6 s; E2E soak N=100 in 3.2 s with all invariants.
  - Validation: **138 tests passing**, 5 verify harnesses, E2E **17/17** checks (idempotent re-runs, accounting closes, no duplicate trips).
- **Speaker Notes**: This is a production-releasable engineering state, not a prototype — a 17-dimension evidence scorecard rates the system at **92.6/100 (+3.6, +4.05%)** with a clean freeze check; no research logic was altered during hardening.

## Slide 10: Conclusion & Future Scope
- **Content**:
  - Solved the fragmentation problem: cross-domain batching is feasible and auditable.
  - Future: Predictive ML driver positioning, dynamic pricing, batch-formation caching/parallelization.
- **Speaker Notes**: Wrap up with commercial viability — higher utilization, lower emissions, driver earnings — and thank the evaluators.