import sys
sys.path.insert(0, r"d:\agent-project\SelfwellAgent\backend")
from app.services.diagnosis_service import create_diagnosis, _check_text_safety
print("OK diagnosis_service", _check_text_safety("hello"))
