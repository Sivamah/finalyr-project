# Technical Documentation

## 1. Software Requirements Specification (SRS)
**Purpose**: The system provides a unified platform for passenger ride-hailing, food delivery, and parcel logistics, utilizing an AI engine to optimize driver allocation.
**Target Audience**: Urban commuters, Restaurants, Local Couriers, and Gig-economy Drivers.
**Functional Requirements**:
- Role-based authentication (Admin, Customer, Driver).
- Booking interfaces for three distinct service types.
- Algorithmic batching of compatible requests (DMFE).
- Real-time geospatial tracking via WebSockets.
- Data visualization and analytics dashboards.

## 2. System Design Document
- **Architecture**: Client-Server Model with RESTful JSON APIs and WebSocket channels.
- **Frontend**: React.js 19 + Vite. Tailwind CSS for styling. React Router for SPA navigation. Context API for global state management.
- **Backend**: FastAPI (Python 3). Uvicorn ASGI server. 
- **AI/OR Integration**: Google OR-Tools (Constraint Programming Solver) handles the Vehicle Routing Problem (VRP).

## 3. Database Schema
**Relational Database (PostgreSQL / SQLite)**
- `users`: id, full_name, email, password_hash, role, created_at
- `bookings` (Polymorphic Base): id, customer_id, type, status, distance_km, estimated_fare, created_at
  - `ride_bookings`: pickup_lat/lng, drop_lat/lng, pickup_address, drop_address
  - `food_bookings`: restaurant_lat/lng, delivery_lat/lng, items_json
  - `parcel_bookings`: pickup_lat/lng, drop_lat/lng, weight_kg, parcel_type
- `ai_decisions`: id, batch_group_id, decision_text, metrics_json, created_at

## 4. API Reference (Core Endpoints)
- `POST /api/auth/register` - Registers a new user.
- `POST /api/auth/login` - Authenticates and returns JWT.
- `POST /api/bookings/{type}` - Creates a ride, food, or parcel booking.
- `POST /api/dmfe/evaluate` - Triggers the optimization engine.
- `GET /api/analytics/summary` - Returns JSON aggregate statistics.
- `WS /api/ws/tracking/{trip_id}` - WebSocket for real-time location.

## 5. User Manual
**For Customers**:
1. Register and login as "Customer".
2. Navigate to the Dashboard. Select "Book a Ride", "Order Food", or "Send Parcel".
3. Enter locations using the Google Maps interface.
4. Track the assigned driver in real-time under the "Live Tracking" tab.

## 6. Administrator Manual
1. Login with Admin credentials.
2. The Dashboard displays system health, live trips, and total revenue.
3. Use the **Trip Scheduler** tab to monitor DMFE batches.
4. Use the **AI Insights** tab to read the Explainable AI (XAI) breakdown of algorithmic decisions.
5. In emergencies, force-update booking statuses via the control panel.

## 7. Developer Guide
- **Setup**: Clone the repo. Run `npm install` in `frontend/`. Setup a Python virtual environment in `backend/` and run `pip install -r requirements.txt`.
- **Environment Variables**: Requires `VITE_GOOGLE_MAPS_API_KEY` (frontend) and `SECRET_KEY` (backend).
- **Testing**: Run `pytest` for backend coverage and `npm run test` for frontend component validation. Playwright handles E2E tests in `frontend/e2e`.

## 8. Known Limitations & Engineering Decisions

### 8.1 SQLite foreign-key enforcement is OFF in the dev database
`backend/app/db/database.py::_sqlite_pragmas` enables WAL mode and `busy_timeout`
but deliberately does **not** enable `PRAGMA foreign_keys=ON`.
- **Rationale (decision):** enabling FK enforcement was staged, not immediate,
  because it must come after the delete handlers are made dependency-ordered and
  after the dev DB is audited for orphans (`Vehicle.current_driver_id` is a
  declared FK that is skipped in the SQLite schema for load-order reasons).
  Flipping it early risks breaking a live dev DB.
- **Mitigation:** ORM-level `cascade="all, delete"` on `Provider.vehicles` covers
  the primary delete path; REST delete handlers are being hardened to delete in
  dependency order (children → parent).
- **Status:** targeted enablement is planned as a gated post-fix step, verified
  by the full regression gate before and after.

### 8.2 Dataset uploads: XLSX/CSV/JSON parsed, `data_type` normalized
- `POST /api/orchestration/upload` accepts CSV, JSON and XLSX; an `.xlsx`
  workbook is parsed with `openpyxl` (first sheet, header row, `row_count`
  = data rows) and, for `data_type=vehicle`, feeds the same import path as
  CSV. A corrupt/empty workbook is rejected with an explicit `400` and no
  row is persisted.
- **History:** XLSX was originally rejected with a `400` (no parser present).
  `openpyxl>=3.1.0` was added in `requirements.txt` and the rejection
  replaced with verified parsing (see `tests/test_datasets_upload.py`).
- `data_type` token normalization: the UI submits capitalized names (e.g.
  `Vehicles`) while the import pipeline keys on lowercase tokens (e.g.
  `vehicle`). The upload endpoint now accepts case-insensitive `data_type`
  values so the vehicle-import workflow is reachable from the page.

### 8.3 Legacy `POST /api/orchestration/optimize` retired
Returns **HTTP 410 Gone**; the live workflow is analyze → run → results. Any
remaining `/optimize` mentions in historical reports are annotated as such
(see `docs/12_Performance_Optimization_Report.md`).
