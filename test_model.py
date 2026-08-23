import os
from dotenv import load_dotenv
load_dotenv()

from agent.model_client import invoke_llm

def test_basic_prompt():
    print("🧪 Testing Gemini client with a simple prompt...")
    prompt = "What is the capital of France? Answer in one word."
    response = invoke_llm(prompt)
    print(f"✅ Response: {response.content}")
    print(f"   Input tokens: {response.input_tokens}")
    print(f"   Output tokens: {response.output_tokens}")
    print(f"   Latency: {response.latency_ms} ms")
    assert "Paris" in response.content
    print("✅ Test passed.")

if __name__ == "__main__":
    test_basic_prompt()