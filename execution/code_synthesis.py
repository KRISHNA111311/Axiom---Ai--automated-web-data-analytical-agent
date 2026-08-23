"""
Phase 13: Code Synthesis & Self-Healing (M10)
GEN-1, GEN-2, GEN-3, GEN-4
"""

import re
from typing import List, Optional

from data_contracts import (
    StructuredTask,
    ProfileBundle,
    AuditVerdict,
    VizSpec,
    GeneratedScript,
)
from agent.model_client import invoke_llm


def build_codegen_prompt(
    task: StructuredTask,
    profile: ProfileBundle,
    verdict: AuditVerdict,
    viz_specs: List[VizSpec],
) -> str:
    """GEN-1: Build a detailed prompt for Gemini to write analysis code."""

    task_desc = f"Task type: {task.task_type}\n"

    if task.group_column:
        task_desc += f"Group column: {task.group_column}\n"

    if task.value_column:
        task_desc += f"Value column: {task.value_column}\n"

    if task.time_column:
        task_desc += f"Time column: {task.time_column}\n"

    if task.label_column:
        task_desc += f"Label column: {task.label_column}\n"

    profile_summary = "Data profile:\n"

    if profile.schema_profile:
        profile_summary += (
            f"- {profile.schema_profile.row_count} rows, "
            f"{len(profile.schema_profile.columns)} columns\n"
        )

    if profile.group_stats:
        profile_summary += (
            f"- {len(profile.group_stats.groups)} groups "
            f"(group column: {profile.group_stats.group_column})\n"
        )

    if profile.missing_values:
        missing = [
            f"{column}: {percentage:.2%}"
            for column, percentage in profile.missing_values.items()
            if percentage > 0
        ]

        if missing:
            profile_summary += (
                f"- Missing values: {', '.join(missing)}\n"
            )

    audit_summary = (
        f"Audit verdict: {'PASSED' if verdict.passed else 'FAILED'}\n"
    )

    audit_summary += (
        f"Recommended test/model: "
        f"{verdict.recommended_test_or_model}\n"
    )

    if verdict.findings:
        audit_summary += "Findings:\n"
        audit_summary += "\n".join(
            f"- {finding}" for finding in verdict.findings
        )
        audit_summary += "\n"

    viz_summary = "Planned visualizations:\n"

    for index, spec in enumerate(viz_specs, 1):
        viz_summary += (
            f"{index}. {spec.chart_type} chart: "
            f"{spec.title} "
            f"(saved as {spec.output_filename})\n"
        )

    if profile.schema_profile:
        col_names = ", ".join(
            column["name"]
            for column in profile.schema_profile.columns
        )
    else:
        col_names = "unknown"

    prompt = f"""
You are an expert data analyst and Python programmer.

Write robust Python code to analyze the given data.

TASK DETAILS:
{task_desc}

DATA PROFILE:
{profile_summary}

AUDIT:
{audit_summary}

PLANNED VISUALIZATIONS:
{viz_summary}

AVAILABLE COLUMNS:
{col_names}

The data is stored in a mounted read-only Parquet file:

/data/snapshot.parquet

Requirements:

1. Read the Parquet file using pandas.
2. Perform thorough exploratory data analysis.
3. Generate at least 15 distinct meaningful insights.
4. Generate one labelled chart for each insight.
5. Save all charts as PNG files inside /workspace/.
6. Use absolute paths such as:
   /workspace/insight_1_distribution.png
7. Use descriptive chart titles and axis labels.
8. Handle missing values robustly.
9. Handle numeric and categorical columns safely.
10. Do not assume that a time column exists.
11. Do not assume that a group column exists.
12. Use the recommended test/model from the audit where applicable.
13. Use matplotlib and/or seaborn.
14. Close figures after saving.
15. The script must work in a non-interactive environment.
16. Avoid duplicate insights.
17. Print the complete insight summary at the end.

The final printed output MUST use this format:

INSIGHT 1: description
CHART: insight_1_filename.png

INSIGHT 2: description
CHART: insight_2_filename.png

Continue until at least INSIGHT 15.

IMPORTANT:
Return ONLY Python source code.
Do not return explanations.
Do not return markdown.
Do not return a code block.
"""

    return prompt


def synthesize_analysis_code(prompt: str) -> GeneratedScript:
    """GEN-2: Generate analysis code using the LLM."""

    response = invoke_llm(prompt)

    code = _extract_code_from_response(response.content)

    if not code:
        code = response.content.strip()

    return GeneratedScript(
        code=code,
        script_path="generated_script.py",
        attempt_number=1,
    )


def self_heal_script(
    previous_script: GeneratedScript,
    stderr: str,
) -> GeneratedScript:
    """GEN-3: Repair a previously generated script."""

    prompt = f"""
The following Python script failed during execution.

ERROR:
{stderr}

ORIGINAL SCRIPT:
{previous_script.code}

Fix the script.

Requirements:

1. Return the complete corrected Python script.
2. Preserve the original functionality.
3. Preserve generation of at least 15 insights.
4. Preserve chart generation.
5. Preserve the INSIGHT and CHART output format.
6. Handle missing values safely.
7. Handle unexpected data types safely.
8. Save charts using absolute paths under /workspace/.
9. Do not provide explanations.
10. Return ONLY Python source code.
11. Do not use markdown or code fences.
"""

    response = invoke_llm(prompt)

    code = _extract_code_from_response(response.content)

    if not code:
        code = response.content.strip()

    return GeneratedScript(
        code=code,
        script_path=previous_script.script_path,
        attempt_number=previous_script.attempt_number + 1,
    )


def apply_user_prompt_amendments(
    prompt_text: str,
    amendment_text: str,
) -> str:
    """GEN-4: Apply a user amendment to the code-generation prompt."""

    return (
        prompt_text
        + "\n\nUSER AMENDMENT:\n"
        + amendment_text
    )


def _extract_code_from_response(
    content: str,
) -> Optional[str]:
    """Extract Python code from an LLM response."""

    if not content:
        return None

    content = content.strip()

    # Case 1: Python markdown block
    pattern = r"```python\s*(.*?)```"

    matches = re.findall(
        pattern,
        content,
        re.DOTALL | re.IGNORECASE,
    )

    if matches:
        return matches[0].strip()

    # Case 2: Generic markdown code block
    pattern = r"```\s*(.*?)```"

    matches = re.findall(
        pattern,
        content,
        re.DOTALL,
    )

    if matches:
        return matches[0].strip()

    # Case 3: LLM returned plain Python
    return content