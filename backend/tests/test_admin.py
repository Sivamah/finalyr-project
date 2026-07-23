"""Phase 9 — Admin Tests"""

from .conftest import auth_header, ADMIN_DATA


class TestAdminUsers:
    def test_list_users_as_admin(self, client, admin_token, customer_token):
        res = client.get(
            "/api/admin/users",
            headers=auth_header(admin_token),
        )
        assert res.status_code == 200
        assert isinstance(res.json(), list)
        assert len(res.json()) >= 2  # At least admin and customer exist

    def test_list_users_as_customer(self, client, customer_token):
        res = client.get(
            "/api/admin/users",
            headers=auth_header(customer_token),
        )
        assert res.status_code in [401, 403]

    def test_change_role(self, client, admin_token):
        # Create a temp user
        data = {
            "full_name": "Temp",
            "email": "temp@test.com",
            "phone": "9999999999",
            "password": "Pass",
            "role": "Customer"
        }
        res_reg = client.post("/api/auth/register", json=data)
        uid = res_reg.json()["id"]

        res = client.put(
            f"/api/admin/users/{uid}/role",
            json={"role": "Driver"},
            headers=auth_header(admin_token),
        )
        assert res.status_code == 200
        assert res.json()["role"] == "Driver"


class TestAdminBookings:
    def test_list_all_bookings(self, client, admin_token):
        res = client.get(
            "/api/admin/bookings",
            headers=auth_header(admin_token),
        )
        assert res.status_code == 200
        data = res.json()
        assert "rides" in data
        assert "foods" in data
        assert "parcels" in data

    def test_force_status(self, client, admin_token, customer_token):
        # Create a ride
        ride_data = {
            "pickup_address": "A", "drop_address": "B",
            "pickup_lat": 1, "pickup_lng": 1, "drop_lat": 2, "drop_lng": 2,
            "distance_km": 5, "estimated_fare": 100
        }
        res_ride = client.post("/api/bookings/ride", json=ride_data, headers=auth_header(customer_token))
        ride_id = res_ride.json()["id"]

        res = client.put(
            f"/api/admin/bookings/ride/{ride_id}/status",
            json={"status": "Completed"},
            headers=auth_header(admin_token),
        )
        assert res.status_code == 200
        assert res.json()["status"] == "Completed"
