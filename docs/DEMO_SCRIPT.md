# A-DMFE Live Demo Script (final, frozen state)

> Matches the frozen engineering state (92.6/100, FINAL_FREEZE_CHECK.md) and the
> verified results in `docs/04_IEEE_Paper_Draft.md` / `backend/evaluation/results/ieee_tables.md`.
> Two tracks: **A) automated, evidence-based** (reliable under pressure) and
> **B) interactive UI** (the visual walkthrough). Track A runs on throwaway
> databases so the development DB is never touched.

Prerequisites: Python venv at `backend/.venv`; `frontend/node_modules` installed.

---

## Track A — Automated engine demo (recommended as backup / numbers slide)

Everything runs against fresh isolated SQLite files in temp directories.

```powershell
# 1. End-to-end hardening soak (real HTTP, 17 checks)
cd D:\rapidoproject\backend
.\.venv\Scripts\python.exe scripts/e2e_hardening.py --requests 50
```

**Expected:** login OK → seeded fleet (drivers/vehicles) → `/api/dmfe/run` returns
`200` in ~1.5 s → trip/batch logging → `[PASS]` rows for all 17 checks →
second `/api/dmfe/run` creates **no new trips** (idempotent) →
`===== "N=50: 0 failure(s)" =====`.

```powershell
# 2. Demo-data isolation harness (demo_only filtering works end-to-end)
.\.venv\Scripts\python.exe scripts/verify_demo.py
```

**Expected:** login OK → `[A-DMFE Demo Scenario]` requests seeded →
`Analysis result: N batches created` → demo-tagged batches listed
→ `Verification complete.`

```powershell
# 3. Full verify gate (24 checks) — run once before the presentation day
.\.venv\Scripts\python.exe scripts/verify_all.py
```

**Expected:** all `PASS`, `24 passed, 0 failed, 1 skipped, 1 informational`.

> Timing note: XAI decision-filter queries are bounded to ≈1.2 s on the
> 12,688-request dev DB (previously >300 s) — see Slide 9.

---

## Track B — Interactive UI demo

### 0. Start the stack

```powershell
# Terminal 1 — backend (http://localhost:8000)
cd D:\rapidoproject\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Terminal 2 — frontend (http://localhost:5173)
cd D:\rapidoproject\frontend
npm run dev
```

The frontend calls the API at `http://localhost:8000/api` by default
(override with `VITE_API_URL`). UI refresh is **HTTP polling (2.5–15 s)** —
there is no WebSocket.

### 1. Login
- Open `http://localhost:5173` → `/login`.
- Seeded admin: `admin@aiorch.com` / `admin123` (created by the app lifespan).

### 2. Demonstration flow (≈6–8 minutes)

1. **`/live-map`** (2 min) — fleet markers, Active trips, route polylines, and
   per-trip confidence. Point out "(estimated)" badges where score-derived
   confidence is shown vs recorded engine confidence.
2. **`/xai` (AI Insights)** (2 min) — pick a dispatched trip; the replay shows
   compatibility score, decision confidence, signed factor contributions,
   batch-quality score vs threshold, and the trip code. Confidence with
   `confidence_fallback` is labelled "(estimated)".
3. **`/ai-orchestration`** (1.5 min) — hit **Run**: pending requests →
   batches → assigned trips. **Re-run the same selection** → HTTP **409**
   (requests already in an Active trip); no duplicate trips are created.
4. **`/dashboard`** (1 min) — utilization %, batching rate, fuel/CO2 KPIs;
   `/drivers` shows per-driver load.

### 3. API-only fallback (if the UI is slow)

```powershell
$body = '{"email":"admin@aiorch.com","password":"admin123"}'
$tok  = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/auth/login -Body $body
$h    = @{ Authorization = "Bearer $($tok.access_token)" }
# Live run + idempotent second run + XAI replay
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/dmfe/run -Headers $h -Body '{"limit":50}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/dmfe/run -Headers $h -Body '{"limit":50}'  # 409/0 new trips
Invoke-RestMethod -Method Get -Uri  http://localhost:8000/api/xai/explanations/1 -Headers $h
```

---

## Rehearsal checklist

- [ ] Track A run [1] returns `===== 50: 0 failure(s) =====` (repeat [3] for the full gate).
- [ ] Backend + frontend up; login works; API base reaches `:8000`.
- [ ] `/live-map` renders; XAI replay matches a real dispatched trip (trip code present).
- [ ] Re-run in `/ai-orchestration` shows the HTTP 409 conflict, no duplicate trips.
- [ ] Speakers have `docs/04_IEEE_Paper_Draft.md` + `06_Presentation_Outline.md` + the
      freeze reports on hand for Q&A.
- [ ] Keep `docs/reports/FINAL_HARDENING_REPORT.md` / `FINAL_FREEZE_CHECK.md` open on a
      third monitor for the "92.6/100, +3.6, +4.05%, freeze PASS" claims.

## Honest notes for Q&A
- Live map data is **seeded-simulator positions over REST polling**, not GPS/push.
- Research claims hold for **100–250-request workloads**; at W=500 adaptive≈static.
- Batch formation is the adaptive pipeline bottleneck at high volume (57.9% of wall
  time at W=500) — future caching/parallelization.