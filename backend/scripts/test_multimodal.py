"""Test multimodal (vision) LLM call with fixed URL generation."""
import asyncio
import sys
sys.path.insert(0, "d:/agent-project/SelfwellAgent/backend")

from app.llm import multimodal_llm
from app.llm.schemas import DiagnosisOutput
from langchain_core.messages import SystemMessage, HumanMessage


async def test():
    print("Testing multimodal (vision) LLM call with fixed URL generation...")

    # Test with a publicly accessible image (using a test image)
    print("\n[1] Multimodal test with accessible image:")
    try:
        # Using a publicly accessible image from a test service
        test_image_url = "https://www.w3schools.com/css/paris.jpg"

        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=[
                {"type": "text", "text": "Briefly describe what you see in this image in one sentence."},
                {"type": "image_url", "image_url": {"url": test_image_url}}
            ])
        ]

        # First test the API directly
        result = await multimodal_llm.with_structured_output(DiagnosisOutput).ainvoke(messages)
        print(f"  [OK] Multimodal call success!")
        print(f"  Result directions: {len(result.directions)} items")
        print(f"  Result tags: {result.tags}")
        print(f"  Result summary: {result.summary[:100]}...")
    except Exception as e:
        print(f"  [FAIL] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())
