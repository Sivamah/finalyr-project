import json
import math
import random
from typing import List, Dict, Any, Optional
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from sqlalchemy.orm import Session
from app.db.models import Provider, Vehicle, SimulationRequest
from .distance import haversine, create_distance_matrix


class AIOrchestrator:
    def __init__(self, providers: List[Provider], vehicles: List[Vehicle], db: Session):
        self.providers = providers
        self.vehicles = vehicles
        self.db = db

    def _fetch_requests(self) -> List[Dict[str, Any]]:
        pending = (
            self.db.query(SimulationRequest)
            .filter(SimulationRequest.status == "Pending")
            .all()
        )
        requests = []
        for r in pending:
            provider = self.db.query(Provider).filter(Provider.id == r.provider_id).first()
            requests.append({
                "id": r.id,
                "type": r.request_type,
                "pickup_lat": r.pickup_lat,
                "pickup_lng": r.pickup_lng,
                "drop_lat": r.drop_lat,
                "drop_lng": r.drop_lng,
                "demand": r.demand,
                "provider_id": r.provider_id,
                "provider_name": provider.name if provider else "Unknown",
            })
        return requests

    def _build_vehicle_configs(self) -> List[Dict[str, Any]]:
        configs = []
        for v in self.vehicles:
            provider = self.db.query(Provider).filter(Provider.id == v.provider_id).first()
            configs.append({
                "id": v.id,
                "name": v.name,
                "provider_id": v.provider_id,
                "provider_name": provider.name if provider else "Unknown",
                "type": v.vehicle_type,
                "capacity": v.capacity,
                "cost_per_km": v.cost_per_km,
                "mileage": v.mileage_kmpl,
                "fuel_type": v.fuel_type,
            })
        return configs

    def run(self) -> List[Dict[str, Any]]:
        requests = self._fetch_requests()
        if not requests:
            return self._generate_simulated_results()

        vehicle_configs = self._build_vehicle_configs()
        if not vehicle_configs:
            return self._generate_simulated_results()

        batches = self._optimize_with_ortools(requests, vehicle_configs)
        return self._build_results(batches, requests, vehicle_configs)

    def _optimize_with_ortools(self, requests: List[Dict], vehicles: List[Dict]) -> List[Dict]:
        all_lats = []
        all_lngs = []
        for req in requests:
            all_lats.extend([req["pickup_lat"], req["drop_lat"]])
            all_lngs.extend([req["pickup_lng"], req["drop_lng"]])

        if all_lats and all_lngs:
            depot = (sum(all_lats) / len(all_lats), sum(all_lngs) / len(all_lngs))
        else:
            depot = (0.0, 0.0)

        locations = [depot]
        pickups_deliveries = []
        demands = [0]
        request_mapping = {}

        idx = 1
        for req in requests:
            locations.append((req["pickup_lat"], req["pickup_lng"]))
            locations.append((req["drop_lat"], req["drop_lng"]))
            pickups_deliveries.append([idx, idx + 1])
            demands.extend([req.get("demand", 1), -req.get("demand", 1)])
            request_mapping[idx] = req
            request_mapping[idx + 1] = req
            idx += 2

        num_vehicles = min(max(1, len(vehicles)), len(requests))
        if num_vehicles == 0:
            return []

        dist_matrix = create_distance_matrix(locations)
        dist_matrix_m = [[int(d * 1000) for d in row] for row in dist_matrix]

        manager = pywrapcp.RoutingIndexManager(len(locations), num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return dist_matrix_m[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        max_dist = max(100000, len(requests) * 30000)
        dimension_name = "Distance"
        routing.AddDimension(transit_callback_index, 0, max_dist, True, dimension_name)
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(max(500, 200 * len(requests)))

        for request in pickups_deliveries:
            pickup_index = manager.NodeToIndex(request[0])
            delivery_index = manager.NodeToIndex(request[1])
            routing.AddPickupAndDelivery(pickup_index, delivery_index)
            routing.solver().Add(
                routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index)
            )
            routing.solver().Add(
                distance_dimension.CumulVar(pickup_index) <=
                distance_dimension.CumulVar(delivery_index)
            )

        cap = [v["capacity"] for v in vehicles[:num_vehicles]]
        while len(cap) < num_vehicles:
            cap.append(4)

        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return demands[from_node] if from_node < len(demands) else 0

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index, 0, cap, True, "Capacity"
        )

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        )
        search_parameters.time_limit.seconds = 2

        solution = routing.SolveWithParameters(search_parameters)

        batches = []
        if solution:
            for vehicle_id in range(num_vehicles):
                index = routing.Start(vehicle_id)
                route = []
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    if node_index != 0 and node_index in request_mapping:
                        route.append(request_mapping[node_index])
                    index = solution.Value(routing.NextVar(index))
                if route:
                    unique_reqs = []
                    seen = set()
                    for r in route:
                        rid = r["id"]
                        if rid not in seen:
                            seen.add(rid)
                            unique_reqs.append(r)
                    if unique_reqs:
                        batches.append({
                            "vehicle_idx": vehicle_id,
                            "requests": unique_reqs,
                            "distance_m": solution.Min(
                                distance_dimension.CumulVar(routing.End(vehicle_id))
                            ) if routing.End(vehicle_id) is not None else 0,
                        })
        return batches

    def _build_results(self, batches: List[Dict], requests: List[Dict], vehicles: List[Dict]) -> List[Dict]:
        results = []
        for batch in batches:
            vehicle_idx = batch["vehicle_idx"]
            vehicle = vehicles[vehicle_idx] if vehicle_idx < len(vehicles) else vehicles[0]
            batch_reqs = batch["requests"]
            distance_m = batch["distance_m"]
            distance_km = distance_m / 1000.0

            direct_km = 0.0
            for r in batch_reqs:
                direct_km += haversine(r["pickup_lat"], r["pickup_lng"], r["drop_lat"], r["drop_lng"])

            saved_km = max(0.0, direct_km - distance_km)
            fuel_saved = saved_km / vehicle["mileage"] if vehicle["mileage"] > 0 else 0
            co2_saved = fuel_saved * 2.3
            cost = distance_km * vehicle["cost_per_km"]
            eta = (distance_km / 30.0) * 60.0
            score = min(100.0, max(0.0, 100.0 - (saved_km / max(direct_km, 0.1)) * 50.0 + 50.0))

            results.append({
                "request_count": len(batch_reqs),
                "provider_id": vehicle["provider_id"],
                "vehicle_id": vehicle["id"],
                "best_route": {
                    "distance_km": round(distance_km, 2),
                    "stops": [
                        {"lat": r["pickup_lat"], "lng": r["pickup_lng"], "action": "pickup"}
                        for r in batch_reqs
                    ] + [
                        {"lat": r["drop_lat"], "lng": r["drop_lng"], "action": "drop"}
                        for r in batch_reqs
                    ],
                },
                "chosen_provider": vehicle["provider_name"],
                "chosen_vehicle": vehicle["name"],
                "estimated_cost": round(cost, 2),
                "eta_mins": round(eta, 1),
                "fuel_saved_l": round(fuel_saved, 2),
                "distance_saved_km": round(saved_km, 2),
                "co2_saved_kg": round(co2_saved, 2),
                "optimization_score": round(score, 1),
                "explanation": {
                    "requests_batched": len(batch_reqs),
                    "direct_distance_km": round(direct_km, 2),
                    "optimized_distance_km": round(distance_km, 2),
                    "savings_percentage": round((saved_km / max(direct_km, 0.1)) * 100, 1) if direct_km > 0 else 0,
                    "vehicle_used": vehicle["name"],
                    "provider": vehicle["provider_name"],
                    "fuel_type": vehicle["fuel_type"],
                },
            })

            for r in batch_reqs:
                sim_req = self.db.query(SimulationRequest).filter(
                    SimulationRequest.id == r["id"]
                ).first()
                if sim_req:
                    sim_req.status = "Optimized"

        self.db.commit()
        return results

    def _generate_simulated_results(self) -> List[Dict]:
        results = []
        for i in range(min(len(self.vehicles), 5)):
            v = self.vehicles[i] if i < len(self.vehicles) else self.vehicles[0]
            provider = self.db.query(Provider).filter(Provider.id == v.provider_id).first()
            pname = provider.name if provider else "Unknown"
            dist_km = random.uniform(3.0, 15.0)
            direct_km = dist_km * random.uniform(1.2, 1.8)
            saved_km = direct_km - dist_km
            fuel_saved = saved_km / (v.mileage_kmpl or 15.0)
            co2_saved = fuel_saved * 2.3
            cost = dist_km * (v.cost_per_km or 10.0)
            eta = (dist_km / 30.0) * 60.0
            score = random.uniform(65.0, 98.0)

            results.append({
                "request_count": random.randint(2, 5),
                "provider_id": v.provider_id,
                "vehicle_id": v.id,
                "best_route": {
                    "distance_km": round(dist_km, 2),
                    "stops": [],
                },
                "chosen_provider": pname,
                "chosen_vehicle": v.name,
                "estimated_cost": round(cost, 2),
                "eta_mins": round(eta, 1),
                "fuel_saved_l": round(fuel_saved, 2),
                "distance_saved_km": round(saved_km, 2),
                "co2_saved_kg": round(co2_saved, 2),
                "optimization_score": round(score, 1),
                "explanation": {
                    "requests_batched": random.randint(2, 5),
                    "direct_distance_km": round(direct_km, 2),
                    "optimized_distance_km": round(dist_km, 2),
                    "savings_percentage": round((saved_km / direct_km) * 100, 1),
                    "vehicle_used": v.name,
                    "provider": pname,
                    "fuel_type": v.fuel_type,
                },
            })
        return results
