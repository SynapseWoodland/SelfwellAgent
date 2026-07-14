"""Add source column to reports table for mock data labeling."""
import psycopg

with psycopg.connect(
    host="localhost", port=5432, dbname="selfwell",
    user="selfwell", password="change_me_in_dev_only", autocommit=True,
) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'reports' AND column_name = 'source'
        """)
        if cur.fetchone():
            print("reports table already has 'source' column")
        else:
            cur.execute("ALTER TABLE reports ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'mock'")
            print("ALTER TABLE reports ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'mock'")
            # Update existing rows: rule-engine = mock, demo-model = demo, NULL llm_model = pending
            cur.execute("UPDATE reports SET source = 'mock-rule-engine' WHERE llm_model = 'rule-engine'")
            print(f"  -> Labeled rule-engine reports as 'mock-rule-engine'")
            cur.execute("UPDATE reports SET source = 'demo-model' WHERE llm_model = 'demo-model'")
            print(f"  -> Labeled demo-model reports as 'demo-model'")
            cur.execute("UPDATE reports SET source = 'pending' WHERE llm_model IS NULL")
            print(f"  -> Labeled NULL-model reports as 'pending'")
    print("\nDone.")