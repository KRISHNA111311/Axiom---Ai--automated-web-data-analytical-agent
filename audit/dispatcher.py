"""
AUD-5, AUD-6, AUD-7: Dispatcher, Route logic, and User amendments.
"""

from data_contracts import ProfileBundle, AuditVerdict, StructuredTask
from audit.regression_audit import audit_regression_assumptions
from audit.classification_audit import audit_classification_assumptions
from audit.timeseries_audit import audit_timeseries_assumptions
from audit.group_comparison_audit import audit_group_comparison_assumptions


def dispatch_audit(task: StructuredTask, profile: ProfileBundle) -> AuditVerdict:
    """
    AUD-5: Route to the appropriate audit function based on task_type.
    """
    task_type = task.task_type

    if task_type == "regression":
        return audit_regression_assumptions(profile)
    elif task_type == "classification":
        return audit_classification_assumptions(profile)
    elif task_type == "timeseries":
        return audit_timeseries_assumptions(profile)
    elif task_type == "group_comparison":
        return audit_group_comparison_assumptions(profile)
    else:
        # Fallback: generic pass
        return AuditVerdict(
            task_type=task_type,
            passed=True,
            findings=[f"Unknown task type '{task_type}'. No audit performed."],
            recommended_test_or_model="None"
        )


def route_after_audit(verdict: AuditVerdict, mode: str) -> str:
    """
    AUD-6: Decide whether to proceed, halt, or proceed with alternative.
    Returns: "proceed", "halt", or "proceed_with_alternative".
    """
    if verdict.passed:
        return "proceed"

    if mode in ["autonomous", "interactive"]:
        # In autonomous/interactive, we proceed with the recommended alternative
        return "proceed_with_alternative"
    else:
        # Assisted mode: halt for human sign-off
        return "halt"


def apply_user_amendments(verdict: AuditVerdict, amendment_text: str) -> AuditVerdict:
    """
    AUD-7: Apply user amendments to override audit recommendations.
    Example: "force ANOVA" -> overrides recommended_test_or_model.
    """
    text = amendment_text.lower()
    if "anova" in text:
        verdict.recommended_test_or_model = "ANOVA"
        verdict.findings.append("User override: forced ANOVA.")
        verdict.passed = True
    elif "kruskal" in text or "kruskal-wallis" in text:
        verdict.recommended_test_or_model = "Kruskal-Wallis"
        verdict.findings.append("User override: forced Kruskal-Wallis.")
        verdict.passed = True

    # Allow excluding groups
    import re
    match = re.search(r'exclude\s+(\w+)', text)
    if match:
        group_name = match.group(1)
        if verdict.excluded_groups is None:
            verdict.excluded_groups = []
        if group_name not in verdict.excluded_groups:
            verdict.excluded_groups.append(group_name)
            verdict.findings.append(f"User override: excluded group '{group_name}'.")

    return verdict