# AI-Powered Unified Mobility and Delivery System Using Dynamic Multi-Service Feasibility Engine

**Abstract**— Modern urban logistics suffer from network fragmentation. Ride-hailing, food delivery, and courier services operate in mutually exclusive silos, resulting in sub-optimal vehicle utilization, increased traffic congestion, and excess carbon emissions. This paper proposes a novel framework: the AI-Powered Unified Mobility and Delivery System. By abstracting transport requests into a unified geographic payload, the system utilizes a Dynamic Multi-Service Feasibility Engine (DMFE) to solve a constraint-heavy variant of the Vehicle Routing Problem (VRP). Utilizing Google OR-Tools and Explainable AI (XAI), the DMFE clusters heterogeneous payloads (e.g., matching a passenger ride with a concurrent parcel delivery) without violating strict Service Level Agreements (SLAs). In deterministic closed-loop simulations, the adaptive DMFE increased vehicle utilization by 3.3–5.8%, fuel savings by 5–17%, and CO2 savings by 5–17% relative to a static DMFE across workloads of 50–500 concurrent requests, while reducing unassigned trips by 1–3% at high volume — at the cost of a 2–5% increase in average delay in some workloads and up to a 2x growth in pipeline wall time driven by batch-formation cost.

**Keywords**— Vehicle Routing Problem, Gig Economy, Urban Logistics, Explainable AI, OR-Tools, Multi-Service Batching.

---

## I. INTRODUCTION
The rise of the on-demand economy has populated urban centers with millions of independent contractors fulfilling micro-tasks. However, the software platforms orchestrating these tasks are heavily fragmented. A driver transporting a passenger across a city often returns empty, completely unaware of a parcel requiring delivery along their return route. This inefficiency represents a massive loss of economic potential and environmental sustainability. 

## II. LITERATURE REVIEW
Traditional approaches to the Vehicle Routing Problem (VRP) focus on static, homogeneous payloads. [Insert Citation 1]. Recent advancements in dynamic routing (Dynamic VRP) adapt to real-time requests, but remain confined to single-domain applications like pure ride-sharing (e.g., UberPool) [Insert Citation 2]. Cross-domain batching involving disparate constraints (human passenger comfort vs. food thermal decay) remains largely unexplored in commercial applications due to computational complexity.

## III. PROBLEM STATEMENT
To develop a real-time, unified platform capable of processing heterogeneous transport requests (Passenger, Food, Parcel) and optimally assigning them to a single fleet of drivers without violating the distinct temporal and spatial constraints of any individual payload.

## IV. PROPOSED METHODOLOGY

### A. System Architecture
The proposed system utilizes a microservice-inspired monolithic architecture built on FastAPI and React. A central PostgreSQL database employs polymorphic relationships to store generic `Bookings`. 

### B. Dynamic Multi-Service Feasibility Engine (DMFE)
The DMFE acts as the brain of the platform. It operates in two phases:
1. **Geospatial Pre-filtering**: Using Haversine distance heuristics, the engine drops combinations that exceed a baseline bounding box.
2. **Combinatorial Optimization**: The engine leverages Google OR-Tools. It constructs a distance matrix using the Google Maps API and solves the traveling salesperson problem (TSP) for the clustered nodes.

### C. Mathematical Model
Let $R$ be the set of requests, where $r_i \in R$ possesses a pickup node $P_i$, drop-off node $D_i$, and a maximum allowable delay penalty $\delta_i$. 
The objective function minimizes total distance $D$:
$$ \text{min} \sum_{i,j} d_{ij} x_{ij} $$
Subject to the SLA constraint for all batched payloads:
$$ t_{actual}(r_i) \leq t_{direct}(r_i) \times (1 + \delta_i) $$

## V. EXPERIMENTAL RESULTS
Deterministic simulations modeled a 10km x 10km urban grid with workloads of 50, 100, 250 and 500 concurrent heterogeneous requests, each repeated over 5 seeds (3 at volume 500). The adaptive DMFE (learned thresholds, learned corridor multipliers) was compared against a static DMFE (fixed thresholds). Full tables are in `ieee_tables.md` / `ieee_tables.tex`, generated from `evaluation/results/`.

Table 1 (headline delivery metrics, static vs adaptive):

