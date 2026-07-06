f = 'd:/agent-project/SelfwellAgent/docs/plan/mvp-implementation-plan.md'
with open(f, 'r', encoding='utf-8', newline='') as fh:
    content = fh.read()

# Mapping: (old_text, new_text)
# Verified against openapi.yaml V1.1.0 operationId list
replacements = [
    # auth
    ('`auth.loginByWx` POST `/auth/wx-login`',
     '`wxMpLogin` POST `/api/v1/auth/wx-login`'),
    # users
    ('`users.getMe` GET `/users/me`',
     '`getCurrentUser` GET `/api/v1/users/me`'),
    ('`users.updatePushToken` POST `/users/push-token`',
     '`updatePushToken` PUT `/api/v1/users/me/push-token`'),
    # diagnosis
    ('`diagnosis.create` POST `/diagnosis`',
     '`createDiagnosis` POST `/api/v1/diagnosis`'),
    ('`diagnosis.streamEvents` GET `/diagnosis/{id}/stream`',
     '`streamDiagnosis` GET `/api/v1/diagnosis/{id}/stream`'),
    ('`diagnosis.getReport` GET `/diagnosis/{id}`',
     '`getDiagnosis` GET `/api/v1/diagnosis/{id}`'),
    # assistant (P03a) - single endpoint in openapi
    ('`assistant.createSession` POST `/assistant/sessions` + `assistant.sendMessage` POST `/assistant/sessions/{id}/messages`',
     '`assistantChat` POST `/api/v1/assistant/chat`（单端点，session_id 在请求体内）'),
    # plans
    ('`plans.generate` POST `/plans/generate`',
     '`generatePlan` POST `/api/v1/plans/generate`'),
    # videos
    ('`videos.matchForPlan` GET `/videos/match?tag=...`',
     '`searchVideos` GET `/api/v1/videos/search`'),
    # checkins (03-home uses checkins.getToday)
    ('`checkins.getToday` GET `/checkins/today`',
     '`getTodayPlan` GET `/api/v1/plans/today`'),
    # checkins (08-checkin uses checkins.create)
    ('`checkins.create` POST `/checkins`',
     '`createCheckin` POST `/api/v1/checkins`'),
    # feedback (08-butler-diary uses feedback.createMood)
    ('`feedback.createMood` POST `/feedback`',
     '`createFeedback` POST `/api/v1/feedback`'),
    # feedback quick (08-checkin)
    ('`feedback.createQuick` POST `/feedback`',
     '`createFeedback` POST `/api/v1/feedback`'),
    # recall (09-butler-compare)
    ('`butler.getRecall` GET `/butler/recall/{day}`',
     '`getRecallMessages` GET `/api/v1/butler/recall/{id}/messages`'),
    # community
    ('`community.listPosts` GET `/community/posts`',
     '`getCommunityPosts` GET `/api/v1/community/posts`'),
    ('`community.createPost` POST `/community/posts`',
     '`createPost` POST `/api/v1/community/posts`'),
    # share poster
    ('`share.generateHugCard` POST `/share/hug-card?day=7`',
     '`generateSharePoster` POST `/api/v1/share/poster`（body.day 控制第 7/14/21 天）'),
    # uploads.presign - no openapi entry, keep as-is with note
    ('`uploads.presign` POST `/uploads/presign`',
     '`uploads.presign` POST `/api/v1/uploads/presign`（storage 抽象，详见 ADR-0009）'),
]

for old, new in replacements:
    count = content.count(old)
    if count > 0:
        content = content.replace(old, new)
        print(f'OK: replaced {count}x: {old[:50]}...')
    else:
        print(f'MISS: {old[:60]}')

with open(f, 'w', encoding='utf-8', newline='') as fh:
    fh.write(content)
print('\nDone')
