"""Add source column to seed target tables for idempotent tracking."""
import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="selfwell",
    user="selfwell",
    password="change_me_in_dev_only",
)

TABLES = ["plans", "checkins", "feedback", "recall_sessions", "posts", "videos"]

for tbl in TABLES:
    cur = conn.execute(
        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tbl}'"
    )
    cols = {r[0] for r in cur}
    if "source" not in cols:
        conn.execute(
            f"ALTER TABLE {tbl} ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'manual'"
        )
        conn.commit()
        print(f"ALTER TABLE {tbl} ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'manual'")
    else:
        print(f"{tbl} already has source column")

conn.close()
print("\nDone.")
