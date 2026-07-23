"""Phase 9 — DMFE Tests"""

from .conftest import auth_header

class TestDMFE:
    def test_run_optimization_no_requests(self, client, admin_token):
        res = client.post(
            "/api/dmfe/evaluate",
            headers=auth_header(admin_token)
        )
        assert res.status_code == 200
        assert res.json()["batches_created"] == 0

    def test_run_optimization_with_requests(self, client, admin_token, customer_token):
        # Create a ride booking
        ride_data = {
            "pickup_address": "A", "drop_address": "B",
            "pickup_lat": 12.9, "pickup_lng": 77.5,
            "drop_lat": 12.91, "drop_lng": 77.51,
            "distance_km": 2.0, "estimated_fare": 100
        }
        client.post("/api/bookings/ride", json=ride_data, headers=auth_header(customer_token))

        # Create a food booking
        food_data = {
            "restaurant_name": "R", "restaurant_address": "C",
            "restaurant_lat": 12.92, "restaurant_lng": 77.52,
            "delivery_address": "D", "delivery_lat": 12.93, "delivery_lng": 77.53,
            "distance_km": 1.5, "estimated_fare": 50,
            "items_json": "[]"
        }
        client.post("/api/bookings/food", json=food_data, headers=auth_header(customer_token))

        # Run DMFE
        res = client.post(
            "/api/dmfe/evaluate",
            headers=auth_header(admin_token)
        )
        assert res.status_code == 200
        assert res.json()["batches_created"] > 0

    def test_list_decisions(self, client, admin_token):
        res = client.get("/api/dmfe/decisions", headers=auth_header(admin_token))
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_get_single_decision_not_found(self, client, admin_token):
        res = client.get("/api/dmfe/decisions/9999", headers=auth_header(admin_token))
        assert res.status_code == 404
