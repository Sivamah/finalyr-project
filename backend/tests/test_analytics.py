"""Phase 9 — Analytics Tests"""

from tests.conftest import auth_header

class TestAnalytics:
    def test_get_summary(self, client, admin_token):
        res = client.get("/api/analytics/summary", headers=auth_header(admin_token))
        assert res.status_code == 200
        data = res.json()
        assert "total_users" in data
        assert "total_trips" in data

    def test_get_trips(self, client, admin_token):
        res = client.get("/api/analytics/trips", headers=auth_header(admin_token))
        assert res.status_code == 200
        assert "trend" in res.json()

    def test_get_drivers(self, client, admin_token):
        res = client.get("/api/analytics/drivers", headers=auth_header(admin_token))
        assert res.status_code == 200
        assert "status" in res.json()

    def test_get_dmfe_analytics(self, client, admin_token):
        res = client.get("/api/analytics/dmfe", headers=auth_header(admin_token))
        assert res.status_code == 200
        assert "avg_feasibility" in res.json()

    def test_export_csv(self, client, admin_token):
        res = client.get("/api/analytics/export?type=csv&report=trips", headers=auth_header(admin_token))
        assert res.status_code == 200
        assert res.headers["Content-Type"] == "text/csv"
        assert "attachment" in res.headers["Content-Disposition"]
