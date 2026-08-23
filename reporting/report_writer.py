"""
Phase 15: Reporting (M12)
REP-1, REP-2, REP-3, REP-4
"""

import os
import shutil
import json
import re
from typing import List, Optional, Dict
from data_contracts import (
    StructuredTask, AuditVerdict, ExecutionResult,
    ReportBundle
)
from agent.model_client import invoke_llm


# ============================================================
# REP-1: Persist Artifacts
# ============================================================

def persist_artifacts(
    result: ExecutionResult,
    task: StructuredTask,
    verdict: AuditVerdict,
    output_dir: str = "results"
) -> ReportBundle:
    """
    REP-1: Copy sandbox artifacts to the output directory.
    Returns a ReportBundle with artifact paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    artifact_paths = []

    # Copy all artifact files (PNGs, CSVs, JSON) from the sandbox
    for src_path in result.artifact_paths:
        if os.path.exists(src_path):
            basename = os.path.basename(src_path)
            dst_path = os.path.join(output_dir, basename)
            shutil.copy2(src_path, dst_path)
            artifact_paths.append(dst_path)
            print(f"📄 Copied artifact: {basename}")

    # Also save the stdout (analysis summary) as a text file for reference
    if result.stdout:
        summary_path = os.path.join(output_dir, "analysis_output.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(result.stdout)
        artifact_paths.append(summary_path)

    # Metrics (could be extended)
    metrics = {"records_processed": len(artifact_paths)}

    return ReportBundle(
        task=task,
        audit=verdict,
        artifacts=artifact_paths,
        metrics=metrics
    )


# ============================================================
# REP-2: Generate Markdown Report
# ============================================================

def generate_markdown_report(bundle: ReportBundle) -> str:
    """
    REP-2: Use Gemini to write a human‑readable markdown report.
    Parses the structured summary from stdout to build a list of insights with charts.
    Returns the path to the generated report.md.
    """
    task = bundle.task
    verdict = bundle.audit
    artifacts = bundle.artifacts
    metrics = bundle.metrics

    # Find analysis_output.txt
    output_file = None
    for p in artifacts:
        if p.endswith("analysis_output.txt"):
            output_file = p
            break

    stdout = ""
    if output_file and os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            stdout = f.read()

    # Extract insight-chart mapping from stdout
    insights = []
    chart_filenames = []
    pattern = r"INSIGHT (\d+): (.+?)\nCHART: (.+?)(?:\n|$)"
    matches = re.findall(pattern, stdout, re.DOTALL)
    if matches:
        for num, desc, chart in matches:
            insights.append(f"Insight {num}: {desc.strip()}")
            chart_filenames.append(chart.strip())
    else:
        # Fallback: list all PNGs and infer insights from stdout (simplified)
        pngs = [os.path.basename(p) for p in artifacts if p.endswith(".png")]
        if stdout:
            # Split stdout into lines and treat each non‑empty line as an insight
            lines = [line.strip() for line in stdout.splitlines() if line.strip()]
            # Try to match each line with a PNG filename (heuristic)
            for i, line in enumerate(lines[:15]):
                # Find the first PNG mentioned in the line
                match = re.search(r'(insight_\d+_\w+\.png)', line)
                if match:
                    chart = match.group(1)
                else:
                    chart = pngs[i] if i < len(pngs) else f"chart_{i+1}.png"
                insights.append(f"Insight {i+1}: {line}")
                chart_filenames.append(chart)
        else:
            # If stdout is empty, just list PNGs
            for i, png in enumerate(pngs[:15], 1):
                insights.append(f"Insight {i}: See chart {png}")
                chart_filenames.append(png)

    # Build a summary of available charts
    artifact_filenames = [os.path.basename(p) for p in artifacts if p.endswith('.png')]
    image_links = []
    for i, (insight, chart) in enumerate(zip(insights, chart_filenames), 1):
        # Ensure chart file exists in artifact_filenames
        if chart not in artifact_filenames:
            # Try to find a matching file
            for fname in artifact_filenames:
                if chart in fname or fname in chart:
                    chart = fname
                    break
            else:
                # fallback to first available PNG
                if artifact_filenames:
                    chart = artifact_filenames[i-1] if i-1 < len(artifact_filenames) else artifact_filenames[0]
                else:
                    chart = "no_chart.png"
        image_links.append(f"![{insight}]({chart})")

    task_desc = f"Task type: {task.task_type}\n"
    if task.group_column:
        task_desc += f"Group column: {task.group_column}\n"
    if task.value_column:
        task_desc += f"Value column: {task.value_column}\n"
    if task.time_column:
        task_desc += f"Time column: {task.time_column}\n"
    if task.label_column:
        task_desc += f"Label column: {task.label_column}\n"

    audit_summary = (
        f"Audit verdict: {'PASSED' if verdict.passed else 'FAILED'}\n"
        f"Recommended test/model: {verdict.recommended_test_or_model}\n"
    )
    if verdict.findings:
        audit_summary += "Findings:\n" + "\n".join(f"- {f}" for f in verdict.findings)

    # Build a string with insights and chart links
    insights_text = "\n".join([f"{i+1}. {insight}" for i, (insight, _) in enumerate(zip(insights, chart_filenames))])
    charts_text = "\n".join([f"**Chart {i+1}:** {img}" for i, img in enumerate(image_links)])

    prompt = f"""
