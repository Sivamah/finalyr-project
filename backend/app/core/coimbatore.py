"""
Coimbatore city bounding box and validation utilities.
"""

from fastapi import HTTPException

COIMBATORE_BOUNDS = {
    "min_lat": 10.95,
    "max_lat": 11.15,
    "min_lng": 76.85,
    "max_lng": 77.05,
}

COIMBATORE_CENTER = {"lat": 11.0168, "lng": 76.9558}

def is_in_coimbatore(lat: float, lng: float) -> bool:
    return (
        COIMBATORE_BOUNDS["min_lat"] <= lat <= COIMBATORE_BOUNDS["max_lat"]
        and COIMBATORE_BOUNDS["min_lng"] <= lng <= COIMBATORE_BOUNDS["max_lng"]
    )

def validate_coimbatore_location(lat: float, lng: float, location_name: str = "Location"):
    if not is_in_coimbatore(lat, lng):
        raise HTTPException(
            status_code=400,
            detail=f"{location_name} is outside Coimbatore. Service is currently available only in Coimbatore."
        )
