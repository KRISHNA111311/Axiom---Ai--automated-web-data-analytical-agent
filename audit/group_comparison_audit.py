"""
AUD-4: Group Comparison Assumption Audit (e.g., ANOVA vs Kruskal-Wallis)
Checks: Skewness per group, variance ratio, sample size per group.
"""

import math
from typing import List
from data_contracts import ProfileBundle, AuditVerdict


def audit_group_comparison_assumptions(profile: ProfileBundle) -> AuditVerdict:
    """
    Audit group comparison assumptions.
    - |skew| > 1.0 in any group -> flag non-normality.
    - Variance ratio > 4.0 -> flag heteroscedasticity.
    - Groups with n < 5 -> excluded from formal test.
    """
    findings = []
    recommended = "ANOVA"
    excluded_groups = []

    if not profile.group_stats or not profile.group_stats.groups:
        return AuditVerdict(
            task_type="group_comparison",
            passed=True,
            findings=["No group statistics available. Skipping audit."],
            recommended_test_or_model="ANOVA",
            excluded_groups=None
        )

    groups = profile.group_stats.groups
    variances = []
    norm_issues = False
    var_issues = False

    for g in groups:
        n = g.get("n", 0)
        skew = g.get("skewness", 0.0)
        var = g.get("variance", 0.0)  # we need variance, stddev^2

        if n < 5:
            excluded_groups.append(g.get("group_name", "Unknown"))
            # We don't flag for exclusion yet, just collect

        if abs(skew) > 1.0:
            norm_issues = True
            findings.append(f"Group '{g.get('group_name')}': Skewness = {skew:.2f} (non-normal)")

        if var > 0:
            variances.append(var)

    # Check variance ratio
    if len(variances) >= 2:
        max_var = max(variances)
        min_var = min(variances)
        if min_var > 0 and max_var / min_var > 4.0:
            var_issues = True
            findings.append(f"Variance ratio: {max_var / min_var:.2f} (heteroscedasticity detected)")

    # Determine recommendation
    if norm_issues or var_issues:
        recommended = "Kruskal-Wallis (non-parametric)"
    else:
        recommended = "ANOVA"

    passed = not (norm_issues or var_issues)

    return AuditVerdict(
        task_type="group_comparison",
        passed=passed,
        findings=findings if findings else ["Assumptions met for ANOVA."],
        recommended_test_or_model=recommended,
        excluded_groups=excluded_groups if excluded_groups else None
    )