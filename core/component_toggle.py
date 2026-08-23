from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from config import RunConfig

# ----------------------------------------
# Step 38: ComponentFlags Dataclass
# ----------------------------------------
@dataclass
class ComponentFlags:
    scraper_enabled: bool
    db_enabled: bool
    sandbox_enabled: bool
    ai_enabled: bool

    def to_string(self) -> str:
        """Convert flags to a compact string like 'ScDbSbAi'"""
        parts = []
        if self.scraper_enabled: parts.append("Sc")
        if self.db_enabled: parts.append("Db")
        if self.sandbox_enabled: parts.append("Sb")
        if self.ai_enabled: parts.append("Ai")
        return "".join(parts) if parts else "None"

# ----------------------------------------
# Step 39: ExecutionPlan Dataclass
# ----------------------------------------
@dataclass
class ExecutionPlan:
    stages: List[Dict[str, any]]  # list of stage definitions
    order: List[str]              # ordered list of stage IDs
    skip_reason: Dict[str, str]   # stage_id -> reason string

# ----------------------------------------
# Step 40: CMP-1 - Parse Component Flags
# ----------------------------------------
def parse_component_flags(flag_string: str) -> ComponentFlags:
    """
    Parse a string like 'ScDbSbAi' into ComponentFlags.
    Valid characters: S, c, D, b, S, b, A, i (case-sensitive per design)
    """
    # Default: all disabled
    flags = ComponentFlags(
        scraper_enabled=False,
        db_enabled=False,
        sandbox_enabled=False,
        ai_enabled=False
    )

    # Step 41: Validation - check if string contains only valid chars
    valid_chars = {'S', 'c', 'D', 'b', 'S', 'b', 'A', 'i'}  # The letters in order
    # Actually, we just check if specific substrings exist
    
    if "Sc" in flag_string:
        flags.scraper_enabled = True
    if "Db" in flag_string:
        flags.db_enabled = True
    if "Sb" in flag_string:
        flags.sandbox_enabled = True
    if "Ai" in flag_string:
        flags.ai_enabled = True
    
    return flags

# ----------------------------------------
# Step 42-43: CMP-2 - Build Execution Plan
# ----------------------------------------
def build_execution_plan(flags: ComponentFlags, config: RunConfig) -> ExecutionPlan:
    """
    Build the execution plan based on component flags.
    Defines which stages run and in what order.
    """
    stages = []
    order = []
    skip_reason = {}

    # Define all possible stages with their dependencies
    stage_definitions = [
        {
            "id": "parsing",
            "name": "Query Parsing",
            "enabled": flags.ai_enabled,
            "dependencies": [],
            "skip_reason": "Component 'ai' disabled" if not flags.ai_enabled else None
        },
        {
            "id": "scraping",
            "name": "Web Scraping",
            "enabled": flags.scraper_enabled,
            "dependencies": [],
            "skip_reason": "Component 'scraper' disabled" if not flags.scraper_enabled else None
        },
        {
            "id": "injection_defense",
            "name": "Injection Defense Scan",
            "enabled": flags.scraper_enabled,  # Only runs if we scrape external content
            "dependencies": ["scraping"],
            "skip_reason": "Component 'scraper' disabled (no external content to scan)" if not flags.scraper_enabled else None
        },
        {
            "id": "extraction",
            "name": "Data Extraction",
            "enabled": flags.scraper_enabled,
            "dependencies": ["scraping", "injection_defense"],
            "skip_reason": "Component 'scraper' disabled" if not flags.scraper_enabled else None
        },
        {
            "id": "ingestion",
            "name": "Database Ingestion",
            "enabled": flags.db_enabled,
            "dependencies": ["extraction"] if flags.scraper_enabled else [],
            "skip_reason": "Component 'db' disabled" if not flags.db_enabled else None
        },
        {
            "id": "profiling",
            "name": "Data Profiling (TLS-8)",
            "enabled": flags.db_enabled,
            "dependencies": ["ingestion"] if flags.db_enabled else [],
            "skip_reason": "Component 'db' disabled" if not flags.db_enabled else None
        },
        {
            "id": "audit",
            "name": "Assumption Audit (M8)",
            "enabled": flags.db_enabled,
            "dependencies": ["profiling"],
            "skip_reason": "Component 'db' disabled" if not flags.db_enabled else None
        },
        {
            "id": "viz_planning",
            "name": "Visualization Planning",
            "enabled": flags.db_enabled and flags.ai_enabled,
            "dependencies": ["audit", "profiling"],
            "skip_reason": "Requires both 'db' and 'ai'" if not (flags.db_enabled and flags.ai_enabled) else None
        },
        {
            "id": "code_generation",
            "name": "Code Synthesis (GEN-1/2)",
            "enabled": flags.ai_enabled,
            "dependencies": ["viz_planning"] if (flags.db_enabled and flags.ai_enabled) else [],
            "skip_reason": "Component 'ai' disabled" if not flags.ai_enabled else None
        },
        {
            "id": "sandbox_execution",
            "name": "Sandbox Execution (SBX-3)",
            "enabled": flags.sandbox_enabled,
            "dependencies": ["code_generation"] if flags.ai_enabled else [],
            "skip_reason": "Component 'sandbox' disabled" if not flags.sandbox_enabled else None
        },
        {
            "id": "reporting",
            "name": "Report Generation (REP-1/2)",
            "enabled": flags.ai_enabled or flags.sandbox_enabled or flags.db_enabled,
            "dependencies": ["sandbox_execution"] if flags.sandbox_enabled else ["code_generation"] if flags.ai_enabled else [],
            "skip_reason": "No data or AI to report on" if not (flags.ai_enabled or flags.sandbox_enabled or flags.db_enabled) else None
        }
    ]

    # Build stages list and record skip reasons
    for stage in stage_definitions:
        stages.append({
            "id": stage["id"],
            "name": stage["name"],
            "enabled": stage["enabled"],
            "dependencies": stage["dependencies"]
        })
        
        if not stage["enabled"] and stage["skip_reason"]:
            skip_reason[stage["id"]] = stage["skip_reason"]
        elif not stage["enabled"]:
            skip_reason[stage["id"]] = "Disabled by component flags"
        
        # Add to order if enabled
        if stage["enabled"]:
            order.append(stage["id"])

    return ExecutionPlan(stages=stages, order=order, skip_reason=skip_reason)

# ----------------------------------------
# Step 44: CMP-3 - Check Stage Dependency
# ----------------------------------------
def check_stage_dependency(stage_id: str, execution_plan: ExecutionPlan) -> bool:
    """
    Check if a given stage can run (i.e., all its dependencies are met).
    """
    # Find the stage definition
    stage_def = None
    for s in execution_plan.stages:
        if s["id"] == stage_id:
            stage_def = s
            break
    
    if not stage_def:
        return False
    
    if not stage_def["enabled"]:
        return False
    
    # Check if all dependencies are in the execution order
    for dep in stage_def["dependencies"]:
        if dep not in execution_plan.order:
            return False
    
    return True

# ----------------------------------------
# Step 45: CMP-4 - Get Skip Reasons
# ----------------------------------------
def get_skip_reasons(execution_plan: ExecutionPlan) -> Dict[str, str]:
    """
    Return a dictionary of stage_id -> skip reason for all disabled stages.
    """
    return execution_plan.skip_reason