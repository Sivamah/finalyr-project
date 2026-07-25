"""Phase 9 — Admin Tests"""

from tests.conftest import auth_header, ADMIN_DATA


class TestAdminUsers:
    def test_list_users_as_admin(self, client, admin_token, customer_token):
        res = client.get(
            "/api/admin/users",
            headers=auth_header(admin_token),
        )
        assert res.status_code == 200
        assert isinstance(res.json(), list)
        assert len(res.json()) >= 2

    def test_list_users_as_customer(self, client, customer_token):
        res = client.get(
            "/api/admin/users",
            headers=auth_header(customer_token),
        )
        assert res.status_code in [401, 403]

    def test_change_role(self, client, admin_token):
        data = {
            "full_name": "Temp",
            "email": "temp@test.com",
            "phone": "9999999999",
            "password": "Pass",
            "role": "Customer"
        }
        res_reg = client.post("/api/auth/register", json=data)
        uid = res_reg.json()["id"]

        res = client.patch(
            f"/api/admin/users/{uid}/role",
            json={"role": "Driver"},
            headers=auth_header(admin_token),
        )
        assert res.status_code == 200


class TestAdminBookings:
    def test_list_all_bookings(self, client, admin_token):
        res = client.get(
            "/api/admin/bookings",
            headers=auth_header(admin_token),
        )
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    def test_force_status(self, client, admin_token, customer_token):
        ride_data = {
            "pickup_address": "Gandhipuram, Coimbatore",
            "drop_address": "Peelamedu, Coimbatore",
            "pickup_lat": 11.0168, "pickup_lng": 76.9558,
            "drop_lat": 11.0250, "drop_lng": 76.9700,
            "distance_km": 5, "estimated_fare": 100
        }
        res_ride = client.post("/api/bookings/ride", json=ride_data, headers=auth_header(customer_token))
        ride_id = res_ride.json()["id"]

        res = client.patch(
            f"/api/admin/bookings/ride/{ride_id}/status",
            json={"status": "Completed"},
            headers=auth_header(admin_token),
        )
        assert res.status_code == 200
