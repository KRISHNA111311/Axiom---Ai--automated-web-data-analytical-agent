"""
Phase 10: Model Client (M7)
MDL-1, MDL-2
Uses the modern google.genai client.
"""

import os
import time
from typing import Optional, List, Dict, Any
from data_contracts import ModelConfig, LLMResponse

try:
    from google import genai
except ImportError:
    genai = None
    print("⚠️  google-genai not installed. Run: pip install google-genai")


# ============================================================
# MDL-1: Get Model Configuration
# ============================================================

def get_model_config() -> ModelConfig:
    """Return the default model configuration."""
    return ModelConfig(
        model_name="gemini-3.6-flash",
        temperature=0.2,
        max_output_tokens=4096
    )


# ============================================================
# MDL-2: Invoke LLM
# ============================================================

def invoke_llm(
    prompt: str,
    tools: Optional[List[Dict]] = None,
    config: Optional[ModelConfig] = None,
    max_retries: int = 3
) -> LLMResponse:
    """
    Send a prompt to Gemini and return the response.
    Uses google.genai.Client.
    """
    if config is None:
        config = get_model_config()

    # 1. Ensure API key is set
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set in environment or .env file.")

    # 2. Check library
    if genai is None:
        raise ImportError("google-genai library is not installed.")

    # 3. Create client
    client = genai.Client(api_key=api_key)

    # 4. Prepare generation config
    gen_config = {
        "temperature": config.temperature,
        "max_output_tokens": config.max_output_tokens,
    }

    # 5. Retry loop
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            response = client.models.generate_content(
                model=config.model_name,
                contents=prompt,
                config=gen_config
            )
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Extract text
            content = response.text if hasattr(response, 'text') and response.text else ""

            # Extract tool calls (if any)
            tool_calls = None
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    func_calls = []
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            func_calls.append({
                                "name": part.function_call.name,
                                "args": part.function_call.args
                            })
                    if func_calls:
                        tool_calls = func_calls

            # Token usage
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                input_tokens = getattr(usage, 'prompt_token_count', 0)
                output_tokens = getattr(usage, 'candidates_token_count', 0)

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=elapsed_ms
            )

        except Exception as e:
            error_str = str(e).lower()
            is_retryable = any(kw in error_str for kw in ["rate limit", "timeout", "429", "503", "server"])
            if is_retryable and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"⚠️  Gemini error (attempt {attempt+1}/{max_retries}): {e}")
                print(f"   Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                raise RuntimeError(f"Gemini call failed: {e}")

    raise RuntimeError(f"Gemini call failed after {max_retries} attempts.")