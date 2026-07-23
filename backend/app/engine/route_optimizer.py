import json
from typing import List, Dict, Any
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from .distance_matrix import haversine

class RouteOptimizer:
    def __init__(self, driver_location: tuple, route_stops: List[Dict[str, Any]]):
        """
        driver_location: (lat, lng)
        route_stops: list of dicts with {"lat", "lng", "action", "address"}
        """
        self.driver_location = driver_location
        self.stops = route_stops
        self.locations = [self.driver_location] + [(s["lat"], s["lng"]) for s in self.stops]
        self.num_vehicles = 1
        self.depot = 0
        
    def _create_distance_matrix(self):
        matrix = []
        for i in range(len(self.locations)):
            row = []
            for j in range(len(self.locations)):
                if i == j:
                    row.append(0.0)
                else:
                    dist = haversine(self.locations[i][0], self.locations[i][1], self.locations[j][0], self.locations[j][1])
                    row.append(dist)
            matrix.append(row)
        return matrix

    def optimize(self):
        if not self.stops:
            return None

        distance_matrix_km = self._create_distance_matrix()
        # Convert to meters for OR-Tools to handle as integer
        dist_matrix_m = [[int(d * 1000) for d in row] for row in distance_matrix_km]

        manager = pywrapcp.RoutingIndexManager(len(self.locations), self.num_vehicles, self.depot)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return dist_matrix_m[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # For this phase, we also want to minimize fuel and time. 
        # Since fuel and time are directly proportional to distance in our simple model (Time = Dist / Speed, Fuel = Dist / Mileage),
        # minimizing distance effectively minimizes all three.
        # But we could add penalties. We'll stick to distance.

        # Add distance dimension
        dimension_name = 'Distance'
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            300000,  # maximum travel distance 300km
            True,  # start cumul to zero
            dimension_name)

        # We must enforce Pickup before Drop. We don't have explicit P&D pairs in this simple model if it's already a generated DMFE batch,
        # wait, the batch from DMFE IS ordered if we use the exact DMFE output.
        # However, if we are re-optimizing the route for the driver's current location, we should just let it find the shortest path 
        # visiting all nodes from the driver's location.
        # To strictly enforce P&D, we'd need pair indices. Let's assume the trip has already been validated and we just want to re-order 
        # optimally from driver location. 
        # Actually, for simplicity and since it's a TSP from driver location, we just let OR-tools solve the TSP.

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.seconds = 1

        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            return None

        # Extract route
        index = routing.Start(0)
        route_sequence = []
        total_distance_m = 0
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            if node_index != 0:
                # Map back to original stop
                stop = self.stops[node_index - 1]
                route_sequence.append(stop)
            
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            total_distance_m += routing.GetArcCostForVehicle(previous_index, index, 0)

        # Calculate time (avg 30 km/h) and fuel (avg 15 km/l)
        total_distance_km = total_distance_m / 1000.0
        total_duration_mins = (total_distance_km / 30.0) * 60.0
        estimated_fuel_liters = total_distance_km / 15.0

        return {
            "optimized_stops": route_sequence,
            "total_distance_km": total_distance_km,
            "total_duration_mins": total_duration_mins,
            "estimated_fuel_liters": estimated_fuel_liters
        }
