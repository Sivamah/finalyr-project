"""
E2E API Test — A-DMFE Delivery Platform
=======================================
End-to-end smoke test against a running backend.

Flow:
    POST /api/auth/login            -> fresh access_token (never hardcoded)
    GET  /api/auth/profile
    POST /api/orchestration/simulate -> seed test requests
    POST /api/dmfe/analyze          -> A-DMFE analysis
    GET  /api/dmfe/batches          -> formed batches
    GET  /api/simulation/queue      -> pending queue
    GET  /api/drivers/assignments/history
    GET  /api/notifications/timeline
    GET  /api/dmfe/statistics

Output uses portable ASCII markers ([PASS]/[FAIL]) so the script
runs identically on Windows (cp1252) and POSIX consoles.

Usage:
    python e2e_test.py                      # defaults: localhost:8000
    E2E_BASE_URL=http://host:port python e2e_test.py
    E2E_EMAIL=... E2E_PASSWORD=... python e2e_test.py   # optional override
"""

import os
import sys
import time

import requests

BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000/api")
EMAIL = os.environ.get("E2E_EMAIL", "admin@aiorch.com")
PASSWORD = os.environ.get("E2E_PASSWORD", "admin123")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass  # Python < 3.7 — ASCII markers keep the output safe anyway


def check(name, req):
    """Assert 2xx; [PASS] / [FAIL] with HTTP status and response body."""
    if not 200 <= req.status_code < 300:
        print(f"[FAIL] {name} - HTTP {req.status_code}")
        print(f"Response: {req.text}")
        sys.exit(1)
    print(f"[PASS] {name} - HTTP {req.status_code}")
    return req.json()


def require_field(data, key, name):
    """Fail hard when an expected response field is genuinely missing."""
    if key not in data:
        print(f"[FAIL] {name}: expected field '{key}' missing in response")
        print(f"Response: {data}")
        sys.exit(1)
    return data[key]


class Api:
    """Small authenticated client — one fresh token for the whole run."""

    def __init__(self):
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"[FAIL] Login - HTTP {resp.status_code}")
            print(f"Response: {resp.text}")
            print(
                "[FAIL] E2E authentication failed: could not obtain a fresh "
                "access_token via POST /api/auth/login. Check that the backend "
                "is running and that E2E_EMAIL/E2E_PASSWORD match a seeded "
                "Admin account (default: admin@aiorch.com / admin123)."
            )
            sys.exit(1)
        body = resp.json()
        require_field(body, "access_token", "Login")
        self.headers = {"Authorization": f"Bearer {body['access_token']}"}
        print("[PASS] Login - HTTP 200 (fresh access_token via /api/auth/login)")

    def get(self, path, **kw):
        return requests.get(f"{BASE_URL}{path}", headers=self.headers,
                            timeout=60, **kw)

    def post(self, path, **kw):
        return requests.post(f"{BASE_URL}{path}", headers=self.headers,
                             timeout=120, **kw)


def main() -> None:
    api = Api()

    print("--- Starting E2E API Test ---")
    profile = check("Profile", api.get("/auth/profile"))
    email = require_field(profile, "email", "Profile")
    role = require_field(profile, "role", "Profile")
    print(f"  -> Authenticated as: {email} ({role})")

    print("Simulating 5 requests...")
    check("Simulate", api.post("/orchestration/simulate?count=5"))

    print("Running DMFE...")
    started = time.monotonic()
    res = check("DMFE Analyze", api.post("/dmfe/analyze"))
    elapsed_ms = (time.monotonic() - started) * 1000.0
    batches_created = require_field(res, "batches_created", "DMFE Analyze")
    rejected = require_field(res, "rejected_count", "DMFE Analyze")
    print(f"  -> Batches created: {batches_created}")
    print(f"  -> Rejected: {rejected}")
    print(f"  -> Execution time: {elapsed_ms:.1f}ms (client-side)")

    batches = check("Batches", api.get("/dmfe/batches"))
    print(f"  -> Found {len(batches)} batches")

    queue = check("Queue", api.get("/simulation/queue"))
    queue_items = require_field(queue, "items", "Queue")
    print(f"  -> Queue size: {len(queue_items)}")

    history = check("Driver History",
                    api.get("/drivers/assignments/history"))
    print(f"  -> Found {len(history)} driver assignments")

    notifications = check("Notifications",
                          api.get("/notifications/timeline?limit=10"))
    print(f"  -> Found {len(notifications)} notifications")

    analytics = check("Analytics", api.get("/dmfe/statistics"))
    total_batches = require_field(analytics, "total_batches_created", "Analytics")
    total_trips = require_field(analytics, "total_trips", "Analytics")
    print(f"  -> Total batches created: {total_batches}")
    print(f"  -> Total trips: {total_trips}")

    trips = check("Trips", api.get("/dmfe/trips?limit=5"))
    print(f"  -> Found {len(trips)} trips")

    print("[PASS] E2E Test Passed Successfully!")


if __name__ == "__main__":
    main()