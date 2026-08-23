"""
Phase 14: Sandbox Execution (M11)
SBX-1, SBX-2, SBX-3, SBX-4, SBX-5, SBX-6
"""

import os
import subprocess
import time
import tempfile
import shutil
from typing import List, Optional, Tuple
from data_contracts import GeneratedScript, ExecutionResult, SandboxPolicy
from storage.broker import broker_client_call


def provision_sandbox_view(broker_address: tuple, snapshot_dir: str) -> str:
    os.makedirs(snapshot_dir, exist_ok=True)
    snapshot_path = os.path.join(snapshot_dir, "snapshot.parquet")
    result = broker_client_call(
        "export_snapshot",
        {"file_path": snapshot_path},
        broker_address
    )
    if not os.path.exists(snapshot_path):
        raise RuntimeError(f"Snapshot export failed: {result}")
    return snapshot_dir  # return the directory, not the file


def sandbox_network_policy() -> SandboxPolicy:
    return SandboxPolicy(
        network_mode="none",
        memory_limit_mb=1024,
        cpu_limit=1.0,
        timeout_sec=120   # extended to avoid timeouts
    )


def execute_in_sandbox(
    script: GeneratedScript,
    policy: SandboxPolicy,
    view_path: str
) -> ExecutionResult:
    work_dir = tempfile.mkdtemp(prefix="sandbox_")
    script_path = os.path.join(work_dir, "script.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script.code)

    docker_cmd = [
        "docker", "run",
        "--rm",
        "--network", policy.network_mode,
        "--memory", f"{policy.memory_limit_mb}m",
        "--cpus", str(policy.cpu_limit),
        "-v", f"{work_dir}:/workspace",
        "-v", f"{view_path}:/data:ro",
        "-w", "/workspace",
        "ai-analysis-sandbox",
        "python", "script.py"
    ]

    start_time = time.time()
    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=policy.timeout_sec
        )
        elapsed_ms = int((time.time() - start_time) * 1000)
        success = result.returncode == 0
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        success = False
        stdout = e.stdout or ""
        stderr = f"Timeout after {policy.timeout_sec} seconds"
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        success = False
        stdout = ""
        stderr = str(e)

    artifact_paths = []
    for fname in os.listdir(work_dir):
        if fname.endswith(".png") or fname.endswith(".csv") or fname.endswith(".json"):
            artifact_paths.append(os.path.join(work_dir, fname))

    return ExecutionResult(
        success=success,
        stdout=stdout,
        stderr=stderr,
        artifact_paths=artifact_paths,
        duration_ms=elapsed_ms
    )


def sanitize_execution_output(stdout: str, stderr: str) -> Tuple[str, str]:
    max_lines = 1000
    max_chars = 50000
    def _sanitize(text: str) -> str:
        if not text:
            return ""
        lines = text.splitlines()
        if len(lines) > max_lines:
            lines = lines[:max_lines] + [f"... (truncated, {len(lines)-max_lines} more lines)"]
        result = "\n".join(lines)
        if len(result) > max_chars:
            result = result[:max_chars] + "... (truncated)"
        return result
    return _sanitize(stdout), _sanitize(stderr)


def handle_execution_outcome(
    result: ExecutionResult,
    attempt: int,
    max_retries: int
) -> str:
    if result.success:
        return "success"
    if attempt < max_retries:
        return "retry"
    return "fail"


def get_cached_snapshot_if_needed(flags, config) -> Optional[str]:
    if not flags.db_enabled and flags.sandbox_enabled:
        if config.snapshot_source and os.path.exists(config.snapshot_source):
            return config.snapshot_source
        raise RuntimeError("No snapshot source provided when db is disabled.")
    return None