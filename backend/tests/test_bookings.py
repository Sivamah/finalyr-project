"""Phase 9 — Booking Tests (Ride, Food, Parcel)"""

from tests.conftest import auth_header


RIDE_DATA = {
    "pickup_address": "Gandhipuram, Coimbatore",
    "drop_address": "Peelamedu, Coimbatore",
    "pickup_lat": 11.0168,
    "pickup_lng": 76.9558,
    "drop_lat": 11.0250,
    "drop_lng": 76.9700,
    "distance_km": 3.5,
    "estimated_fare": 75.0,
}

FOOD_DATA = {
    "restaurant_name": "Pizza Palace",
    "restaurant_address": "RS Puram, Coimbatore",
    "restaurant_lat": 11.0000,
    "restaurant_lng": 76.9600,
    "delivery_address": "Sitra, Coimbatore",
    "delivery_lat": 11.0100,
    "delivery_lng": 76.9200,
    "order_description": "2x Margherita Pizza, 1x Garlic Bread",
    "distance_km": 5.2,
    "estimated_fare": 70.0,
}

PARCEL_DATA = {
    "sender_name": "John Doe",
    "sender_phone": "9876543210",
    "pickup_address": "Saibaba Colony, Coimbatore",
    "pickup_lat": 11.0200,
    "pickup_lng": 76.9400,
    "recipient_name": "Jane Doe",
    "recipient_phone": "9876543211",
    "drop_address": "Singanallur, Coimbatore",
    "drop_lat": 11.0050,
    "drop_lng": 77.0000,
    "parcel_size": "Small",
    "distance_km": 10.0,
    "weight_kg": 2.5,
    "description": "Documents",
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
        assert res.json()["parcel_size"] == "Small"


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
