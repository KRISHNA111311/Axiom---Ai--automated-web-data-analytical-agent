import os
import tempfile
from data_contracts import (
    StructuredTask, AuditVerdict, ExecutionResult,
    ReportBundle
)
from reporting.report_writer import persist_artifacts, generate_markdown_report

def test_report():
    print("🧪 Testing Reporting (Phase 15)...")

    # 1. Create a dummy ExecutionResult with some artifact paths
    # We'll create dummy PNG files in a temp dir
    temp_dir = tempfile.mkdtemp(prefix="report_test_")
    artifact_paths = []
    for i in range(2):
        fname = f"chart_{i+1}.png"
        path = os.path.join(temp_dir, fname)
        with open(path, "w") as f:
            f.write("dummy PNG content")
        artifact_paths.append(path)

    result = ExecutionResult(
        success=True,
        stdout="Group means:\nA: 12.33\nB: 22.50",
        stderr="",
        artifact_paths=artifact_paths,
        duration_ms=1234
    )

    # 2. Create task and verdict
    task = StructuredTask(
        task_type="group_comparison",
        target_domain="books.toscrape.com",
        group_column="category",
        value_column="price",
        visualization_requested=True
    )
    verdict = AuditVerdict(
        task_type="group_comparison",
        passed=True,
        findings=[],
        recommended_test_or_model="ANOVA"
    )

    # 3. Persist artifacts
    output_dir = "results"
    bundle = persist_artifacts(result, task, verdict, output_dir)
    print(f"   Artifacts persisted: {bundle.artifacts}")

    # 4. Generate report (this calls Gemini – optional; we can mock for testing)
    # If you want to test with real Gemini, uncomment the next line
    # report_path = generate_markdown_report(bundle)
    # print(f"   Report generated: {report_path}")

    # 5. Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    print("✅ Report test completed.")

if __name__ == "__main__":
    test_report()