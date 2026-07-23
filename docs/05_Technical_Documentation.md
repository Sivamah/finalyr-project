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
