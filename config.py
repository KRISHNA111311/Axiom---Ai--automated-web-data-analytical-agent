import logging
from dataclasses import dataclass
from typing import Literal, Optional, List

logging.basicConfig(level=logging.INFO)

DEFAULT_MODEL = "gemini-3.6-flash"
DEFAULT_TEMPERATURE = 0.2

@dataclass
class RunConfig:
    query: str
    target_domain: str
    mode: Literal["assisted", "semi_autonomous", "autonomous", "interactive"]
    scraper: Literal["direct", "brightdata"]
    output_dir: str
    test_injection: bool
    max_retries: int

    # Phase 5 additions
    max_pages: Optional[int] = None           # simple page limit
    target_records: Optional[int] = None      # estimation-based record target
    sample_durations: List[int] = None        # for estimation
    safety_factor: float = 1.2                # buffer
    fields: Optional[List[str]] = None
    snapshot_source: Optional[str] = None

    def __post_init__(self):
        if self.sample_durations is None:
            self.sample_durations = [60,90,120]

@dataclass
class ModelConfig:
    model_name: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_output_tokens: int = 4096

@dataclass
class SandboxPolicy:
    network_mode: str = "none"
    memory_limit_mb: int = 1024
    cpu_limit: float = 1.0
    timeout_sec: int = 60