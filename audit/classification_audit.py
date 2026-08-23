"""
AUD-2: Classification Assumption Audit
Checks: Class imbalance ratio.
"""

from data_contracts import ProfileBundle, AuditVerdict


def audit_classification_assumptions(profile: ProfileBundle) -> AuditVerdict:
    """
    Audit classification assumptions.
    - Imbalance ratio > 3.0 -> moderate, recommend class-weighting.
    - Imbalance ratio > 10.0 -> severe, recommend resampling.
    """
    findings = []
    recommended = "Logistic Regression / Random Forest"

    if not profile.class_balance or not profile.class_balance.class_counts:
        return AuditVerdict(
            task_type="classification",
            passed=True,
            findings=["No class balance information available. Skipping audit."],
            recommended_test_or_model="Logistic Regression"
        )

    counts = list(profile.class_balance.class_counts.values())
    if len(counts) < 2:
        return AuditVerdict(
            task_type="classification",
            passed=True,
            findings=["Only one class detected. Classification may not be needed."],
            recommended_test_or_model="Logistic Regression"
        )

    majority = max(counts)
    minority = min(counts)
    ratio = majority / minority if minority > 0 else float('inf')

    if ratio > 10.0:
        findings.append(f"Severe class imbalance: {ratio:.2f}. Recommend resampling.")
        recommended = "Resampling (SMOTE/ADASYN) + XGBoost"
    elif ratio > 3.0:
        findings.append(f"Moderate class imbalance: {ratio:.2f}. Recommend class weighting.")
        recommended = "Random Forest with class_weight='balanced'"

    passed = len(findings) == 0

    return AuditVerdict(
        task_type="classification",
        passed=passed,
        findings=findings if findings else ["No classification assumption violations."],
        recommended_test_or_model=recommended,
        excluded_groups=None
    )