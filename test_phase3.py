from core.interaction_handler import checkpoint, capture_amendment, interpret_amendment, apply_amendment, log_checkpoint
from datetime import datetime

# Test INT-1: Checkpoint
print("=== Testing INT-1: Checkpoint ===")
display = {
    "stage": "parsing",
    "task_type": "group_comparison",
    "group_column": "category",
    "value_column": "price",
    "records_found": 1000
}
# Uncomment the line below to test interactively (it will pause)
# choice = checkpoint("parsing", display)
# print(f"User chose: {choice}")

# Test INT-6: Logging
print("\n=== Testing INT-6: Logging ===")
log_checkpoint({
    "stage": "parsing",
    "user_choice": "Y",
    "execution_time_ms": 120
})
print("Log entry written to logs/interaction_log.jsonl")

# Test INT-2 + INT-3: Amendment capture and interpretation
print("\n=== Testing INT-3: Interpretation ===")
test_amendments = [
    ("change task to regression", "parsing"),
    ("exclude Travel category", "scraping"),
    ("force ANOVA", "audit"),
    ("add scatter plot", "viz_planning"),
    ("use seaborn for plots", "code_generation")
]
for text, stage in test_amendments:
    mod = interpret_amendment(text, stage)
    print(f"  '{text}' -> {mod['parsed']}")

print("\nAll tests completed!")
