-- Migration: Add assistant_profile column to ai_sessions
-- Sprint 2026-07-09 M5 智能管家扩展
-- 真源: backend/alembic/versions/0005_add_assistant_profile_to_ai_sessions.py

ALTER TABLE ai_sessions
ADD COLUMN assistant_profile JSONB NULL;

ALTER TABLE ai_sessions
ADD CONSTRAINT ck_ai_sessions_assistant_profile_type
CHECK (assistant_profile IS NULL OR jsonb_typeof(assistant_profile) = 'object');

COMMENT ON COLUMN ai_sessions.assistant_profile IS
'AI 管家侧角色/配置信息（persona、greeting、capabilities 等），结构为 JSON object。';
