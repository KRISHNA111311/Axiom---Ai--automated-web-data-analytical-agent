from data_contracts import StructuredTask, ProfileBundle, AuditVerdict, VizSpec
from visualization.viz_planner import plan_visualizations, amend_viz_plan

def test_viz():
    print("🧪 Testing Visualization Planning (VIZ-1)...")
    
    # Test group comparison
    task = StructuredTask(task_type="group_comparison", target_domain="test.com", group_column="category", value_column="price")
    verdict = AuditVerdict(task_type="group_comparison", passed=True, recommended_test_or_model="ANOVA")
    profile = ProfileBundle()  # minimal

    specs = plan_visualizations(task, profile, verdict)
    print(f"✅ Group comparison: {len(specs)} charts")
    for s in specs:
        print(f"   - {s.chart_type}: {s.title}")
    assert len(specs) == 4

    # Test regression
    task = StructuredTask(task_type="regression", target_domain="test.com", value_column="price")
    specs = plan_visualizations(task, profile, verdict)
    print(f"✅ Regression: {len(specs)} charts")
    assert len(specs) == 2

    # Test classification
    task = StructuredTask(task_type="classification", target_domain="test.com", label_column="category")
    specs = plan_visualizations(task, profile, verdict)
    print(f"✅ Classification: {len(specs)} charts")
    assert len(specs) == 2

    # Test timeseries
    task = StructuredTask(task_type="timeseries", target_domain="test.com", time_column="date", value_column="sales")
    specs = plan_visualizations(task, profile, verdict)
    print(f"✅ Timeseries: {len(specs)} charts")
    assert len(specs) == 2

    # Test VIZ-2: Add chart
    print("\n🧪 Testing Amendment (VIZ-2)...")
    amended = amend_viz_plan(specs, "add a scatter plot")
    print(f"   Added chart: {len(amended)} charts (was {len(specs)})")
    assert len(amended) == len(specs) + 1

    amended = amend_viz_plan(specs, "remove chart 1")
    print(f"   Removed chart 1: {len(amended)} charts")
    assert len(amended) == len(specs) - 1

    print("\n🎉 All Phase 12 tests passed!")

if __name__ == "__main__":
    test_viz()