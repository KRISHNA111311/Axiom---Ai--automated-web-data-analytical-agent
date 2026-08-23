import os
import tempfile
import shutil
from data_contracts import GeneratedScript, SandboxPolicy
from execution.sandbox_runner import (
    sandbox_network_policy,
    execute_in_sandbox,
    sanitize_execution_output,
    handle_execution_outcome
)

def test_sandbox():
    print("🧪 Testing Sandbox Execution (Phase 14)...")

    # 1. Create a dummy snapshot in a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="sandbox_test_")
    snapshot_path = os.path.join(temp_dir, "snapshot.parquet")
    import pandas as pd
    df = pd.DataFrame({
        "category": ["A", "B", "A", "B", "A"],
        "price": [10, 20, 15, 25, 12]
    })
    df.to_parquet(snapshot_path)
    print(f"   Dummy snapshot created: {snapshot_path}")

    # 2. Script that reads from /data/snapshot.parquet (mounted read-only)
    script_code = """
import pandas as pd
df = pd.read_parquet('/data/snapshot.parquet')
print(df.groupby('category')['price'].mean().to_string())
print("Script executed successfully.")
"""
    script = GeneratedScript(
        code=script_code,
        script_path="test_script.py",
        attempt_number=1
    )

    # 3. Get the policy
    policy = sandbox_network_policy()
    print(f"   Policy: network={policy.network_mode}, timeout={policy.timeout_sec}s")

    # 4. Execute in sandbox with the directory containing the snapshot mounted as /data
    result = execute_in_sandbox(script, policy, temp_dir)

    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_ms} ms")
    print(f"   Stdout: {result.stdout[:200]}")
    if result.stderr:
        print(f"   Stderr: {result.stderr[:200]}")

    # 5. Sanitize output
    sanitized_stdout, sanitized_stderr = sanitize_execution_output(result.stdout, result.stderr)
    print("   Sanitization OK.")

    # 6. Handle outcome
    outcome = handle_execution_outcome(result, attempt=1, max_retries=3)
    print(f"   Outcome: {outcome}")

    # Cleanup
    shutil.rmtree(temp_dir)
    print("✅ Sandbox test completed.")

if __name__ == "__main__":
    test_sandbox()