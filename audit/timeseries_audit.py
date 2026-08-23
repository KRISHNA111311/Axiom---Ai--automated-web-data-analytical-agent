"""
AUD-3: Time-Series Assumption Audit
Checks: Lag-1 autocorrelation > 0.8 (likely non-stationary).
"""

from data_contracts import ProfileBundle, AuditVerdict


def audit_timeseries_assumptions(profile: ProfileBundle) -> AuditVerdict:
    """
    Audit time-series assumptions.
    - lag1_autocorr > 0.8 -> flag non-stationary, recommend differencing.
    """
    findings = []
    recommended = "ARIMA"

    if not profile.time_series_stats:
        return AuditVerdict(
            task_type="timeseries",
            passed=True,
            findings=["No time-series stats available. Skipping audit."],
            recommended_test_or_model="ARIMA"
        )

    lag1 = profile.time_series_stats.lag1_autocorr

    if lag1 > 0.8:
        findings.append(f"High lag-1 autocorrelation: {lag1:.3f}. Data is likely non-stationary.")
        recommended = "ARIMA with differencing (or use ADF test)"
    else:
        findings.append(f"Lag-1 autocorrelation acceptable: {lag1:.3f}")

    passed = len(findings) == 0 or lag1 <= 0.8

    return AuditVerdict(
        task_type="timeseries",
        passed=passed,
        findings=findings,
        recommended_test_or_model=recommended,
        excluded_groups=None
    )