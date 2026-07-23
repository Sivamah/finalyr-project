import json
from typing import List, Dict, Any
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from .distance_matrix import create_distance_matrix, create_time_matrix


class DMFE_Optimizer:
    def __init__(self, vehicles: List[Dict[str, Any]], requests: List[Dict[str, Any]]):
        """
        vehicles: List of driver dicts: {"id": 1, "lat": 12.9, "lng": 77.5, "capacity": 4, "type": "Passenger"}
        requests: List of request dicts: 
            {"id": "ride_1", "type": "ride", "pickup_lat": 12.91, "pickup_lng": 77.51, "drop_lat": 12.92, "drop_lng": 77.52, "demand": 1}
        """
        self.vehicles = vehicles
        self.requests = requests
        
        # Build node list: Node 0..N-1 are vehicles (dummy start/end for each)
        # We will use a dummy depot at index 0, and all vehicles start at their respective locations.
        # But to keep it simple for OR-Tools PDP:
        # Depot (0)
        # Pickups (1, 3, 5...)
        # Deliveries (2, 4, 6...)
        
        self.locations = [(0.0, 0.0)]  # Depot placeholder
        self.pickups_deliveries = []
        self.demands = [0]
        self.request_mapping = {}  # node index -> request info
        
        idx = 1
        for req in self.requests:
            self.locations.append((req["pickup_lat"], req["pickup_lng"]))
            self.locations.append((req["drop_lat"], req["drop_lng"]))
            
            pickup_idx = idx
            delivery_idx = idx + 1
            
            self.pickups_deliveries.append([pickup_idx, delivery_idx])
            
            self.demands.extend([req.get("demand", 1), -req.get("demand", 1)])
            
            self.request_mapping[pickup_idx] = {"req": req, "action": "pickup"}
            self.request_mapping[delivery_idx] = {"req": req, "action": "drop"}
            
            idx += 2
            
        # For simplicity, we assume all vehicles start and end at the depot (Node 0)
        # Real-world: vehicles start at their current GPS location.
        # We can simulate this by setting the distance from Depot to Node to be 0 for the first step, 
        # but let's just use standard VRP for the batching algorithm.
        self.num_vehicles = max(1, len(self.vehicles))
        
        # For academic purposes, if no vehicles are passed, we just use 1 default vehicle
        self.vehicle_capacities = [v.get("capacity", 4) for v in self.vehicles] if self.vehicles else [4]
        
    def solve(self) -> List[Dict[str, Any]]:
        if not self.requests:
            return []

        # Create distance matrix
        distance_matrix = create_distance_matrix(self.locations)
        # Convert to integers (meters) for OR-Tools
        dist_matrix_m = [[int(d * 1000) for d in row] for row in distance_matrix]

        # Create Routing Index Manager
        manager = pywrapcp.RoutingIndexManager(len(self.locations), self.num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        # Distance Callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return dist_matrix_m[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add Distance constraint to prevent infinite routes
        dimension_name = 'Distance'
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            100000,  # vehicle maximum travel distance (100 km)
            True,  # start cumul to zero
            dimension_name)
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100)

        # Define Transportation Requests
        for request in self.pickups_deliveries:
            pickup_index = manager.NodeToIndex(request[0])
            delivery_index = manager.NodeToIndex(request[1])
            routing.AddPickupAndDelivery(pickup_index, delivery_index)
            routing.solver().Add(
                routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index))
            routing.solver().Add(
                distance_dimension.CumulVar(pickup_index) <=
                distance_dimension.CumulVar(delivery_index))

        # Capacity Constraint
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return self.demands[from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            self.vehicle_capacities,  # vehicle maximum capacities
            True,  # start cumul to zero
            'Capacity')

        # Setting first solution heuristic
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)
        search_parameters.time_limit.seconds = 2  # Max 2 seconds to solve

        # Solve the problem
        solution = routing.SolveWithParameters(search_parameters)
        
        batches = []
        if solution:
            for vehicle_id in range(self.num_vehicles):
                index = routing.Start(vehicle_id)
                route = []
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    if node_index != 0:  # Skip depot
                        route.append(self.request_mapping[node_index])
                    index = solution.Value(routing.NextVar(index))
                
                # If vehicle has requests, form a batch
                if route:
                    batches.append({
                        "vehicle_id": self.vehicles[vehicle_id]["id"] if self.vehicles else None,
                        "route": route,
                        "distance_m": solution.Min(distance_dimension.CumulVar(routing.End(vehicle_id)))
                    })
                    
        return batches
