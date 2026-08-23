import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime

# ----------------------------------------
# Step 52: InteractionMode Dataclass
# ----------------------------------------
@dataclass
class InteractionMode:
    interactive: bool = False  # True = checkpoints enabled
    auto_proceed_timeout: Optional[int] = None  # Seconds to wait before auto-proceeding (None = wait forever)

# ----------------------------------------
# Step 53: CheckpointState Dataclass
# ----------------------------------------
@dataclass
class CheckpointState:
    stage: Literal[
        "parsing", "scraping", "extraction", "profiling", 
        "audit", "viz_planning", "code_generation", "execution", "reporting"
    ]
    approved: bool = False
    backtrack_instruction: Optional[str] = None
    modified_prompt: Optional[str] = None

# ----------------------------------------
# Step 54: INT-1 - Checkpoint
# ----------------------------------------
def checkpoint(stage: str, display_data: Dict[str, Any], options: List[str] = None) -> str:
    """
    Display a checkpoint to the user, prompt for input.
    Returns: 'Y', 'N', 'amend', or 'abort'
    """
    if options is None:
        options = ["Y", "N", "amend", "abort"]
    
    # Clear screen for better readability (optional, commented out for Windows compatibility)
    # os.system('cls' if os.name == 'nt' else 'clear')
    
    print("\n" + "=" * 80)
    print(f"🛑 CHECKPOINT: {stage.upper()}")
    print("=" * 80)
    
    # Display structured data nicely
    if display_data:
        print("\n📊 Current State:")
        for key, value in display_data.items():
            if isinstance(value, list):
                print(f"  • {key}: {len(value)} items")
                if len(value) > 0 and isinstance(value[0], dict):
                    # Show first item as sample
                    print(f"    Sample: {json.dumps(value[0], indent=2, default=str)[:200]}...")
                elif len(value) > 0:
                    print(f"    Preview: {str(value[:3])[:200]}...")
            elif isinstance(value, dict):
                print(f"  • {key}: {json.dumps(value, indent=2, default=str)[:300]}...")
            else:
                print(f"  • {key}: {value}")
    
    print("\n" + "-" * 80)
    print("Options:")
    for opt in options:
        print(f"  [{opt.upper()}]", end="  ")
    print("\n" + "-" * 80)
    
    while True:
        choice = input("Your choice: ").strip().lower()
        if choice in [o.lower() for o in options]:
            return choice
        else:
            print(f"Invalid choice. Please enter one of: {', '.join(options)}")

# ----------------------------------------
# Step 55-56: INT-2 - Capture Amendment
# ----------------------------------------
def capture_amendment() -> str:
    """
    Prompt the user for free-text amendment instructions.
    """
    print("\n" + "-" * 80)
    print("✏️  Please describe what needs to be changed.")
    print("   (Type 'abort' to cancel the entire run.)")
    print("-" * 80)
    
    amendment = input("> ").strip()
    return amendment