| Metric (single pass) | W=50 | W=100 | W=250 | W=500 |
|---|---|---|---|---|
| Vehicle utilisation Δ | +4.1% | +3.8% | +3.3% | +5.8% |
| Fuel saved Δ | +16.8% | +5.3% | +13.2% | +9.8% |
| CO2 saved Δ | +16.6% | +5.2% | +13.2% | +9.9% |
| Unassigned Δ | 0 | 0 | −2.7% | −1.0% |
| Avg delay Δ | +2.7% | −0.6% | −5.3% | +3.2% |

Table 2 (efficiency & timeline): batching rate is 42.9–83.3% (adaptive +2.8–3.5% at low volume, parity at high volume); avg delay is 4.3–5.4 minutes in both variants (the same measure whose deltas appear in Table 1); adaptive raises processing cost from +9.5% ms/req (W=50) to +84.9% (W=500), with pipeline wall time rising from 0.92s to 7.36s.

Table 3 (stage share): batch formation dominates the adaptive pipeline at high volume — 57.9% of wall time at W=500 vs 31.5% static; route optimisation is 1.4–7.7% and never the bottleneck.

Table 4 (closed-loop learning): the dispatch rate stays at 100% in both arms at every workload — that is, every generated request was successfully assigned a driver and vehicle. It is a dispatch-success rate, not a measure of trips that ran to completion. Learning refits parameters on days 1–4 (corridor multipliers 1.05–1.25) and reduces on-arm delay error at W=50 (1.41→0.34 min) and W=100 (0.96→0.81 min); at W=250/500 on-arm delay error is flat (≈1.0–1.1 min, no better than the OFF arm).

## VI. DISCUSSION
The integration of Explainable AI (XAI) was critical in validating the DMFE's outputs. By translating mathematical distance matrices into natural language, human operators could easily audit the batching logic: in audited runs, the stored adaptive rationale (compatibility score, decision confidence, signed factor contributions, batch-quality score vs its threshold) matches an independent recomputation from recorded state (e.g. CS 90.90 recomputed to 90.70, decision confidence 68.0% as stored). Attribution is therefore reproducible, not decorative.

Three honest findings temper the headline gains. First, adaptivity buys utilization and fuel-savings mostly at low-to-moderate volume; at W=500 the gap narrows because the static arm already saturates batching (83.3% for both). Second, the latency cost of adaptivity is real: batch formation, not route optimisation, is the bottleneck (up to 58% of wall time at W=500), and learning adds little when corridors saturate at high volume. Third, the system's reliance on real-time traffic data exposes a vulnerability; sudden traffic anomalies could cause a batched trip to violate the stringent SLA of a passenger ride.

## VII. LIMITATIONS
- Deterministic single-pass simulation: repeated seeds vary RNG only; reported means/std are descriptive, not significance tests.
- Learning is inert below the 60-driver tracking threshold (W=50) and flat at W=500; "adaptive wins" claims therefore hold for 100–250-request workloads.
- The live-tracking map renders seeded simulator positions polled over REST; it is not GPS and not a push channel (no WebSocket).
- Avg completion time was reported from real trip records (completed-at minus created-at); a previously duplicated metric was removed because it double-counted processing time.
- Passenger waiting time is not measured independently. The harness records only the trip delay produced by the route model (`Trip.max_delay_min`); the driver's ETA to the first pickup is not persisted on the trip record, so dispatch-to-pickup waiting cannot be reconstructed. An earlier "average waiting time" row was withdrawn because it was computed from the same field as average delay and therefore reported one measurement twice.
- Reported rates are dispatch rates: a request counts as served once it reaches `Assigned`. Trip execution is simulated, so completion is not an independently observed outcome.
- Batch formation is O(pairs) with no caching; large fleets or real-time feeds require caching/parallelisation (see `12_Performance_Optimization_Report.md`).

## VIII. CONCLUSION & FUTURE SCOPE
The Unified Mobility and Delivery System successfully demonstrates that cross-domain batching is computationally feasible — with utilization and sustainability gains between 3% and 17% across workloads, an auditable XAI rationale, and a 100% dispatch rate in closed-loop learning. Future work will focus on caching and parallelising batch formation, integrating Machine Learning for predictive driver pre-positioning, and implementing dynamic pricing models to incentivize passenger-parcel batching.
