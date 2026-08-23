"""
Phase 9: Tool Functions (M5)
Thin RPC clients over the Privacy Broker (M4).
"""

from typing import List, Dict, Any, Optional
from storage.broker import broker_client_call
from data_contracts import (
    ProfileBundle, SchemaProfile, CorrelationResult, BinnedStatsResult,
    GroupStatsResult, ClassBalanceResult, TimeSeriesStatsResult,
    StructuredTask
)

# Default broker address (must match the one used in main.py)
BROKER_ADDRESS = ('localhost', 6000)


# ============================================================
# TLS-1..7: Individual aggregate calls
# ============================================================

def get_schema(table_name: str = "scraped_records") -> Dict:
    """TLS-1: Get table schema."""
    return broker_client_call("get_schema", {}, BROKER_ADDRESS)


def get_missing_values(table_name: str = "scraped_records") -> Dict:
    """TLS-2: Get missing value ratios."""
    return broker_client_call("get_missing_values", {}, BROKER_ADDRESS)


def get_correlations(columns: List[str]) -> Dict:
    """TLS-3: Get correlation matrix for given columns."""
    return broker_client_call("get_correlations", {"columns": columns}, BROKER_ADDRESS)


def get_binned_statistics(column: str, bins: int = 10) -> Dict:
    """TLS-4: Get binned histogram data for a numeric column."""
    return broker_client_call("get_binned_statistics", {"column": column, "bins": bins}, BROKER_ADDRESS)


def get_group_statistics(group_column: str, value_column: str) -> Dict:
    """TLS-5: Get per‑group statistics (mean, median, std, skew, kurtosis)."""
    return broker_client_call("get_group_statistics", {
        "group_column": group_column,
        "value_column": value_column
    }, BROKER_ADDRESS)


def get_class_balance(label_column: str) -> Dict:
    """TLS-6: Get class distribution and imbalance ratio."""
    return broker_client_call("get_class_balance", {"label_column": label_column}, BROKER_ADDRESS)


def get_stationarity_inputs(time_column: str, value_column: str) -> Dict:
    """TLS-7: Get rolling stats and lag‑1 autocorrelation for time‑series."""
    return broker_client_call("get_stationarity_inputs", {
        "time_column": time_column,
        "value_column": value_column
    }, BROKER_ADDRESS)


# ============================================================
# TLS-8: Profiling loop dispatcher
# ============================================================

def run_profiling_loop(task: StructuredTask) -> ProfileBundle:
    """
    TLS-8: Run the profiling loop based on task_type.
    Fetches only the necessary aggregates and returns a ProfileBundle.
    """
    profile = ProfileBundle()
    task_type = task.task_type

    # Always fetch schema and missing values
    schema_data = get_schema()
    profile.schema_profile = SchemaProfile(
        table_name=schema_data.get("table_name", "scraped_records"),
        columns=schema_data.get("columns", []),
        row_count=schema_data.get("row_count", 0)
    )
    profile.missing_values = get_missing_values()

    if task_type == "group_comparison":
        group_col = task.group_column or "category"
        value_col = task.value_column or "price"
        stats = get_group_statistics(group_col, value_col)
        if stats and stats.get("groups"):
            profile.group_stats = GroupStatsResult(
                group_column=stats.get("group_column", group_col),
                value_column=stats.get("value_column", value_col),
                groups=stats.get("groups", [])
            )
        # Also fetch binned stats for the value column (useful for histograms)
        binned = get_binned_statistics(value_col, 10)
        if binned:
            profile.binned_stats = BinnedStatsResult(
                column=binned.get("column", value_col),
                bin_edges=binned.get("bin_edges", []),
                counts=binned.get("counts", [])
            )

    elif task_type == "regression":
        # Fetch correlations for numeric columns
        cols = [c["name"] for c in profile.schema_profile.columns if c["dtype"] in ("DOUBLE", "FLOAT", "INTEGER")]
        if len(cols) >= 2:
            corr_data = get_correlations(cols)
            if corr_data:
                profile.correlations = CorrelationResult(
                    matrix=corr_data.get("matrix", {}),
                    columns=corr_data.get("columns", [])
                )
        # Also get binned stats for the target column (assume first numeric is target)
        target = cols[0] if cols else None
        if target:
            binned = get_binned_statistics(target, 10)
            if binned:
                profile.binned_stats = BinnedStatsResult(
                    column=binned.get("column", target),
                    bin_edges=binned.get("bin_edges", []),
                    counts=binned.get("counts", [])
                )

    elif task_type == "classification":
        label_col = task.label_column or "category"
        balance = get_class_balance(label_col)
        if balance:
            profile.class_balance = ClassBalanceResult(
                label_column=balance.get("label_column", label_col),
                class_counts=balance.get("class_counts", {}),
                imbalance_ratio=balance.get("imbalance_ratio", 0.0)
            )

    elif task_type == "timeseries":
        time_col = task.time_column or "date"
        value_col = task.value_column or "value"
        ts_data = get_stationarity_inputs(time_col, value_col)
        if ts_data:
            profile.time_series_stats = TimeSeriesStatsResult(
                time_column=time_col,
                value_column=value_col,
                rolling_mean_by_bucket=ts_data.get("rolling_mean_by_bucket", []),
                rolling_var_by_bucket=ts_data.get("rolling_var_by_bucket", []),
                lag1_autocorr=ts_data.get("lag1_autocorr", 0.0)
            )

    # Return the bundle (other fields remain None if not applicable)
    return profile


# ============================================================
# TLS-9: Fallback when db_enabled=False (optional)
# ============================================================

def bypass_db_profile(data_source_path: str, task: StructuredTask) -> ProfileBundle:
    """
    TLS-9: Fallback profile generation from a Parquet/CSV file.
    Used when db_enabled=False but sandbox_enabled=True.
    """
    import pandas as pd
    if data_source_path.endswith(".parquet"):
        df = pd.read_parquet(data_source_path)
    else:
        df = pd.read_csv(data_source_path)

    profile = ProfileBundle()
    # Build schema profile from DataFrame
    columns = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        null_ratio = df[col].isna().sum() / len(df)
        columns.append({"name": col, "dtype": dtype, "null_ratio": null_ratio})
    profile.schema_profile = SchemaProfile(
        table_name="snapshot",
        columns=columns,
        row_count=len(df)
    )
    # Optionally compute group stats if needed
    if task.task_type == "group_comparison" and task.group_column and task.value_column:
        if task.group_column in df and task.value_column in df:
            groups = []
            for name, group in df.groupby(task.group_column):
                vals = group[task.value_column].dropna()
                if len(vals) > 0:
                    groups.append({
                        "group_name": str(name),
                        "n": len(vals),
                        "mean": vals.mean(),
                        "median": vals.median(),
                        "std": vals.std(),
                        "skewness": vals.skew(),
                        "kurtosis": vals.kurtosis(),
                        "variance": vals.var()
                    })
            if groups:
                profile.group_stats = GroupStatsResult(
                    group_column=task.group_column,
                    value_column=task.value_column,
                    groups=groups
                )
    return profile