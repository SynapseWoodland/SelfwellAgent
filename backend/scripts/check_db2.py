"""Check video library and plan-video matching."""
import asyncio
import json
from app.db.session import get_sessionmaker
from sqlalchemy import text


async def check():
    sm = get_sessionmaker()
    async with sm() as session:
        # List all videos
        result = await session.execute(
            text("SELECT id, title, status FROM videos ORDER BY id")
        )
        print("=== All Videos ===")
        videos = list(result)
        for row in videos:
            print(f"  {row[0]} | {row[1]} | {row[2]}")
        print(f"\nTotal: {len(videos)} videos")

        # Get video IDs
        video_ids = [str(row[0]) for row in videos]
        
        # Check the plan's video_ids
        result = await session.execute(
            text("SELECT id, days FROM plans WHERE status = 'active' LIMIT 1")
        )
        plan = result.first()
        if plan:
            plan_id = plan[0]
            days = plan[1]
            if isinstance(days, str):
                days = json.loads(days)
            
            items = days.get("items", []) if isinstance(days, dict) else []
            
            # Collect all video_ids used in the plan
            plan_video_ids = set()
            for day_item in items:
                for task in day_item.get("tasks", []):
                    plan_video_ids.add(task.get("video_id"))
            
            print(f"\n=== Plan Video IDs ===")
            print(f"Plan has {len(plan_video_ids)} unique video IDs")
            
            # Check which ones exist in video table
            existing = set()
            missing = set()
            for vid in plan_video_ids:
                if vid in video_ids:
                    existing.add(vid)
                else:
                    missing.add(vid)
            
            print(f"Existing in DB: {len(existing)}")
            print(f"Missing from DB: {len(missing)}")
            if missing:
                print(f"Missing video IDs: {list(missing)[:5]}...")
            
            # Check day 1 details
            day1 = items[0] if items else None
            if day1:
                print(f"\n=== Day 1 Details ===")
                print(f"Day: {day1.get('day')}")
                print(f"Phase: {day1.get('phase')}")
                print(f"Tasks: {day1.get('tasks')}")
                
                # Check if day 1 task's video exists
                day1_video_id = day1.get("tasks", [{}])[0].get("video_id") if day1.get("tasks") else None
                if day1_video_id:
                    result = await session.execute(
                        text("SELECT id, title FROM videos WHERE id = :vid"),
                        {"vid": day1_video_id}
                    )
                    video_row = result.first()
                    if video_row:
                        print(f"Day 1 video EXISTS: {video_row[1]}")
                    else:
                        print(f"Day 1 video MISSING: {day1_video_id}")

        # Check if user has any checkin records
        result = await session.execute(
            text("SELECT user_id, plan_id, day, video_id, created_at FROM checkins LIMIT 5")
        )
        print(f"\n=== Existing Checkins ===")
        checkins = list(result)
        if checkins:
            for row in checkins:
                print(f"  User: {row[0]}, Plan: {row[1]}, Day: {row[2]}, Video: {row[3]}, At: {row[4]}")
        else:
            print("  No checkins found")


if __name__ == "__main__":
    asyncio.run(check())
