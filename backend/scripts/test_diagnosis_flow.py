"""Test the complete diagnosis flow with fixed vision LLM."""
import asyncio
import sys
sys.path.insert(0, "d:/agent-project/SelfwellAgent/backend")


async def test():
    print("Testing complete diagnosis flow...")

    # Simulate photos as they come from the service
    test_photos = [
        {
            "url": "https://www.w3schools.com/css/paris.jpg",
            "body_part": "face",
            "format": "jpg"
        }
    ]

    test_profile = {
        "nickname": "Test User",
        "focus_parts": ["面部气色", "整体状态"],
        "skin_type": "混合肌",
    }

    # Import after path is set
    from app.services.diagnosis_service import _invoke_llm_structured

    print("\n[1] Testing _invoke_llm_structured:")
    try:
        result = await _invoke_llm_structured(test_photos, test_profile, "我想了解一下最近的皮肤状态")
        print(f"  [OK] LLM structured call success!")
        print(f"  Model: {result['model']}")
        print(f"  Directions: {len(result['directions'])} items")
        print(f"  Tags: {result['tags']}")
        print(f"  Summary: {result['summary'][:100]}...")
    except Exception as e:
        print(f"  [FAIL] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())
