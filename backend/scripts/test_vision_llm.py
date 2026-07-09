"""测试 vision LLM（Ark SDK）多模态调用，诊断智能分析失败原因。"""
import asyncio
import sys

# 添加 backend 到 path
sys.path.insert(0, "d:/agent-project/SelfwellAgent/backend")

from app.conf.app_config import app_config
from app.llm import multimodal_llm
from app.llm.schemas import DiagnosisOutput
from langchain_core.messages import HumanMessage, SystemMessage


async def test_vision_llm():
    print("=" * 60)
    print("Vision LLM diagnostic test")
    print("=" * 60)

    # 1. 打印当前配置
    print("\n[1] Current LLM config:")
    print(f"  multi_api_key: {app_config.llm.multi_api_key[:20]}..." if app_config.llm.multi_api_key else "  multi_api_key: (empty)")
    print(f"  multi_model: {app_config.llm.multi_model}")
    print(f"  multi_base_url: {app_config.llm.multi_base_url}")

    # 2. 测试 Ark Client 直接调用
    print("\n[2] Test Ark SDK responses.create() API:")
    try:
        ark_client = multimodal_llm._ark_client
        # 简单文本测试
        test_messages = [
            {"role": "user", "content": [{"type": "input_text", "text": "Hello, respond with OK"}]}
        ]
        response = ark_client.responses.create(
            model=app_config.llm.multi_model,
            input=test_messages,
            temperature=0.1,
            max_output_tokens=50,
        )
        print(f"  [OK] Text call success: {response.output_text[:100]}")
    except Exception as e:
        print(f"  [FAIL] Text call failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # 3. 测试多模态消息
    print("\n[3] 测试多模态消息（带图片）:")
    try:
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=[
                {"type": "text", "text": "Describe this image briefly."},
                {"type": "image_url", "image_url": {"url": "https://via.placeholder.com/100"}}
            ])
        ]

        result = await multimodal_llm.with_structured_output(DiagnosisOutput).ainvoke(messages)
        print(f"  ✓ 多模态调用成功: {result}")
    except Exception as e:
        print(f"  ✗ 多模态调用失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # 4. 测试 structured output
    print("\n[4] 测试 Structured Output:")
    try:
        messages = [
            SystemMessage(content="You are a helpful assistant. Respond only with valid JSON."),
            HumanMessage(content=[
                {"type": "text", "text": """Return JSON with these fields:
{
  "directions": [{"title": "test", "description": "test desc", "video_id": null}],
  "tags": ["test"],
  "summary": "test summary"
}"""}
            ])
        ]

        result = await multimodal_llm.with_structured_output(DiagnosisOutput).ainvoke(messages)
        print(f"  ✓ Structured output 成功: {result}")
    except Exception as e:
        print(f"  ✗ Structured output 失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_vision_llm())
