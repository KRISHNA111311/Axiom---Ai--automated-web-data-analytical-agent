"""
Phase 12: Visualization Planning (M9)
VIZ-1, VIZ-2
"""

from typing import List, Optional
from data_contracts import StructuredTask, ProfileBundle, AuditVerdict, VizSpec


# ============================================================
# VIZ-1: Plan Visualizations
# ============================================================

def plan_visualizations(
    task: StructuredTask,
    profile: ProfileBundle,
    verdict: AuditVerdict
) -> List[VizSpec]:
    """
    VIZ-1: Plan charts based on task type, profile, and audit verdict.
    """
    specs = []
    task_type = task.task_type

    if task_type == "group_comparison":
        # Group comparison: box plot, bar chart with error bars, histogram, count chart
        group_col = task.group_column or "category"
        value_col = task.value_column or "price"

        # 1. Box plot
        specs.append(VizSpec(
            chart_type="box",
            x=group_col,
            y=value_col,
            title=f"Distribution of {value_col} by {group_col}",
            x_label=group_col,
            y_label=value_col,
            output_filename="box_plot.png"
        ))

        # 2. Bar chart with error bars (mean ± 1 SD)
        specs.append(VizSpec(
            chart_type="bar",
            x=group_col,
            y=value_col,
            title=f"Average {value_col} by {group_col} (± 1 SD)",
            x_label=group_col,
            y_label=f"Mean {value_col}",
            output_filename="bar_chart.png"
        ))

        # 3. Histogram of the value column
        specs.append(VizSpec(
            chart_type="histogram",
            x=value_col,
            y=None,
            title=f"Distribution of {value_col} (All Groups)",
            x_label=value_col,
            y_label="Count",
            output_filename="histogram.png"
        ))

        # 4. Count chart (number of items per group)
        specs.append(VizSpec(
            chart_type="count",
            x=group_col,
            y=None,
            title=f"Number of Items per {group_col}",
            x_label=group_col,
            y_label="Count",
            output_filename="count_chart.png"
        ))

    elif task_type == "regression":
        # Scatter plot, residuals plot (to be generated in sandbox), QQ plot
        value_col = task.value_column or "target"
        # We can plan a scatter plot of predicted vs actual (will be done in sandbox)
        specs.append(VizSpec(
            chart_type="scatter",
            x="actual",
            y="predicted",
            title=f"Actual vs Predicted {value_col}",
            x_label="Actual",
            y_label="Predicted",
            output_filename="scatter.png"
        ))
        specs.append(VizSpec(
            chart_type="histogram",
            x="residuals",
            y=None,
            title="Distribution of Residuals",
            x_label="Residuals",
            y_label="Count",
            output_filename="residuals.png"
        ))

    elif task_type == "classification":
        # Confusion matrix, ROC curve, class distribution
        label_col = task.label_column or "label"
        specs.append(VizSpec(
            chart_type="confusion_matrix",
            x="predicted",
            y="actual",
            title="Confusion Matrix",
            x_label="Predicted",
            y_label="Actual",
            output_filename="confusion_matrix.png"
        ))
        specs.append(VizSpec(
            chart_type="bar",
            x=label_col,
            y=None,
            title=f"Class Distribution for {label_col}",
            x_label=label_col,
            y_label="Count",
            output_filename="class_distribution.png"
        ))

    elif task_type == "timeseries":
        # Line plot, autocorrelation plot, decomposition
        time_col = task.time_column or "date"
        value_col = task.value_column or "value"
        specs.append(VizSpec(
            chart_type="line",
            x=time_col,
            y=value_col,
            title=f"{value_col} over {time_col}",
            x_label=time_col,
            y_label=value_col,
            output_filename="timeseries.png"
        ))
        specs.append(VizSpec(
            chart_type="autocorrelation",
            x="lag",
            y="correlation",
            title="Autocorrelation Plot",
            x_label="Lag",
            y_label="Autocorrelation",
            output_filename="autocorrelation.png"
        ))

    # If no charts planned (fallback), add a generic histogram
    if not specs:
        specs.append(VizSpec(
            chart_type="histogram",
            x="value",
            y=None,
            title="Data Distribution",
            x_label="Value",
            y_label="Frequency",
            output_filename="histogram.png"
        ))

    return specs


# ============================================================
# VIZ-2: Amend Visualization Plan
# ============================================================

def amend_viz_plan(viz_specs: List[VizSpec], amendment_text: str) -> List[VizSpec]:
    """
    VIZ-2: Add/remove charts based on user amendment (keyword-based).
    """
    text = amendment_text.lower()
    updated = viz_specs.copy()

    if "add" in text:
        # Try to detect chart type
        if "scatter" in text:
            updated.append(VizSpec(
                chart_type="scatter",
                x="x",
                y="y",
                title="Scatter Plot (User Added)",
                x_label="X",
                y_label="Y",
                output_filename="scatter_user.png"
            ))
        elif "line" in text:
            updated.append(VizSpec(
                chart_type="line",
                x="x",
                y="y",
                title="Line Plot (User Added)",
                x_label="X",
                y_label="Y",
                output_filename="line_user.png"
            ))
        elif "box" in text:
            updated.append(VizSpec(
                chart_type="box",
                x="category",
                y="value",
                title="Box Plot (User Added)",
                x_label="Category",
                y_label="Value",
                output_filename="box_user.png"
            ))
        else:
            # Generic added chart
            updated.append(VizSpec(
                chart_type="histogram",
                x="value",
                y=None,
                title="Additional Histogram (User Added)",
                x_label="Value",
                y_label="Frequency",
                output_filename="histogram_user.png"
            ))

    elif "remove" in text:
        # Remove last chart (or match by filename)
        import re
        match = re.search(r"chart (\d+)", text)
        if match:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(updated):
                updated.pop(idx)
        else:
            # Remove last chart if no number specified
            if updated:
                updated.pop()

    return updated