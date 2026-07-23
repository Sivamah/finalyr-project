import math
from typing import List, Tuple

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def create_distance_matrix(locations: List[Tuple[float, float]]) -> List[List[float]]:
    """
    Creates a distance matrix for a list of (lat, lng) coordinates.
    Returns a 2D array where matrix[i][j] is the distance from location i to location j in km.
    """
    matrix = []
    for i in range(len(locations)):
        row = []
        for j in range(len(locations)):
            if i == j:
                row.append(0.0)
            else:
                dist = haversine(locations[i][0], locations[i][1], locations[j][0], locations[j][1])
                row.append(dist)
        matrix.append(row)
    return matrix

def create_time_matrix(distance_matrix: List[List[float]], avg_speed_kmh: float = 30.0) -> List[List[float]]:
    """
    Converts a distance matrix (in km) to a time matrix (in minutes) 
    assuming a constant average speed.
    """
    time_matrix = []
    for row in distance_matrix:
        time_row = [(dist / avg_speed_kmh) * 60.0 for dist in row]
        time_matrix.append(time_row)
    return time_matrix
