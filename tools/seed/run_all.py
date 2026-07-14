"""Run all seed scripts in order. Idempotent: safe to run multiple times."""
import subprocess
import sys
from pathlib import Path

SEED_DIR = Path(__file__).parent
PYTHON = SEED_DIR.parent.parent / ".venv" / "Scripts" / "python.exe"

# Phase 4 batch 5: videos moved to front so plans (which match against videos) hit the
# real rank_videos() path instead of the placeholder template.
SCRIPTS = [
    "seed_users.py",             # 2 users (FK prerequisite for everything else)
    "seed_videos.py",            # 50+ videos (MUST run before seed_plans; rank_videos() needs >=50)
    "seed_plans.py",             # 10 plans (depends on users + videos)
    "seed_checkins.py",          # 42 checkins (depends on plans)
    "seed_feedback.py",          # 30 feedback (independent)
    "seed_recall_sessions.py",   # 5 recall_sessions (independent)
    "seed_posts.py",             # 10 posts (independent)
]


def main() -> int:
    for script in SCRIPTS:
        path = SEED_DIR / script
        if not path.exists():
            print(f"[ERROR] Missing script: {path}")
            return 1
        print(f"\n=== Running {script} ===")
        result = subprocess.run([str(PYTHON), str(path)], cwd=str(SEED_DIR.parent.parent))
        if result.returncode != 0:
            print(f"[FAIL] {script} exited with code {result.returncode}")
            return result.returncode

    # Verification
    print("\n=== Running verify_all.py ===")
    result = subprocess.run(
        [str(PYTHON), str(SEED_DIR / "verify_all.py")],
        cwd=str(SEED_DIR.parent.parent),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())