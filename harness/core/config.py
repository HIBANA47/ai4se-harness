from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml

@dataclass
class GuardrailsConfig:
    blacklist: list[str] = field(default_factory=lambda: [".env", ".git", "secrets/"])
    max_diff_lines: int = 100
    require_approval_commands: list[str] = field(default_factory=lambda: ["rm", "del", "drop", "delete"])
    max_command_timeout: int = 120
    max_command_memory_mb: int = 512
    hitl_timeout: int = 300

@dataclass
class ConvergenceConfig:
    stagnation_limit: int = 3
    no_edit_limit: int = 3
    max_iterations: int = 5

@dataclass
class LLMConfig:
    provider: str = "openai_compatible"
    model: str = "gpt-4o"
    base_url: Optional[str] = None

@dataclass
class HarnessConfig:
    max_iterations: int = 5
    build_cmd: Optional[str] = None
    test_cmd: Optional[str] = None
    build_timeout: int = 60
    test_timeout: int = 120
    allowed_tools: list[str] = field(default_factory=lambda: ["read_file", "edit_file", "run_command", "grep", "glob"])
    max_feedback_lines: int = 50
    guardrails: GuardrailsConfig = field(default_factory=GuardrailsConfig)
    convergence: ConvergenceConfig = field(default_factory=ConvergenceConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}

def load_config(project_path: Optional[Path] = None, global_path: Optional[Path] = None) -> HarnessConfig:
    if global_path is None:
        global_path = Path.home() / ".config" / "harness" / "global.yaml"
    if project_path is None:
        project_path = Path.cwd()
    global_data = _load_yaml(global_path)
    project_data = _load_yaml(project_path / ".harness.yaml")
    merged = _deep_merge(global_data, project_data)
    guardrails_raw = merged.get("guardrails", {})
    convergence_raw = merged.get("convergence", {})
    llm_raw = merged.get("llm", {})
    guardrails = GuardrailsConfig(**{k: v for k, v in guardrails_raw.items() if k in GuardrailsConfig.__dataclass_fields__})
    convergence = ConvergenceConfig(
        max_iterations=merged.get("max_iterations", 5),
        **{k: v for k, v in convergence_raw.items() if k in ConvergenceConfig.__dataclass_fields__ and k != "max_iterations"},
    )
    llm = LLMConfig(**{k: v for k, v in llm_raw.items() if k in LLMConfig.__dataclass_fields__})
    return HarnessConfig(
        max_iterations=merged.get("max_iterations", 5),
        build_cmd=merged.get("build_cmd"),
        test_cmd=merged.get("test_cmd"),
        build_timeout=merged.get("build_timeout", 60),
        test_timeout=merged.get("test_timeout", 120),
        allowed_tools=merged.get("allowed_tools", ["read_file", "edit_file", "run_command", "grep", "glob"]),
        max_feedback_lines=merged.get("max_feedback_lines", 50),
        guardrails=guardrails,
        convergence=convergence,
        llm=llm,
    )