"""Final verification of all seeded data + reports source labeling."""
import psycopg

with psycopg.connect(
    host="localhost", port=5432, dbname="selfwell",
    user="selfwell", password="change_me_in_dev_only", autocommit=True,
) as conn:
    print("=" * 70)
    print(" FINAL DATA GOVERNANCE VERIFICATION")
    print("=" * 70)

    # 1. Table row counts
    tables = [
        ("users", "users table (preserved)"),
        ("plans", "D5-1 plans"),
        ("checkins", "D6-1 checkins"),
        ("recall_sessions", "D7-1 recall_sessions"),
        ("feedback", "D8-1 feedback"),
        ("posts", "D9-1 posts"),
        ("videos", "D10-1 videos"),
        ("reports", "D4 reports (with source labeling)"),
    ]
    print("\n[1] Table row counts:")
    for tbl, desc in tables:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            n = cur.fetchone()[0]
            print(f"  {desc}: {n} rows")

    # 2. Seed-marked rows
    print("\n[2] Seed-marked rows (source='seed'):")
    seed_tables = ["plans", "checkins", "feedback", "recall_sessions", "posts"]
    for tbl in seed_tables:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE source = 'seed'")
            n = cur.fetchone()[0]
            print(f"  {tbl}: {n} seed rows")

    # 3. Videos seed rows
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM videos WHERE source = 'seed'")
        n = cur.fetchone()[0]
        print(f"  videos (seed): {n} seed rows")
        cur.execute("SELECT COUNT(*) FROM videos WHERE source != 'seed'")
        n2 = cur.fetchone()[0]
        print(f"  videos (manual/existing): {n2} rows")

    # 4. Reports source breakdown
    print("\n[3] Reports source labeling:")
    with conn.cursor() as cur:
        cur.execute("SELECT source, COUNT(*) FROM reports GROUP BY source ORDER BY source")
        for row in cur:
            print(f"  source={row[0]}: {row[1]} rows")

    # 5. Recall sessions trigger breakdown
    print("\n[4] Recall sessions trigger breakdown:")
    with conn.cursor() as cur:
        cur.execute("SELECT trigger, COUNT(*) FROM recall_sessions GROUP BY trigger ORDER BY trigger")
        for row in cur:
            print(f"  {row[0]}: {row[1]} rows")

    # 6. Feedback breakdown
    print("\n[5] Feedback breakdown:")
    with conn.cursor() as cur:
        cur.execute("SELECT feedback_type, COUNT(*) FROM feedback GROUP BY feedback_type ORDER BY feedback_type")
        for row in cur:
            print(f"  {row[0]}: {row[1]} rows")

    # 7. Plans status breakdown
    print("\n[6] Plans status breakdown:")
    with conn.cursor() as cur:
        cur.execute("SELECT status, COUNT(*) FROM plans WHERE source = 'seed' GROUP BY status ORDER BY status")
        for row in cur:
            print(f"  {row[0]}: {row[1]} rows")

    # 8. Per-user summary
    print("\n[7] Per-user data summary:")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                u.id,
                u.nickname,
                (SELECT COUNT(*) FROM plans p WHERE p.user_id = u.id) AS plans,
                (SELECT COUNT(*) FROM checkins c WHERE c.user_id = u.id) AS checkins,
                (SELECT COUNT(*) FROM feedback f WHERE f.user_id = u.id) AS feedback,
                (SELECT COUNT(*) FROM recall_sessions r WHERE r.user_id = u.id) AS recall,
                (SELECT COUNT(*) FROM posts po WHERE po.user_id = u.id) AS posts
            FROM users u
            ORDER BY u.created_at
        """)
        for row in cur:
            print(f"  user {row[1]}:")
            print(f"    plans={row[2]}, checkins={row[3]}, feedback={row[4]}, recall={row[5]}, posts={row[6]}")

    # 9. Acceptance criteria check
    print("\n[8] Acceptance criteria:")
    criteria = [
        ("plans >= 10", "SELECT COUNT(*) FROM plans"),
        ("checkins >= 42", "SELECT COUNT(*) FROM checkins"),
        ("recall_sessions >= 5", "SELECT COUNT(*) FROM recall_sessions"),
        ("feedback >= 30", "SELECT COUNT(*) FROM feedback"),
        ("posts >= 10", "SELECT COUNT(*) FROM posts"),
        ("videos >= 15", "SELECT COUNT(*) FROM videos"),
    ]
    for desc, sql in criteria:
        with conn.cursor() as cur:
            cur.execute(sql)
            n = cur.fetchone()[0]
            status = "PASS" if (
                (desc.startswith("plans") and n >= 10)
                or (desc.startswith("checkins") and n >= 42)
                or (desc.startswith("recall_sessions") and n >= 5)
                or (desc.startswith("feedback") and n >= 30)
                or (desc.startswith("posts") and n >= 10)
                or (desc.startswith("videos") and n >= 15)
            ) else "FAIL"
            print(f"  [{status}] {desc}: {n}")

    print("\n" + "=" * 70)
    print(" Verification complete.")
    print("=" * 70)