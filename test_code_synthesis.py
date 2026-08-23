


## 🧪 Test Phase 13


import os
from dotenv import load_dotenv
load_dotenv()

from data_contracts import (
    StructuredTask, ProfileBundle, AuditVerdict, VizSpec,
    GeneratedScript
)
from execution.code_synthesis import (
    build_codegen_prompt,
    synthesize_analysis_code,
    self_heal_script,
    apply_user_prompt_amendments,
    _extract_code_from_response
)

def test_prompt_building():
    print("🧪 Testing GEN-1: Build CodeGen Prompt...")
    task = StructuredTask(
        task_type="group_comparison",
        target_domain="test.com",
        group_column="category",
        value_column="price"
    )
    profile = ProfileBundle()
    # Add minimal schema
    from data_contracts import SchemaProfile
    profile.schema_profile = SchemaProfile(
        table_name="snapshot",
        columns=[{"name": "category", "dtype": "VARCHAR", "null_ratio": 0.0},
                 {"name": "price", "dtype": "DOUBLE", "null_ratio": 0.0}],
        row_count=100
    )
    verdict = AuditVerdict(
        task_type="group_comparison",
        passed=False,
        findings=["Skewness > 1.0", "Variance ratio > 4.0"],
        recommended_test_or_model="Kruskal-Wallis",
        excluded_groups=["Travel"]
    )
    viz_specs = [
        VizSpec("box", "category", "price", "Box Plot", "Category", "Price", "box.png"),
        VizSpec("bar", "category", "price", "Bar Chart", "Category", "Price", "bar.png")
    ]
    prompt = build_codegen_prompt(task, profile, verdict, viz_specs)
    assert "Kruskal-Wallis" in prompt
    assert "box.png" in prompt
    print("✅ Prompt built successfully.")
    return prompt

def test_code_extraction():
    print("🧪 Testing code extraction...")
    sample = "```python\nprint('Hello')\n```"
    code = _extract_code_from_response(sample)
    assert code == "print('Hello')"
    sample = "Some text\n```python\nx = 1\n```\nmore text"
    code = _extract_code_from_response(sample)
    assert code == "x = 1"
    sample = "No code block"
    code = _extract_code_from_response(sample)
    assert code is None
    print("✅ Code extraction works.")

def test_synthesize():
    print("🧪 Testing GEN-2: Code synthesis (will call Gemini)...")
    prompt = test_prompt_building()
    script = synthesize_analysis_code(prompt)
    print(f"Generated script (first 100 chars): {script.code[:100]}...")
    assert script.attempt_number == 1
    assert "import" in script.code or "pandas" in script.code
    print("✅ Code synthesis works.")

def test_self_heal():
    print("🧪 Testing GEN-3: Self-healing...")
    original = GeneratedScript(
        code="import pandas as pd\ndf = pd.read_parquet('snapshot.parquet')\nprint(df)",
        script_path="script.py",
        attempt_number=1
    )
    error = "FileNotFoundError: [Errno 2] No such file or directory: 'snapshot.parquet'"
    healed = self_heal_script(original, error)
    print(f"Healed script (first 100 chars): {healed.code[:100]}...")
    assert healed.attempt_number == 2
    # Typically, self-heal will add a try/except or check file existence
    print("✅ Self-healing worked.")

if __name__ == "__main__":
    test_code_extraction()
    prompt = test_prompt_building()
    # Optional: uncomment to test actual Gemini calls (costs API credits)
    # test_synthesize()
    # test_self_heal()
    print("🎉 All Phase 13 tests passed (basic) – Gemini calls commented out to save credits.")