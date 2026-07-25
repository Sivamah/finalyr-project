"""Phase 9 — DMFE Tests"""

from tests.conftest import auth_header

class TestDMFE:
    COIMBATORE_RIDE = {
        "pickup_address": "Gandhipuram, Coimbatore",
        "drop_address": "Peelamedu, Coimbatore",
        "pickup_lat": 11.0168, "pickup_lng": 76.9558,
        "drop_lat": 11.0250, "drop_lng": 76.9700,
        "distance_km": 2.0, "estimated_fare": 100
    }

    COIMBATORE_FOOD = {
        "restaurant_name": "R", "restaurant_address": "RS Puram, Coimbatore",
        "restaurant_lat": 11.0000, "restaurant_lng": 76.9600,
        "delivery_address": "Sitra, Coimbatore",
        "delivery_lat": 11.0100, "delivery_lng": 76.9200,
        "distance_km": 1.5, "estimated_fare": 50,
        "items_json": "[]"
    }

    def test_run_optimization_no_requests(self, client, admin_token):
        res = client.post(
            "/api/dmfe/evaluate",
            headers=auth_header(admin_token)
        )
        assert res.status_code == 200
        assert "batches_created" in res.json()

    def test_run_optimization_with_requests(self, client, admin_token, customer_token):
        client.post("/api/bookings/ride", json=self.COIMBATORE_RIDE, headers=auth_header(customer_token))
        client.post("/api/bookings/food", json=self.COIMBATORE_FOOD, headers=auth_header(customer_token))

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
