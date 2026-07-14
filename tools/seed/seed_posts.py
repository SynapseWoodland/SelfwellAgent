"""Seed posts table (D9-1): 10 posts for community E2E testing.

Target: 10 rows
Idempotent: deletes all rows before inserting.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import psycopg

USER_1 = uuid.UUID("40e10a9e-329f-4998-a3f0-d36c0ab08abf")
USER_2 = uuid.UUID("f255dff8-9f47-43a6-91c4-932b00c0447f")
SOURCE = "seed"

POSTS = [
    {"user_id": USER_2, "content": "完成了21天蜕变计划，感觉整个人都不一样了！肩颈不再酸痛，心情也开朗了很多。感谢这个过程让我学会关爱自己。", "images": [{"url": "https://picsum.photos/400/300?random=1", "caption": "蜕变前后对比"}], "status": "approved", "ai_comment": "你的坚持真的很棒！21天的蜕变值得庆祝~", "official_comment": "恭喜完成蜕变计划！", "like_count": 42, "comment_count": 8, "created_at": datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)},
    {"user_id": USER_1, "content": "坚持了一周的打卡，每天10分钟的肩颈放松真的有效！现在脖子不那么僵硬了，睡眠质量也提升了。", "images": [], "status": "approved", "ai_comment": "一周的坚持已经看到效果，继续加油！", "official_comment": None, "like_count": 23, "comment_count": 5, "created_at": datetime(2026, 7, 11, 14, 0, 0, tzinfo=timezone.utc)},
    {"user_id": USER_2, "content": "分享一下我的睡前放松routine：热敷5分钟+拉伸3分钟+冥想2分钟，一套下来整个人都放松了。", "images": [{"url": "https://picsum.photos/400/300?random=2", "caption": "放松时刻"}], "status": "approved", "ai_comment": "这个routine看起来很棒！感谢分享~", "official_comment": "实用分享，感谢！", "like_count": 67, "comment_count": 12, "created_at": datetime(2026, 7, 10, 20, 0, 0, tzinfo=timezone.utc)},
    {"user_id": USER_1, "content": "第一次尝试刮痧，肩颈出痧明显，看来确实需要好好调理了。姐妹们也要注意身体啊！", "images": [{"url": "https://picsum.photos/400/300?random=3", "caption": "刮痧记录"}, {"url": "https://picsum.photos/400/300?random=4", "caption": "出痧情况"}], "status": "approved", "ai_comment": "出痧说明经络不通，坚持调理会越来越好~", "official_comment": "注意刮痧后的护理哦", "like_count": 35, "comment_count": 7, "created_at": datetime(2026, 7, 9, 16, 0, 0, tzinfo=timezone.utc)},
    {"user_id": USER_2, "content": "Day 14打卡，感觉自己的心态变化最大。从最初的焦虑到现在的平静，感恩每一次练习。", "images": [], "status": "approved", "ai_comment": "身体和心灵的双重进步是最棒的收获！", "official_comment": None, "like_count": 51, "comment_count": 9, "created_at": datetime(2026, 7, 8, 9, 0, 0, tzinfo=timezone.utc)},
    {"user_id": USER_1, "content": "为什么我每天打卡了还是没有明显效果？是不是动作不对？求指导", "images": [], "status": "pending", "ai_comment": "每个人的身体状况不同，效果也会有差异。建议记录下每天的感受，慢慢会发现变化的~", "official_comment": None, "like_count": 12, "comment_count": 4, "created_at": datetime(2026, 7, 7, 18, 0, 0, tzinfo=timezone.utc)},
    {"user_id": USER_2, "content": "每天10分钟，改变看得见！给大家看看我坚持一个月的前后对比。", "images": [{"url": "https://picsum.photos/400/300?random=5", "caption": "一个月前后对比"}], "status": "approved", "ai_comment": "一个月的变化真的很明显！", "official_comment": "坚持就是胜利！", "like_count": 89, "comment_count": 15, "created_at": datetime(2026, 7, 6, 11, 0, 0, tzinfo=timezone.utc)},
    {"user_id": USER_1, "content": "今天完成了第7天的打卡，虽然有点累但是感觉很充实。每天进步一点点，加油！", "images": [], "status": "approved", "ai_comment": "7天打卡完成得很棒！继续坚持~", "official_comment": None, "like_count": 28, "comment_count": 3, "created_at": datetime(2026, 7, 5, 21, 0, 0, tzinfo=timezone.utc)},
    {"user_id": USER_2, "content": "给大家推荐几个我常用的放松音乐，配合练习使用效果翻倍！", "images": [], "status": "pending", "ai_comment": "音乐确实能帮助放松，感谢分享~", "official_comment": None, "like_count": 19, "comment_count": 6, "created_at": datetime(2026, 7, 4, 15, 0, 0, tzinfo=timezone.utc)},
    {"user_id": USER_1, "content": "蜕变计划的Day 1，期待21天后的自己。希望能坚持下去，改变从今天开始！", "images": [], "status": "approved", "ai_comment": "Day 1 是最好的开始！", "official_comment": "欢迎开始蜕变之旅~", "like_count": 15, "comment_count": 2, "created_at": datetime(2026, 7, 1, 9, 0, 0, tzinfo=timezone.utc)},
]


def run() -> None:
    with psycopg.connect(
        host="localhost", port=5432, dbname="selfwell",
        user="selfwell", password="change_me_in_dev_only", autocommit=True,
    ) as conn:
        conn.execute("DELETE FROM posts")
        print("[seed_posts] Deleted all posts (dev env full refresh)")

        inserted = 0
        for post in POSTS:
            conn.execute(
                "INSERT INTO posts (id, user_id, content, images, status, ai_comment, official_comment, like_count, comment_count, reviewed_by, reviewed_at, created_at, deleted_at, source, created_by, created_time, last_updated_time, last_updated_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, %s, NULL, %s, %s, %s, %s, %s)",
                (
                    str(uuid.uuid4()), str(post["user_id"]), post["content"],
                    psycopg.types.json.Jsonb(post["images"]), post["status"],
                    post["ai_comment"], post["official_comment"],
                    post["like_count"], post["comment_count"],
                    post["created_at"], SOURCE, "seed",
                    post["created_at"], post["created_at"], "seed",
                ),
            )
            inserted += 1

        print(f"[seed_posts] Inserted {inserted} posts (source='{SOURCE}')")

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM posts")
            total = cur.fetchone()[0]
            print(f"[seed_posts] Verified: {total} posts in DB (expected 10)")


if __name__ == "__main__":
    run()
