"""Check database state for debugging checkin issue."""
import asyncio
from app.db.session import get_sessionmaker
from sqlalchemy import text


async def check():
    sm = get_sessionmaker()
    async with sm() as session:
        # Check users
        result = await session.execute(text("SELECT id, nickname FROM users LIMIT 3"))
        print("=== Users ===")
        for row in result:
            print(row)

        # Check plans
        result = await session.execute(
            text("SELECT id, user_id, status, started_at FROM plans LIMIT 5")
        )
        print("\n=== Plans ===")
        for row in result:
            print(row)

        # Check videos count
        result = await session.execute(text("SELECT COUNT(*) FROM videos"))
        print(f"\n=== Video count: {result.scalar()} ===")

        # Check if there's a plan with tasks
        result = await session.execute(
            text("SELECT id, days FROM plans WHERE status = 'active' LIMIT 1")
        )
        plan = result.first()
        if plan:
            print(f"\n=== Active Plan ===")
            print(f"Plan ID: {plan[0]}")
            print(f"Days data type: {type(plan[1])}")
            if plan[1]:
                import json

                days = plan[1]
                if isinstance(days, str):
                    days = json.loads(days)
                items = days.get("items", []) if isinstance(days, dict) else []
                print(f"Days items count: {len(items)}")
                if items:
                    print(f"Day 1 tasks: {items[0].get('tasks', []) if items else []}")


if __name__ == "__main__":
    asyncio.run(check())
