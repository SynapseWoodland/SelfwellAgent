import sys
sys.path.insert(0, r"d:\agent-project\SelfwellAgent\backend")
from app.main import app
print("OK app loaded")
for route in app.routes:
    if hasattr(route, "methods") and hasattr(route, "path"):
        print(f"{sorted(route.methods or [])} {route.path}")
