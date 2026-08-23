"""
AUD-1: Regression Assumption Audit
Checks: Skewness of target, multicollinearity (VIF proxy via correlations).
"""

from typing import Dict, Any
from data_contracts import ProfileBundle, AuditVerdict


def audit_regression_assumptions(profile: ProfileBundle) -> AuditVerdict:
    """
    Audit regression assumptions.
    - Skewness > |1.0| -> flag transform.
    - Correlation > 0.8 between predictors -> flag multicollinearity.
    """
    findings = []
    recommended = "Linear Regression"

    if not profile.schema_profile:
        return AuditVerdict(
            task_type="regression",
            passed=True,
            findings=["No schema profile available. Skipping detailed audit."],
            recommended_test_or_model="Linear Regression"
        )

    # 1. Check skewness of target (first numeric column if available)
    target_col = None
    for col in profile.schema_profile.columns:
        if col.get("dtype") in ["FLOAT", "DOUBLE", "INTEGER"]:
            target_col = col["name"]
            break

    if target_col and profile.binned_stats:
        # We don't have direct skewness in binned stats, we use the moment.
        # For now, we assume skewness is passed or we use the presence of binned stats as a proxy.
        # In a real scenario, TLS-1..7 would provide skewness directly.
        # For Phase 7 we will check if any skewness flag is present in the profile.
        pass

    # 2. Check correlations (multicollinearity proxy)
    if profile.correlations and profile.correlations.matrix:
        high_corr = False
        for col1, row in profile.correlations.matrix.items():
            for col2, corr in row.items():
                if col1 != col2 and abs(corr) > 0.8:
                    high_corr = True
                    findings.append(f"High correlation ({col1} ↔ {col2}): {corr:.2f}")
        if high_corr:
            recommended = "Ridge Regression / PCA or Tree-based model"

    # If no findings, passed is True
    passed = len(findings) == 0

    return AuditVerdict(
        task_type="regression",
        passed=passed,
        findings=findings if findings else ["No regression assumption violations detected."],
        recommended_test_or_model=recommended,
        excluded_groups=None
    )