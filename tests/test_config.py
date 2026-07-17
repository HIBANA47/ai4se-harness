import os
import tempfile
from pathlib import Path
import pytest
import yaml
from harness.core.config import (
    HarnessConfig, GuardrailsConfig, ConvergenceConfig, LLMConfig, load_config,
)

@pytest.fixture
def project_config_path(tmp_path):
    config = {
        "max_iterations": 10,
        "build_cmd": "make build",
        "test_cmd": "make test",
        "build_timeout": 30,
        "test_timeout": 60,
        "allowed_tools": ["read_file", "edit_file", "run_command"],
        "guardrails": {
            "blacklist": [".env", ".git"],
            "max_diff_lines": 50,
            "require_approval_commands": ["rm", "del"],
            "max_command_timeout": 30,
            "max_command_memory_mb": 256,
            "hitl_timeout": 120,
        },
        "convergence": {"stagnation_limit": 5, "no_edit_limit": 3},
        "llm": {"provider": "openai_compatible", "model": "gpt-4", "base_url": "https://api.example.com/v1"},
        "max_feedback_lines": 30,
    }
    path = tmp_path / ".harness.yaml"
    with open(path, "w") as f:
        yaml.dump(config, f)
    return path

def test_load_project_config(project_config_path):
    cfg = load_config(project_path=project_config_path.parent)
    assert cfg.max_iterations == 10
    assert cfg.build_cmd == "make build"
    assert cfg.test_cmd == "make test"
    assert cfg.build_timeout == 30
    assert cfg.test_timeout == 60
    assert cfg.allowed_tools == ["read_file", "edit_file", "run_command"]
    assert cfg.max_feedback_lines == 30

def test_guardrails_config(project_config_path):
    cfg = load_config(project_path=project_config_path.parent)
    assert cfg.guardrails.blacklist == [".env", ".git"]
    assert cfg.guardrails.max_diff_lines == 50
    assert cfg.guardrails.require_approval_commands == ["rm", "del"]
    assert cfg.guardrails.max_command_timeout == 30
    assert cfg.guardrails.max_command_memory_mb == 256
    assert cfg.guardrails.hitl_timeout == 120

def test_convergence_config(project_config_path):
    cfg = load_config(project_path=project_config_path.parent)
    assert cfg.convergence.stagnation_limit == 5
    assert cfg.convergence.no_edit_limit == 3

def test_llm_config(project_config_path):
    cfg = load_config(project_path=project_config_path.parent)
    assert cfg.llm.provider == "openai_compatible"
    assert cfg.llm.model == "gpt-4"
    assert cfg.llm.base_url == "https://api.example.com/v1"

def test_default_values(tmp_path):
    cfg = load_config(project_path=tmp_path, global_path=tmp_path / "nonexistent.yaml")
    assert cfg.max_iterations == 5
    assert cfg.max_feedback_lines == 50
    assert cfg.guardrails.hitl_timeout == 300
    assert cfg.convergence.stagnation_limit == 3
    assert cfg.convergence.no_edit_limit == 3

def test_global_then_project_override(tmp_path):
    global_cfg = {"max_iterations": 20, "build_cmd": "global_build"}
    global_path = tmp_path / "global.yaml"
    with open(global_path, "w") as f:
        yaml.dump(global_cfg, f)
    project_cfg = {"max_iterations": 7}
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    with open(project_dir / ".harness.yaml", "w") as f:
        yaml.dump(project_cfg, f)
    cfg = load_config(project_path=project_dir, global_path=global_path)
    assert cfg.max_iterations == 7
    assert cfg.build_cmd == "global_build"

def test_missing_both_configs(tmp_path):
    cfg = load_config(project_path=tmp_path, global_path=tmp_path / "nonexistent.yaml")
    assert isinstance(cfg, HarnessConfig)