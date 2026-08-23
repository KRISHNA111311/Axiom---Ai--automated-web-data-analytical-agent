#!/usr/bin/env python3
import os
import json
import tempfile
import subprocess
import shutil
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from data_contracts import GeneratedScript, SandboxPolicy
from agent.model_client import invoke_llm
from execution.sandbox_runner import execute_in_sandbox


def create_dummy_parquet(output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    df = pd.DataFrame({
        "category": ["A", "A", "B", "B", "C", "C"],
        "price": [10, 12, 20, 22, 30, 35],
        "rating": [4.5, 4.0, 3.5, 3.0, 4.8, 4.2]
    })
    file_path = os.path.join(output_dir, "snapshot.parquet")
    df.to_parquet(file_path)
    print(f"✅ Created dummy Parquet: {file_path}")
    return file_path


def get_fallback_script() -> str:
    """Return a known‑working script that reads the Parquet and creates a chart."""
    return '''
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

print("Current working directory:", os.getcwd())
df = pd.read_parquet("/data/snapshot.parquet")
print("Data shape:", df.shape)
print("Mean price per category:")
print(df.groupby("category")["price"].mean())

plt.figure(figsize=(10,6))
sns.boxplot(data=df, x="category", y="price")
plt.title("Price Distribution by Category")
plt.xlabel("Category")
plt.ylabel("Price")
plt.savefig("/workspace/boxplot.png", bbox_inches="tight")
plt.close()
print("Chart saved to /workspace/boxplot.png")
print("Files in /workspace:", os.listdir("/workspace"))
'''


def ask_gemini_for_script() -> str:
    """Try Gemini; if it fails, return the fallback script."""
    prompt = """
Write a Python script that:
- Reads a Parquet file from: /data/snapshot.parquet
- Creates a boxplot showing the distribution of 'price' for each 'category'.
- Saves the plot as '/workspace/boxplot.png'.
- Prints a summary (mean price per category).
- Prints the current working directory and lists files.

Use pandas, matplotlib, and seaborn.
Return ONLY the Python code inside ```python ... ```.
"""
    try:
        response = invoke_llm(prompt)
        content = response.content.strip()
        if "```python" in content:
            code = content.split("```python")[1].split("```")[0].strip()
        elif "```" in content:
            code = content.split("```")[1].split("```")[0].strip()
        else:
            code = content
        return code
    except Exception as e:
        print(f"⚠️  Gemini failed ({e}). Using fallback script.")
        return get_fallback_script()


def main():
    print("🧪 Testing Gemini + Sandbox integration...")

    # 1. Create dummy data
    work_dir = tempfile.mkdtemp(prefix="gemini_sandbox_")
    parquet_path = create_dummy_parquet(work_dir)

    # 2. Get script (try Gemini, fallback)
    print("\n📝 Getting script...")
    script_code = ask_gemini_for_script()
    print(f"✅ Script ({len(script_code)} chars)")
    print("📄 Script:\n", script_code)

    # 3. Save script
    script_path = os.path.join(work_dir, "script.py")
    with open(script_path, "w") as f:
        f.write(script_code)

    script = GeneratedScript(
        code=script_code,
        script_path=script_path,
        attempt_number=1
    )

    policy = SandboxPolicy(
        network_mode="none",
        memory_limit_mb=1024,
        cpu_limit=1.0,
        timeout_sec=30
    )

    print("\n🐳 Running script in sandbox...")
    result = execute_in_sandbox(script, policy, work_dir)

    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_ms} ms")
    if result.stdout:
        print("   stdout:\n", result.stdout)
    if result.stderr:
        print("   stderr:\n", result.stderr)

    # 4. List files
    print("\n📁 Files in work_dir:", os.listdir(work_dir))
    print("📁 Artifact paths from result:", result.artifact_paths)

    # 5. Check for PNG
    png_files = [f for f in os.listdir(work_dir) if f.endswith(".png")]
    if png_files:
        print("\n📊 Charts found manually:")
        for fname in png_files:
            print(f"   - {fname}")
            shutil.copy(os.path.join(work_dir, fname), f"output_{fname}")
            print(f"   -> Copied to output_{fname}")
    else:
        print("\n⚠️  No charts were found in work_dir.")

    # 6. Cleanup
    shutil.rmtree(work_dir)
    print("\n✅ Test completed.")


if __name__ == "__main__":
    main()