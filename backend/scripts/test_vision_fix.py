"""Test vision LLM after fixing the response parsing."""
import asyncio
import sys
sys.path.insert(0, "d:/agent-project/SelfwellAgent/backend")

from app.llm import multimodal_llm
from app.llm.schemas import DiagnosisOutput
from langchain_core.messages import SystemMessage, HumanMessage


async def test():
    print("Testing fixed ArkChatModel...")

    # Test 1: Pure text (no images)
    print("\n[1] Pure text test:")
    try:
        messages = [
            SystemMessage(content="You are helpful. Respond with valid JSON only."),
            HumanMessage(content='Return valid JSON with these exact fields: directions=[{title, description, video_id}], tags=[], summary. No other text.')
        ]

        result = await multimodal_llm.with_structured_output(DiagnosisOutput).ainvoke(messages)
        print(f"  [OK] Result: {result}")
    except Exception as e:
        print(f"  [FAIL] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())
