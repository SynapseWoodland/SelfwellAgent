"""Debug the actual Ark API response."""
import asyncio
import sys
sys.path.insert(0, "d:/agent-project/SelfwellAgent/backend")

from app.llm import multimodal_llm
from app.conf.app_config import app_config


async def test():
    print("Testing actual Ark API response...")

    ark_client = multimodal_llm._ark_client

    # Test with simple prompt
    test_messages = [
        {"role": "user", "content": [{"type": "input_text", "text": "Respond with exactly: HELLO"}]}
    ]

    print("\n[1] Direct Ark API call:")
    try:
        response = ark_client.responses.create(
            model=app_config.llm.multi_model,
            input=test_messages,
            temperature=0.1,
            max_output_tokens=50,
        )
        print(f"  Response type: {type(response)}")
        print(f"  Response fields: output, output_text, text")

        # Try to extract text using our method
        text = multimodal_llm._extract_text_from_response(response)
        print(f"  Extracted text: '{text}'")

        # Print raw response
        print(f"\n  Raw response model_dump:")
        print(response.model_dump())

    except Exception as e:
        print(f"  [FAIL] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())
