# Viva Voce Preparation Guide

## 1. Core Project Logic
**Q: What is the primary problem your project solves?**
A: It solves the fragmentation and inefficiency in urban logistics by unifying ride-hailing and delivery networks, reducing empty miles and carbon emissions through cross-domain batching.

**Q: What is the DMFE?**
A: The Dynamic Multi-Service Feasibility Engine. It's an algorithm that evaluates pending requests (ride, food, parcel) and clusters them into single, optimized vehicle trips using geospatial pre-filtering and Google OR-Tools.

**Q: How do you ensure a passenger isn't delayed by a food delivery?**
A: The DMFE mathematically enforces Service Level Agreement (SLA) constraints. If batching a food delivery adds more than a 5% time penalty to the passenger's direct route, the optimization engine rejects the batch.

## 2. Artificial Intelligence & Algorithms
**Q: Where is the "AI" in your project?**
A: The AI exists in two layers: Combinatorial Optimization (solving the NP-Hard Vehicle Routing Problem via OR-Tools) and Explainable AI (XAI), which translates the mathematical decision boundaries of the optimizer into natural language for administrators.

**Q: What is the Vehicle Routing Problem (VRP)?**
A: VRP is a combinatorial optimization and integer programming problem seeking to service a number of customers with a fleet of vehicles while minimizing distance or cost. It is a generalization of the Traveling Salesperson Problem (TSP).

## 3. Backend (FastAPI & Python)
**Q: Why did you choose FastAPI over Django or Flask?**
A: FastAPI is built on Starlette and Pydantic, making it inherently asynchronous and incredibly fast. It automatically generates Swagger documentation and uses Python type hints for data validation, which was crucial for handling complex, nested JSON objects in the booking and OR-Tools modules.

**Q: How are you securing the backend?**
A: We use JWT (JSON Web Tokens) for stateless authentication, bcrypt for password hashing, and custom middleware to enforce strict CORS origins and HTTP security headers (like XSS protection and HSTS).

## 4. Frontend (React)
**Q: What is React `lazy()` and why did you use it?**
A: `React.lazy()` enables code-splitting. Instead of loading the entire application bundle on the first visit, it dynamically loads components (like the Admin Dashboard) only when the user navigates to them, significantly improving initial load performance.

**Q: How does the Live Tracking map work?**
A: It uses React Leaflet combined with the Google Maps API. The driver's location is pushed in real-time from the backend via WebSockets, and the React state updates the marker's latitude/longitude without reloading the page.

## 5. Database (PostgreSQL / SQLAlchemy)
**Q: How did you store three different types of bookings in the database?**
A: We used SQLAlchemy's Polymorphic Inheritance. A parent `BaseBooking` table stores common attributes (ID, status, price), while child tables (`RideBooking`, `FoodBooking`, `ParcelBooking`) store specific data. SQLAlchemy joins them automatically based on a `type` column.

## 6. Architecture & Deployment
**Q: Is your application production-ready?**
A: Yes. The frontend is deployed via Vercel with a `vercel.json` routing configuration, and the backend is deployed on Render via a `render.yaml` blueprint with a managed PostgreSQL database. All secrets are managed via environment variables.
