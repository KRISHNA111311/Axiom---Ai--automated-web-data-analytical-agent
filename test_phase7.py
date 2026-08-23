import json
from data_contracts import (
    ProfileBundle, StructuredTask, AuditVerdict,
    GroupStatsResult, SchemaProfile, TimeSeriesStatsResult, ClassBalanceResult
)
from audit.dispatcher import dispatch_audit, route_after_audit


def test_group_comparison():
    print("=== Testing Group Comparison Audit ===")
    mock_groups = [
        {"group_name": "A", "n": 50, "mean": 10, "median": 9, "std": 2, "skewness": 1.5, "kurtosis": 2.0, "variance": 4.0},
        {"group_name": "B", "n": 30, "mean": 12, "median": 11, "std": 3, "skewness": 0.5, "kurtosis": 1.0, "variance": 9.0},
        {"group_name": "C", "n": 3, "mean": 15, "median": 14, "std": 1, "skewness": 0.1, "kurtosis": 0.5, "variance": 1.0}
    ]
    profile = ProfileBundle(
        group_stats=GroupStatsResult(
            group_column="category",
            value_column="price",
            groups=mock_groups
        )
    )
    task = StructuredTask(task_type="group_comparison", target_domain="test.com")
    verdict = dispatch_audit(task, profile)

    print(f"Passed: {verdict.passed}")
    print(f"Recommendation: {verdict.recommended_test_or_model}")
    print(f"Findings: {verdict.findings}")
    print(f"Excluded: {verdict.excluded_groups}")
    print("Route:", route_after_audit(verdict, "autonomous"))
    assert verdict.recommended_test_or_model == "Kruskal-Wallis (non-parametric)"
    assert "C" in verdict.excluded_groups
    print("✅ Group comparison audit passed.\n")


def test_classification():
    print("=== Testing Classification Audit ===")
    profile = ProfileBundle(
        class_balance=ClassBalanceResult(
            label_column="label",
            class_counts={"cat": 100, "dog": 5, "bird": 2},
            imbalance_ratio=50.0
        )
    )
    task = StructuredTask(task_type="classification", target_domain="test.com")
    verdict = dispatch_audit(task, profile)
    print(f"Passed: {verdict.passed}")
    print(f"Recommendation: {verdict.recommended_test_or_model}")
    print(f"Findings: {verdict.findings}")
    assert verdict.passed == False
    print("✅ Classification audit passed.\n")


def test_timeseries():
    print("=== Testing Time-Series Audit ===")
    from data_contracts import TimeSeriesStatsResult
    profile = ProfileBundle(
        time_series_stats=TimeSeriesStatsResult(
            time_column="date",
            value_column="sales",
            rolling_mean_by_bucket=[10, 11, 12],
            rolling_var_by_bucket=[1, 1.2, 1.5],
            lag1_autocorr=0.95
        )
    )
    task = StructuredTask(task_type="timeseries", target_domain="test.com")
    verdict = dispatch_audit(task, profile)
    print(f"Passed: {verdict.passed}")
    print(f"Recommendation: {verdict.recommended_test_or_model}")
    print(f"Findings: {verdict.findings}")
    assert verdict.passed == False
    print("✅ Time-series audit passed.\n")


if __name__ == "__main__":
    test_group_comparison()
    test_classification()
    test_timeseries()
    print("🎉 All Phase 7 tests passed!")