You are a data science report writer.

Write a clear, concise, and professional markdown report based on the analysis performed.

Task details:
{task_desc}

Audit summary:
{audit_summary}

The analysis extracted the following insights from the data:

{insights_text}

The corresponding charts are:

{charts_text}

Please write a report with the following sections:

1. **Introduction** – briefly describe the goal of the analysis.
2. **Methodology** – explain the approach and the statistical tests used.
3. **Results** – present the key findings (list the insights) and reference each chart.
4. **Visualizations** – embed each chart image using markdown syntax.
5. **Conclusion** – summarise the implications.

Use markdown formatting. Ensure each insight has its corresponding chart image next to it.

Do not add extra commentary outside the report.
"""

    try:
        response = invoke_llm(prompt)
        report_content = response.content
    except Exception as e:
        # Fallback: generate a simple report from insights and charts
        report_content = f"""
# Analysis Report

## Introduction
Analysis of data from {task.target_domain}.

## Methodology
Task type: {task.task_type}
Recommended test: {verdict.recommended_test_or_model}

## Results
{insights_text}

## Visualizations
{charts_text}

## Conclusion
See the attached charts for detailed visual insights.
"""

    report_path = "results/report.md"
    os.makedirs("results", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_path


# ============================================================
# REP-3: Escalate Failure
# ============================================================

def escalate_failure(result: ExecutionResult, task: StructuredTask) -> str:
    """REP-3: Write a failure report when retries are exhausted."""
    report_path = "results/failure_report.md"
    content = f"""
# Analysis Failure Report

The analysis could not be completed successfully.

## Task
{task}

## Error Details
- Success: {result.success}
- Duration: {result.duration_ms} ms
- Stdout: {result.stdout[:500] if result.stdout else 'None'}
- Stderr: {result.stderr[:500] if result.stderr else 'None'}

## Recommendations
- Check the input data for correctness.
- Verify that the required columns exist.
- Increase retry limit or adjust timeouts.

---
*Generated automatically by Axiom.*
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    return report_path


# ============================================================
# REP-4: Generate Partial Report (Early Termination)
# ============================================================

def generate_partial_report(
    bundle: ReportBundle,
    completed_stages: List[str]
) -> str:
    """REP-4: Write a report for early termination."""
    report_path = "results/partial_report.md"
    content = f"""
# Partial Analysis Report

The pipeline was stopped before completion.

## Completed Stages
{', '.join(completed_stages)}

## Data Summary
- Records: {bundle.metrics.get('records_processed', 'unknown')}
- Task type: {bundle.task.task_type}

## Audit Verdict
{bundle.audit.recommended_test_or_model}

## Available Artifacts
{', '.join(bundle.artifacts) if bundle.artifacts else 'None'}

---
*Partial report generated by Axiom.*
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    return report_path