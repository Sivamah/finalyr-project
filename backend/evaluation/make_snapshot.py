"""Phase 10 baseline snapshot — captured BEFORE any evaluation work.

Records:
  1. SHA-256 hashes of every Phase 9 DMFE engine / API file so the
     verification step can prove none were modified during evaluation.
  2. The complete FastAPI route surface (method, path) so the verification
     step can prove no API was added, removed or changed.
"""

import hashlib
import json
import os
import re
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WATCH_PATTERNS = [
    r"app/dmfe/.*\.py$",
    r"app/engine/.*\.py$",
    r"app/api/routes/.*\.py$",
    r"app/services/.*\.py$",
    r"app/db/models\.py$",
    r"app/main\.py$",
]

engine_manifest = {}

for root, _dirs, files in os.walk(os.path.join(BACKEND, "app")):
    for name in files:
        if not name.endswith(".py"):
            continue
        rel = os.path.relpath(os.path.join(root, name), BACKEND)
        rel = rel.replace(os.sep, "/")
        if any(re.search(p, rel) for p in WATCH_PATTERNS):
            h = hashlib.sha256()
            with open(os.path.join(root, name), "rb") as fh:
                h.update(fh.read())
            engine_manifest[rel] = h.hexdigest()

api_surface = []
sys.path.insert(0, BACKEND)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(BACKEND, 'dmfe_dev.db')}")
from fastapi.routing import APIRoute  # noqa: E402
from app.main import app  # noqa: E402

def walk(router, seen=None):
    """Recursively collect APIRoute entries (handles _IncludedRouter wrappers)."""
    if seen is None:
        seen = set()
    for route in router.routes:
        cls = type(route).__name__
        if cls == "_IncludedRouter":
            walk(route.original_router, seen)
        elif isinstance(route, APIRoute):
            key = (tuple(sorted(route.methods)), route.path)
            if key not in seen:
                seen.add(key)
                api_surface.append({
                    "method": sorted(route.methods),
                    "path": route.path,
                })


walk(app)
api_surface = sorted(api_surface, key=lambda r: (r["path"], ",".join(r["method"])))

out_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(out_dir, "engine_manifest.json"), "w") as fh:
    json.dump(engine_manifest, fh, indent=2, sort_keys=True)
with open(os.path.join(out_dir, "api_surface_snapshot.json"), "w") as fh:
    json.dump(api_surface, fh, indent=2)

print(f"engine_manifest.json : {len(engine_manifest)} files hashed")
print(f"api_surface_snapshot.json : {len(api_surface)} routes recorded")
