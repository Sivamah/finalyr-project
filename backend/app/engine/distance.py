import math
from typing import List, Tuple


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return c * 6371


def create_distance_matrix(locations: List[Tuple[float, float]]) -> List[List[float]]:
    matrix = []
    for i in range(len(locations)):
        row = []
        for j in range(len(locations)):
            if i == j:
                row.append(0.0)
            else:
                row.append(haversine(
                    locations[i][0], locations[i][1],
                    locations[j][0], locations[j][1],
                ))
        matrix.append(row)
    return matrix


def create_time_matrix(distance_matrix: List[List[float]], avg_speed_kmh: float = 30.0) -> List[List[float]]:
    time_matrix = []
    for row in distance_matrix:
        time_row = [(dist / avg_speed_kmh) * 60.0 for dist in row]
        time_matrix.append(time_row)
    return time_matrix