# ----------------------------------------
# Steps 57-61: INT-3 - Interpret Amendment (Keyword Matching)
# ----------------------------------------
def interpret_amendment(amendment_text: str, stage: str) -> Dict[str, Any]:
    """
    Parse user amendment text into a structured modification dict.
    Uses deterministic keyword matching (no model call).
    """
    amendment_text_lower = amendment_text.lower()
    modification = {
        "action": "modify",
        "stage": stage,
        "original_text": amendment_text,
        "parsed": {}
    }
    
    # Stage-specific keyword parsing
    if stage == "parsing":
        # Look for task type changes
        if "regression" in amendment_text_lower:
            modification["parsed"]["task_type"] = "regression"
        elif "classification" in amendment_text_lower:
            modification["parsed"]["task_type"] = "classification"
        elif "timeseries" in amendment_text_lower or "time series" in amendment_text_lower:
            modification["parsed"]["task_type"] = "timeseries"
        elif "group" in amendment_text_lower or "comparison" in amendment_text_lower or "category" in amendment_text_lower:
            modification["parsed"]["task_type"] = "group_comparison"
        
        # Look for column hints
        if "group" in amendment_text_lower or "category" in amendment_text_lower:
            # Try to extract a specific column name (naive)
            words = amendment_text.split()
            for i, word in enumerate(words):
                if word.lower() in ["by", "grouped", "category", "column"] and i + 1 < len(words):
                    modification["parsed"]["group_column"] = words[i+1].strip(" .,;:!?")
        
        if "price" in amendment_text_lower:
            modification["parsed"]["value_column"] = "price"
        elif "rating" in amendment_text_lower:
            modification["parsed"]["value_column"] = "rating"
    
    elif stage == "scraping":
        # Look for exclusion/inclusion keywords
        if "exclude" in amendment_text_lower:
            # Find what to exclude
            words = amendment_text.split()
            for i, word in enumerate(words):
                if word.lower() in ["exclude", "skip", "remove", "omit"] and i + 1 < len(words):
                    target = words[i+1].strip(" .,;:!?").lower()
                    # Check if it's a category name
                    if "travel" in target or "mystery" in target or "fiction" in target:
                        modification["parsed"]["exclude_pattern"] = target
                    else:
                        modification["parsed"]["exclude_pattern"] = target
        
        if "more pages" in amendment_text_lower or "increase pages" in amendment_text_lower:
            modification["parsed"]["max_pages"] = 100  # Increase limit
        elif "fewer pages" in amendment_text_lower or "decrease pages" in amendment_text_lower:
            modification["parsed"]["max_pages"] = 10
    
    elif stage == "audit":
        # Override audit recommendations
        if "anova" in amendment_text_lower:
            modification["parsed"]["force_anova"] = True
            modification["parsed"]["recommended_test"] = "ANOVA"
        elif "kruskal" in amendment_text_lower or "non-parametric" in amendment_text_lower:
            modification["parsed"]["force_kruskal"] = True
            modification["parsed"]["recommended_test"] = "Kruskal-Wallis"
        
        if "exclude" in amendment_text_lower:
            # Try to find group name
            words = amendment_text.split()
            for i, word in enumerate(words):
                if word.lower() in ["exclude", "remove", "omit"] and i + 1 < len(words):
                    modification["parsed"]["exclude_group"] = words[i+1].strip(" .,;:!?")
        
        if "threshold" in amendment_text_lower:
            # Try to find a number
            import re
            numbers = re.findall(r'\d+\.?\d*', amendment_text)
            if numbers:
                modification["parsed"]["threshold"] = float(numbers[0])
    
    elif stage == "viz_planning":
        if "add" in amendment_text_lower:
            modification["parsed"]["action"] = "add_chart"
            if "scatter" in amendment_text_lower:
                modification["parsed"]["chart_type"] = "scatter"
            elif "line" in amendment_text_lower:
                modification["parsed"]["chart_type"] = "line"
            elif "bar" in amendment_text_lower:
                modification["parsed"]["chart_type"] = "bar"
            elif "box" in amendment_text_lower:
                modification["parsed"]["chart_type"] = "box"
        elif "remove" in amendment_text_lower:
            modification["parsed"]["action"] = "remove_chart"
            # Try to find chart number
            import re
            numbers = re.findall(r'\d+', amendment_text)
            if numbers:
                modification["parsed"]["chart_index"] = int(numbers[0]) - 1  # 0-indexed
    
    elif stage == "code_generation":
        if "use" in amendment_text_lower:
            # Look for library/approach changes
            if "seaborn" in amendment_text_lower:
                modification["parsed"]["use_seaborn"] = True
            elif "matplotlib" in amendment_text_lower:
                modification["parsed"]["use_matplotlib"] = True
            
            # Look for test changes
            if "t-test" in amendment_text_lower:
                modification["parsed"]["use_ttest"] = True
            elif "mann-whitney" in amendment_text_lower:
                modification["parsed"]["use_mannwhitney"] = True
        
        if "more" in amendment_text_lower and "charts" in amendment_text_lower:
            modification["parsed"]["additional_charts"] = True
    
    elif stage == "execution":
        if "timeout" in amendment_text_lower:
            import re
            numbers = re.findall(r'\d+', amendment_text)
            if numbers:
                modification["parsed"]["timeout_sec"] = int(numbers[0])
    
    # If no specific modifications found, store the raw text
    if not modification["parsed"]:
        modification["parsed"]["raw_instruction"] = amendment_text
    
    return modification

