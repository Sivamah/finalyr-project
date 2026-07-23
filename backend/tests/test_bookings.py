"""Phase 9 — Booking Tests (Ride, Food, Parcel)"""

from .conftest import auth_header


RIDE_DATA = {
    "pickup_address": "MG Road, Bengaluru",
    "drop_address": "Whitefield, Bengaluru",
    "pickup_lat": 12.9716,
    "pickup_lng": 77.5946,
    "drop_lat": 12.9698,
    "drop_lng": 77.7500,
    "distance_km": 18.5,
    "estimated_fare": 250.0,
}

FOOD_DATA = {
    "restaurant_name": "Pizza Palace",
    "restaurant_address": "Indiranagar, Bengaluru",
    "restaurant_lat": 12.9784,
    "restaurant_lng": 77.6408,
    "delivery_address": "Koramangala, Bengaluru",
    "delivery_lat": 12.9352,
    "delivery_lng": 77.6245,
    "distance_km": 5.2,
    "items_json": '[{"name": "Margherita Pizza", "qty": 2, "price": 350}]',
    "estimated_fare": 70.0,
}

PARCEL_DATA = {
    "pickup_address": "HSR Layout, Bengaluru",
    "drop_address": "Electronic City, Bengaluru",
    "pickup_lat": 12.9116,
    "pickup_lng": 77.6474,
    "drop_lat": 12.8456,
    "drop_lng": 77.6603,
    "distance_km": 10.0,
    "weight_kg": 2.5,
    "parcel_type": "Document",
    "estimated_fare": 120.0,
}


class TestRideBooking:
    def test_create_ride(self, client, customer_token):
        res = client.post(
            "/api/bookings/ride",
            json=RIDE_DATA,
            headers=auth_header(customer_token),
        )
        assert res.status_code == 201
        body = res.json()
        assert body["pickup_address"] == RIDE_DATA["pickup_address"]
        assert body["status"] == "Pending"

    def test_create_ride_no_auth(self, client):
        res = client.post("/api/bookings/ride", json=RIDE_DATA)
        assert res.status_code in [401, 403]


class TestFoodBooking:
    def test_create_food(self, client, customer_token):
        res = client.post(
            "/api/bookings/food",
            json=FOOD_DATA,
            headers=auth_header(customer_token),
        )
        assert res.status_code == 201
        assert res.json()["restaurant_name"] == "Pizza Palace"


class TestParcelBooking:
    def test_create_parcel(self, client, customer_token):
        res = client.post(
            "/api/bookings/parcel",
            json=PARCEL_DATA,
            headers=auth_header(customer_token),
        )
        assert res.status_code == 201
        assert res.json()["parcel_type"] == "Document"


class TestBookingHistory:
    def test_unified_history(self, client, customer_token):
        # Create one booking first
        client.post("/api/bookings/ride", json=RIDE_DATA,
                     headers=auth_header(customer_token))
        res = client.get(
            "/api/bookings/history",
            headers=auth_header(customer_token),
        )
        assert res.status_code == 200
        assert isinstance(res.json(), list)
