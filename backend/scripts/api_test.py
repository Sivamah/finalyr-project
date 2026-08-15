"""Comprehensive API test — correct endpoint paths based on actual router definitions."""
import httpx, sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = "http://localhost:8000/api"
r = httpx.post(f"{BASE}/auth/login", json={"email":"admin@aiorch.com","password":"admin123"}, timeout=10)
assert r.status_code == 200, f"Login failed: {r.status_code}"
TOKEN = r.json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}"}

results = []
def test(method, url, label, body=None):
    try:
        if method == "GET":
            r = httpx.get(f"{BASE}{url}", headers=H, timeout=15)
        elif method == "POST":
            r = httpx.post(f"{BASE}{url}", headers=H, json=body, timeout=15)
        else:
            r = httpx.request(method, f"{BASE}{url}", headers=H, json=body, timeout=15)
        ok = "PASS" if r.status_code < 400 else "FAIL"
        detail = ""
        if r.status_code >= 400:
            try: detail = str(r.json().get("detail",""))[:150]
            except: detail = r.text[:150]
        results.append((label, r.status_code, ok, detail))
        print(f"  [{ok}] {r.status_code} {method} {url} -- {label}" + (f" | {detail}" if detail else ""))
        return r
    except Exception as e:
        results.append((label, "ERR", "FAIL", str(e)[:100]))
        print(f"  [FAIL] ERR {method} {url} -- {label} | {e}")
        return None

print("=== AUTH ===")
test("GET", "/auth/profile", "Profile")

print("\n=== DASHBOARD ===")
test("GET", "/dashboard/stats", "Stats")
test("GET", "/dashboard/providers/breakdown", "Breakdown")
test("GET", "/dashboard/results/recent", "Recent results")

print("\n=== PROVIDERS ===")
test("GET", "/providers/", "List providers")  # note trailing slash

print("\n=== DRIVERS (full path in router) ===")
test("GET", "/drivers", "List drivers")
test("GET", "/drivers/stats", "Driver stats")
test("GET", "/vehicles", "List vehicles")
test("GET", "/vehicles/stats", "Vehicle stats")
test("GET", "/vehicles/locations", "Vehicle locations")
test("GET", "/drivers/assignments/history?limit=100", "Assignment history")

print("\n=== ORCHESTRATION ===")
test("GET", "/orchestration/requests", "List requests (FIXED)")
test("GET", "/orchestration/results", "List results")
test("GET", "/orchestration/datasets", "List datasets")

print("\n=== DMFE ENGINE ===")
test("GET", "/dmfe/queue", "Queue")
test("GET", "/dmfe/trips", "Trips")
test("GET", "/dmfe/assignments", "Assignments")
test("GET", "/dmfe/context", "A-DMFE context")

print("\n=== DMFE V2 ===")
test("GET", "/dmfe/batches", "Batches")
test("GET", "/dmfe/history", "History")
test("GET", "/dmfe/statistics", "Statistics")

print("\n=== SIMULATION ===")
test("GET", "/simulation/status", "Status")
test("GET", "/simulation/queue?limit=200", "Queue")
test("GET", "/simulation/history?limit=200", "History")
test("GET", "/simulation/analytics", "Analytics")
test("GET", "/simulation/advanced-analytics", "Advanced analytics")

print("\n=== NOTIFICATIONS ===")
test("GET", "/notifications", "List")
test("GET", "/notifications/stats", "Stats")
test("GET", "/notifications/timeline?limit=8", "Timeline")

print("\n=== XAI ===")
test("GET", "/xai/explanations", "Explanations")
test("GET", "/xai/overview", "Overview")

print("\n=== CONFIG ===")
test("GET", "/config", "Config")
test("GET", "/config/audit-logs", "Audit logs")

print("\n=== PLAYBACK (full path in router) ===")
test("GET", "/scenarios", "List scenarios")
test("GET", "/simulation/saved/dashboard", "Saved dashboard")
test("GET", "/simulation/saved", "Saved list")

print("\n=== DMFE PIPELINE (E2E) ===")
test("POST", "/orchestration/simulate", "Generate 5 requests", None)
test("GET", "/dmfe/queue", "Queue after gen")
test("POST", "/dmfe/run", "Run pipeline", {"limit": 50})
test("GET", "/dmfe/trips", "Trips after run")
test("GET", "/dmfe/assignments", "Assignments after run")

# Summary
print("\n" + "="*60)
passes = sum(1 for r in results if r[2]=="PASS")
fails = sum(1 for r in results if r[2]=="FAIL")
print(f"TOTAL: {len(results)} | PASS: {passes} | FAIL: {fails}")
if fails:
    print("\nFAILURES:")
    for label, code, status, detail in results:
        if status == "FAIL":
            print(f"  {label} -> {code}: {detail}")
