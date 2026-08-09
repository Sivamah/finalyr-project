import requests
import sys

BASE_URL = "http://127.0.0.1:8000/api"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODYzNzkyMjUsInN1YiI6IjEifQ.AI-XZiHdzbN-t5qYannH7yCzo3cHsPsm9mxKc6npYzQ"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def check(name, req):
    if req.status_code >= 400:
        print(f"❌ {name} failed: {req.status_code} {req.text}")
        sys.exit(1)
    else:
        print(f"✅ {name}")
    return req.json()

print("--- Starting E2E API Test ---")
check("Profile", requests.get(f"{BASE_URL}/auth/profile", headers=HEADERS))

print("Simulating 5 requests...")
check("Simulate", requests.post(f"{BASE_URL}/orchestration/simulate?count=5", headers=HEADERS))

print("Running DMFE...")
res = check("DMFE Analyze", requests.post(f"{BASE_URL}/dmfe/analyze", headers=HEADERS))
print(f"  -> Dispatched trips: {res.get('dispatched_trips', 0)}")
print(f"  -> Execution time: {res.get('execution_time_ms', 0):.1f}ms")

batches = check("Batches", requests.get(f"{BASE_URL}/dmfe/batches", headers=HEADERS))
print(f"  -> Found {len(batches)} batches")

queue = check("Queue", requests.get(f"{BASE_URL}/simulation/queue", headers=HEADERS))
print(f"  -> Queue size: {len(queue.get('requests', []))}")

history = check("Driver History", requests.get(f"{BASE_URL}/drivers/assignments/history", headers=HEADERS))
print(f"  -> Found {len(history)} driver assignments")

notifications = check("Notifications", requests.get(f"{BASE_URL}/notifications/timeline?limit=10", headers=HEADERS))
print(f"  -> Found {len(notifications)} notifications")

analytics = check("Analytics", requests.get(f"{BASE_URL}/dmfe/statistics", headers=HEADERS))
print(f"  -> Global Batches Generated: {analytics.get('total_batches_generated', 0)}")

print("🎉 E2E Test Passed Successfully!")
