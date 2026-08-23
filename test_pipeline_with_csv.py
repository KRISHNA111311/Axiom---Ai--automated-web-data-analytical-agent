#!/usr/bin/env python3
"""
Test the full pipeline: DB -> CSV -> Gemini script -> Sandbox -> Gemini report.
"""

import os
import json
import tempfile
import shutil
import pandas as pd
import duckdb
from dotenv import load_dotenv
load_dotenv()

from data_contracts import GeneratedScript, SandboxPolicy
from agent.model_client import invoke_llm
from execution.sandbox_runner import execute_in_sandbox


def get_data_from_db(db_path: str = "results/data.duckdb") -> pd.DataFrame:
    """Read data from DuckDB, or create a dummy DataFrame if DB is missing."""
    if os.path.exists(db_path):
        conn = duckdb.connect(db_path)
        df = conn.execute("SELECT * FROM scraped_records").df()
        conn.close()
        print(f"✅ Loaded {len(df)} rows from {db_path}")
        return df
    else:
        print("⚠️  Database not found. Creating dummy data.")
        df = pd.DataFrame({
            "category": ["A", "A", "B", "B", "C", "C", "A", "B", "C"],
            "price": [10, 12, 20, 22, 30, 35, 11, 21, 32],
            "rating": [4.5, 4.0, 3.5, 3.0, 4.8, 4.2, 4.1, 3.8, 4.5]
        })
        return df


def generate_analysis_script(
    columns: list,
    sample_rows: list,
    summary: dict
) -> str:
    """Ask Gemini to write a Python script that analyzes the CSV."""
    prompt = f"""
You are a data analyst. Write a Python script that:

- Reads a CSV file from: /data/data.csv
- The CSV has columns: {columns}
- Here is a sample of the first 5 rows: {sample_rows}
- Here is a summary: {summary}

The script should:
- Print basic statistics (mean, median, std) for numeric columns.
- Create two charts:
  1. A histogram of the 'price' column.
  2. A boxplot of 'price' by 'category'.
- Save them as '/workspace/histogram.png' and '/workspace/boxplot.png'.
- Print a summary of findings.

Use pandas, matplotlib, seaborn. Use absolute paths for saving images.
Return ONLY the Python code inside ```python ... ```.
"""
    response = invoke_llm(prompt)
    content = response.content.strip()
    if "```python" in content:
        code = content.split("```python")[1].split("```")[0].strip()
    elif "```" in content:
        code = content.split("```")[1].split("```")[0].strip()
    else:
        code = content
    return code


def generate_report_from_output(stdout: str, chart_filenames: list) -> str:
    """Ask Gemini to write a report based on the script's output and charts."""
    prompt = f"""
You are a data science report writer.

The analysis script produced the following output:

{stdout[:2000]}

The following charts were generated:
{', '.join(chart_filenames) if chart_filenames else 'None'}

Write a markdown report with sections:
- Introduction
- Methodology
- Results
- Visualizations (reference each chart)
- Conclusion

Be concise and professional.
"""
    response = invoke_llm(prompt)
    return response.content.strip()


def main():
    print("🧪 Testing full pipeline with CSV...")

    # 1. Get data
    df = get_data_from_db()
    print(f"Data shape: {df.shape}")
    print("Columns:", df.columns.tolist())

    # 2. Export to CSV in a temporary directory
    work_dir = tempfile.mkdtemp(prefix="pipeline_test_")
    csv_path = os.path.join(work_dir, "data.csv")
    df.to_csv(csv_path, index=False)
    print(f"✅ Exported CSV to: {csv_path}")

    # 3. Prepare summary for Gemini
    columns = df.columns.tolist()
    sample_rows = df.head(5).to_dict(orient="records")
    summary = df.describe().to_dict()

    print("\n📝 Asking Gemini to generate analysis script...")
    try:
        script_code = generate_analysis_script(columns, sample_rows, summary)
    except Exception as e:
        print(f"❌ Gemini failed: {e}. Using fallback script.")
        script_code = """
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
df = pd.read_csv("/data/data.csv")
print(df.describe())
plt.figure()
df['price'].hist()
plt.savefig("/workspace/histogram.png")
plt.close()
plt.figure()
sns.boxplot(data=df, x='category', y='price')
plt.savefig("/workspace/boxplot.png")
plt.close()
print("Charts saved.")
"""

    print("✅ Script generated.")

    # 4. Save script and run in sandbox
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

    # 5. Collect artifacts
    artifact_files = []
    for src in result.artifact_paths:
        if os.path.exists(src):
            basename = os.path.basename(src)
            shutil.copy2(src, f"output_{basename}")
            artifact_files.append(basename)
            print(f"📄 Copied artifact: {basename}")

    # 6. Ask Gemini to generate final report
    if result.stdout or artifact_files:
        print("\n📝 Asking Gemini for final report...")
        try:
            report = generate_report_from_output(result.stdout, artifact_files)
            report_path = "pipeline_report.md"
            with open(report_path, "w") as f:
                f.write(report)
            print(f"✅ Report saved to {report_path}")
        except Exception as e:
            print(f"❌ Gemini report generation failed: {e}")
    else:
        print("⚠️  No output or artifacts to report on.")

    # 7. Cleanup
    shutil.rmtree(work_dir)
    print("\n✅ Test completed.")


if __name__ == "__main__":
    main()