# ----------------------------------------
# Steps 62-63: INT-4 - Request Clarification (Deterministic Fallback)
# ----------------------------------------
def request_clarification(ambiguous_text: str) -> str:
    """
    When amendment is ambiguous, ask the user to clarify.
    This version is deterministic (no model call) but can be upgraded to call MDL-2 later.
    """
    print("\n" + "=" * 80)
    print("❓ CLARIFICATION NEEDED")
    print("=" * 80)
    print(f"Your instruction: '{ambiguous_text}'")
    print("\nI didn't fully understand that. Please choose one of the following:")
    print("  1. Modify the task type (regression, classification, timeseries, group_comparison)")
    print("  2. Exclude/include specific data (categories, columns)")
    print("  3. Override audit recommendations (ANOVA, Kruskal-Wallis)")
    print("  4. Add/remove charts from the visualization plan")
    print("  5. Change code generation parameters (libraries, tests)")
    print("  6. Change execution timeout")
    print("  7. Other (provide a more detailed description)")
    print("-" * 80)
    
    while True:
        choice = input("Enter your choice (1-7): ").strip()
        if choice in ["1", "2", "3", "4", "5", "6", "7"]:
            break
        print("Invalid choice. Please enter a number from 1 to 7.")
    
    follow_up = input("\nPlease provide more details: ").strip()
    
    # Return a concatenated clarification
    return f"Choice {choice}: {follow_up}"

# ----------------------------------------
# Steps 64-68: INT-5 - Apply Amendment
# ----------------------------------------
def apply_amendment(modification: Dict[str, Any], stage: str, current_state: Any) -> Any:
    """
    Apply the structured modification to the current state.
    Returns the modified state (can be RunConfig, StructuredTask, AuditVerdict, etc.)
    """
    parsed = modification.get("parsed", {})
    
    # Handle different stage types
    if stage == "parsing":
        # current_state is expected to be a StructuredTask (or a dict)
        if isinstance(current_state, dict):
            if "task_type" in parsed:
                current_state["task_type"] = parsed["task_type"]
            if "group_column" in parsed:
                current_state["group_column"] = parsed["group_column"]
            if "value_column" in parsed:
                current_state["value_column"] = parsed["value_column"]
        else:
            # If it's a dataclass, we'd need to modify attributes - for now just return a dict
            # In practice, the orchestrator will handle the actual object modification
            pass
    
    elif stage == "scraping":
        # current_state is likely RunConfig
        if hasattr(current_state, "max_pages") and "max_pages" in parsed:
            current_state.max_pages = parsed["max_pages"]
        # For exclude patterns, we'll pass it as a filter
        if "exclude_pattern" in parsed:
            # Store as a custom attribute for the scraper
            if not hasattr(current_state, "exclude_patterns"):
                current_state.exclude_patterns = []
            current_state.exclude_patterns.append(parsed["exclude_pattern"])
    
    elif stage == "audit":
        # current_state is AuditVerdict or a dict
        if isinstance(current_state, dict):
            if "force_anova" in parsed and parsed["force_anova"]:
                current_state["recommended_test_or_model"] = "ANOVA"
                current_state["findings"].append("User overrode audit: forced ANOVA")
            if "force_kruskal" in parsed and parsed["force_kruskal"]:
                current_state["recommended_test_or_model"] = "Kruskal-Wallis"
                current_state["findings"].append("User overrode audit: forced Kruskal-Wallis")
            if "exclude_group" in parsed:
                if "excluded_groups" not in current_state:
                    current_state["excluded_groups"] = []
                current_state["excluded_groups"].append(parsed["exclude_group"])
    
    elif stage == "viz_planning":
        # current_state is List[VizSpec] - we'll handle this in the orchestrator
        # For now, just add the modification as a directive
        if "add_chart" in parsed and parsed.get("action") == "add_chart":
            # We'll pass a directive to VIZ-2
            pass
        if "remove_chart" in parsed and parsed.get("action") == "remove_chart":
            pass
    
    elif stage == "code_generation":
        # current_state is a prompt string - append the amendment
        if isinstance(current_state, str):
            current_state += f"\n\n[User Amendment: {modification.get('original_text', '')}]"
            if "use_seaborn" in parsed:
                current_state += "\n[User requested: use seaborn for plotting]"
            if "use_mannwhitney" in parsed:
                current_state += "\n[User requested: use Mann-Whitney U test]"
    
    elif stage == "execution":
        if hasattr(current_state, "timeout_sec") and "timeout_sec" in parsed:
            current_state.timeout_sec = parsed["timeout_sec"]
    
    return current_state

# ----------------------------------------
# Step 69: INT-6 - Log Checkpoint
# ----------------------------------------
def log_checkpoint(entry: Dict[str, Any]) -> None:
    """
    Append a checkpoint entry to logs/interaction_log.jsonl
    Creates the logs directory if it doesn't exist.
    """
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Add timestamp if not present
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.now().isoformat()
    
    # Append to JSONL file
    log_file = "logs/interaction_log.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")