"""
Phase 11: Query Understanding (M6)
QRY-1, QRY-2
"""

import json
from typing import Optional
from data_contracts import StructuredTask
from agent.model_client import invoke_llm


# ============================================================
# QRY-1: Parse User Query
# ============================================================

def parse_user_query(raw_query: str, target_domain_hint: Optional[str] = None) -> StructuredTask:
    """
    QRY-1: Parse a natural‑language query into a StructuredTask using Gemini.
    """
    # Build the prompt with examples
    prompt = f"""
You are an expert data analysis assistant. Parse the user's query into a structured task.

The user wants to analyze data from: {target_domain_hint or 'unknown domain'}

User query: "{raw_query}"

Extract the following fields and return a valid JSON object:
- task_type: one of ["group_comparison", "regression", "classification", "timeseries"]
- group_column: the column name to group by (for group_comparison)
- value_column: the column name to analyze (for group_comparison, regression, timeseries)
- time_column: the column name for time (for timeseries)
- label_column: the column name for labels (for classification)
- visualization_requested: true or false (if user asks for charts/visualizations)

Here are examples:

Example 1:
Query: "analyze books and tell me the relationship between category and price with visualizations"
Output:
{{
  "task_type": "group_comparison",
  "group_column": "category",
  "value_column": "price",
  "time_column": null,
  "label_column": null,
  "visualization_requested": true
}}

Example 2:
Query: "predict book price based on rating and availability"
Output:
{{
  "task_type": "regression",
  "group_column": null,
  "value_column": "price",
  "time_column": null,
  "label_column": null,
  "visualization_requested": false
}}

Example 3:
Query: "classify books by category based on price and rating"
Output:
{{
  "task_type": "classification",
  "group_column": null,
  "value_column": null,
  "time_column": null,
  "label_column": "category",
  "visualization_requested": false
}}

Example 4:
Query: "analyze sales trends over time"
Output:
{{
  "task_type": "timeseries",
  "group_column": null,
  "value_column": "sales",
  "time_column": "date",
  "label_column": null,
  "visualization_requested": true
}}

Return ONLY the JSON object. Do not include any other text.
"""

    try:
        response = invoke_llm(prompt)
        json_str = response.content.strip()

        # Clean up markdown code blocks if present
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()

        data = json.loads(json_str)

        # Validate required fields
        task_type = data.get("task_type")
        if task_type not in ["group_comparison", "regression", "classification", "timeseries"]:
            raise ValueError(f"Invalid task_type: {task_type}")

        # Create StructuredTask with defaults for missing fields
        return StructuredTask(
            task_type=task_type,
            target_domain=target_domain_hint or "unknown",
            group_column=data.get("group_column"),
            value_column=data.get("value_column"),
            time_column=data.get("time_column"),
            label_column=data.get("label_column"),
            visualization_requested=data.get("visualization_requested", False)
        )

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse Gemini response as JSON: {e}\nResponse: {response.content}")
    except Exception as e:
        raise RuntimeError(f"Query parsing failed: {e}")


# ============================================================
# QRY-2: Reparse with Amendment
# ============================================================

def reparse_with_amendment(original_task: StructuredTask, amendment_text: str) -> StructuredTask:
    """
    QRY-2: Reparse a query with a user amendment.
    Used during backtracking to modify the task.
    """
    prompt = f"""
You previously parsed the user's query as:

Task type: {original_task.task_type}
Group column: {original_task.group_column}
Value column: {original_task.value_column}
Time column: {original_task.time_column}
Label column: {original_task.label_column}
Visualizations: {original_task.visualization_requested}

The user now says: "{amendment_text}"

Update the task based on this amendment. Return a JSON object with the updated fields.
Use the same format as the previous parsing task.

Return ONLY the JSON object. Do not include any other text.
"""

    try:
        response = invoke_llm(prompt)
        json_str = response.content.strip()

        # Clean up markdown
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()

        data = json.loads(json_str)

        # Merge with original task (new fields override)
        return StructuredTask(
            task_type=data.get("task_type", original_task.task_type),
            target_domain=original_task.target_domain,
            group_column=data.get("group_column", original_task.group_column),
            value_column=data.get("value_column", original_task.value_column),
            time_column=data.get("time_column", original_task.time_column),
            label_column=data.get("label_column", original_task.label_column),
            visualization_requested=data.get("visualization_requested", original_task.visualization_requested)
        )

    except Exception as e:
        print(f"⚠️  Amendment parsing failed: {e}. Using original task.")
        return original_task