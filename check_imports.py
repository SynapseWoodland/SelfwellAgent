import sys
sys.path.insert(0, r"d:\agent-project\SelfwellAgent\backend")
from app.services.auth import jwt_service, wx_login_service, phone_login_service
print("OK auth")
from app.services.users import profile_service, optimistic_lock, push_token_service, draft_promotion
print("OK users")
