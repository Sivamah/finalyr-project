# Portfolio & Career Profile Content

## 1. Resume Bullet Points
* **AI-Powered Unified Mobility and Delivery System** | *Full Stack Developer & Systems Architect*
  * Architected a full-stack platform (FastAPI, React, PostgreSQL) that unifies ride-hailing, food, and parcel delivery, with the adaptive DMFE raising vehicle utilization by +3.3–5.8% and delivering +5–17% fuel/CO2 savings across simulated 50–500 request workloads.
  * Engineered a Dynamic Multi-Service Feasibility Engine (DMFE) integrating Google OR-Tools to solve real-time, constraint-heavy Vehicle Routing Problems (VRP), achieving a 42.9–83.3% batching rate and a 100% dispatch rate in closed-loop learning.
  * Implemented an Explainable AI (XAI) module that translates combinatorial matrix optimizations into human-readable text, providing administrators with transparent algorithmic decision logic.
  * Built live geospatial visualization of the fleet map via REST polling (2.5–15 s) of simulated driver/vehicle positions over the Google Maps API.
  * Secured and deployed the application via Vercel and Render, utilizing Pytest, Playwright, code-splitting (React.lazy), and robust middleware (JWT, XSS headers).

## 2. LinkedIn Post Draft
🚀 **I’m thrilled to showcase my Final Year Engineering Project:** An AI-Powered Unified Mobility and Delivery System! 

Current platforms like Uber and DoorDash operate in silos, leading to massive inefficiencies—drivers returning empty-handed, worse traffic, and higher emissions. I built a platform to fix this. 

Using **FastAPI**, **React**, and **Google OR-Tools**, I developed a *Dynamic Multi-Service Feasibility Engine (DMFE)*. The algorithm mathematically proves if a driver can pick up a parcel along a passenger's route without violating strict time constraints (SLAs), drastically reducing "deadhead" miles. 

**Key Technical Achievements:**
✅ Polymorphic SQLAlchemy database handling heterogeneous requests.
✅ Solved the Vehicle Routing Problem (VRP) in real-time.
✅ Live fleet map via HTTP polling (2.5–15 s) of simulated positions on Google Maps.
✅ **Explainable AI (XAI)** layer translating distance matrices into readable explanations.

**Engineering validation:** hardened through a 17-dimension readiness pass —
**92.6/100** (+3.6 vs baseline), **138 automated tests**, and XAI query latency
reduced from >300 s to ≈1.2 s on a 12,688-request database (all frozen in
`docs/reports/FINAL_FREEZE_CHECK.md`).

Check out the full repository and architecture here: [Link to GitHub]
#SoftwareEngineering #FastAPI #React #AI #Optimization #OperationsResearch #GigEconomy

## 3. GitHub README "About" Section Summary
A production-grade, microservice-inspired monolith that merges Passenger, Food, and Parcel delivery networks. Driven by a Python-based Operations Research engine (DMFE), it intelligently batches cross-domain payloads to maximize driver efficiency and minimize carbon emissions. Built with FastAPI, React, PostgreSQL, and Google Maps API. Includes comprehensive Pytest suites, Playwright E2E automation, and production-ready CI/CD configurations.
