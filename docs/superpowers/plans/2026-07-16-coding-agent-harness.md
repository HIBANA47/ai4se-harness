# Coding Agent Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-coded Python agent harness that fixes bugs through a feedback-driven loop with guardrails, HITL, memory, configuration, and a WebUI.

**Architecture:** Sequential pipeline agent loop. LLM generates tool calls → guardrails validate → tools execute in sandbox → feedback pipeline (build → test) evaluates → convergence decides continue/stop → HITL pauses for dangerous operations → WebUI streams everything via WebSocket.

**Tech Stack:** Python 3.11+, FastAPI, HTMX, PyYAML, keyring, python-dotenv, pytest, uvicorn, Docker

## Global Constraints

- Python >= 3.11
- No agent framework dependencies (no LangChain AgentExecutor, AutoGen, CrewAI, LlamaIndex agent)
- All core mechanisms must be testable with mock/stub LLM (no network, no real LLM)
- TDD: red → green → refactor for every task
- Commit after every task passes
- `.harness.yaml` is the project config format, `~/.config/harness/global.yaml` is global config
- Sandbox = single directory, all file operations restricted to it
- `max_feedback_lines` = 50 (default)
- `hitl_timeout` = 300 seconds (default)
- Memory persists to `~/.cache/harness/memory.json`

---

## File Structure

```
harness/                        # project root
├── harness/                    # source package
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration loading & merging
│   │   ├── loop.py             # Agent main loop
│   │   └── memory.py           # Conversation history management
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py           # LLMClient protocol + implementations
│   │   └── schemas.py          # Data models (ToolCall, LLMResponse, etc.)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py             # Tool protocol definition
│   │   ├── dispatcher.py       # Tool registry & dispatch
│   │   ├── read_file.py        # read_file tool
│   │   ├── edit_file.py        # edit_file tool (3-state matching)
│   │   ├── run_command.py      # run_command tool (timeout)
│   │   ├── grep_tool.py        # grep tool
│   │   └── glob_tool.py       # glob tool
│   ├── guardrails/
│   │   ├── __init__.py
│   │   ├── pre_action.py       # Pre-execution guards
│   │   ├── post_action.py      # Post-execution guards
│   │   ├── rules.py            # GuardrailRules dataclass
│   │   └── hitl.py             # HITL synchronous blocking
│   ├── feedback/
│   │   ├── __init__.py
│   │   ├── pipeline.py         # Build → test feedback pipeline
│   │   ├── convergence.py      # Progress tracking & stop decisions
│   │   └── parsers.py          # Error output parsing
│   ├── security/
│   │   ├── __init__.py
│   │   ├── credentials.py      # keyring + .env credential store
│   │   └── setup.py            # First-run interactive setup
│   └── web/
│       ├── __init__.py
│       ├── app.py              # FastAPI application
│       ├── api.py              # REST + WebSocket endpoints
│       └── templates/
│           └── index.html      # HTMX template
├── tests/
│   ├── __init__.py
│   ├── test_schemas.py
│   ├── test_config.py
│   ├── test_memory.py
│   ├── test_tools.py
│   ├── test_dispatcher.py
│   ├── test_guardrails.py
│   ├── test_hitl.py
│   ├── test_parsers.py
│   ├── test_pipeline.py
│   ├── test_convergence.py
│   ├── test_loop.py
│   ├── test_credentials.py
│   └── test_web.py
├── demos/
│   └── mechanism_demo.py       # Mock LLM mechanism demonstration
├── .harness.yaml               # Example project config
├── pyproject.toml
├── Dockerfile
├── .gitlab-ci.yml
└── .env.example
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `harness/__init__.py`
- Create: `harness/core/__init__.py`
- Create: `harness/llm/__init__.py`
- Create: `harness/tools/__init__.py`
- Create: `harness/guardrails/__init__.py`
- Create: `harness/feedback/__init__.py`
- Create: `harness/security/__init__.py`
- Create: `harness/web/__init__.py`
- Create: `tests/__init__.py`
- Create: `.env.example`

**Interfaces:**
- Produces: package structure that all subsequent tasks import from

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "harness"
version = "0.1.0"
description = "A self-coded Coding Agent Harness for automated bug fixing"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "httpx>=0.27",
    "keyring>=25.0",
    "python-dotenv>=1.0",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "websockets>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["harness*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.env
.venv/
dist/
*.egg-info/
.pytest_cache/
.harness.yaml
```

- [ ] **Step 3: Create .env.example**

```
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.example.com/v1
```

- [ ] **Step 4: Create all __init__.py files**

Create empty `__init__.py` in: `harness/`, `harness/core/`, `harness/llm/`, `harness/tools/`, `harness/guardrails/`, `harness/feedback/`, `harness/security/`, `harness/web/`, `tests/`

- [ ] **Step 5: Install project in dev mode**

Run: `pip install -e ".[dev]"`
Expected: SUCCESS, package installed

- [ ] **Step 6: Verify pytest runs**

Run: `pytest --co`
Expected: "no tests collected" (but no errors)

- [ ] **Step 7: Commit**

```bash
git init
git add -A
git commit -m "chore: project scaffolding"
```

---

## Task 2: Data Models

**Files:**
- Create: `harness/llm/schemas.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: nothing
- Produces: `ToolCall`, `ToolResult`, `LLMResponse`, `MemoryEntry`, `FeedbackResult`, `FixResult`, `GuardResult` — used by every other module

- [ ] **Step 1: Write failing tests**

```python
# tests/test_schemas.py
from harness.llm.schemas import (
    ToolCall, ToolResult, LLMResponse, MemoryEntry,
    FeedbackResult, FixResult, GuardResult,
)


def test_tool_call_creation():
    tc = ToolCall(name="read_file", args={"path": "main.py"})
    assert tc.name == "read_file"
    assert tc.args == {"path": "main.py"}


def test_tool_result_success():
    tr = ToolResult(success=True, data="file content")
    assert tr.success is True
    assert tr.data == "file content"
    assert tr.error is None


def test_tool_result_failure():
    tr = ToolResult(success=False, error="file not found")
    assert tr.success is False
    assert tr.error == "file not found"


def test_llm_response_tool_use():
    tc = ToolCall(name="read_file", args={"path": "main.py"})
    resp = LLMResponse(type="tool_use", tool_calls=[tc], reasoning="need to read the file")
    assert resp.type == "tool_use"
    assert len(resp.tool_calls) == 1
    assert resp.reasoning == "need to read the file"


def test_llm_response_fix_complete():
    resp = LLMResponse(type="fix_complete", reasoning="bug is fixed")
    assert resp.type == "fix_complete"
    assert resp.tool_calls == []


def test_llm_response_parse_error():
    resp = LLMResponse(type="parse_error", error="invalid JSON from LLM")
    assert resp.type == "parse_error"
    assert resp.error == "invalid JSON from LLM"


def test_llm_response_defaults():
    resp = LLMResponse(type="tool_use")
    assert resp.tool_calls == []
    assert resp.reasoning == ""
    assert resp.error is None


def test_memory_entry_success():
    tc = ToolCall(name="read_file", args={})
    tr = ToolResult(success=True, data="content")
    entry = MemoryEntry(type="success", tool_call=tc, result=tr)
    assert entry.type == "success"
    assert entry.reason is None


def test_memory_entry_rejected():
    tc = ToolCall(name="read_file", args={"path": ".env"})
    entry = MemoryEntry(type="rejected", tool_call=tc, reason="blacklisted_path")
    assert entry.type == "rejected"
    assert entry.reason == "blacklisted_path"


def test_memory_entry_violation():
    tc = ToolCall(name="edit_file", args={})
    tr = ToolResult(success=True)
    entry = MemoryEntry(type="violation", tool_call=tc, result=tr, reason="diff_too_large")
    assert entry.type == "violation"


def test_feedback_result_failure():
    fr = FeedbackResult(stage="build", success=False, errors=["SyntaxError: line 10"], raw_output="...")
    assert fr.stage == "build"
    assert fr.success is False
    assert len(fr.errors) == 1


def test_feedback_result_success():
    fr = FeedbackResult(stage="test", success=True)
    assert fr.success is True
    assert fr.errors == []
    assert fr.raw_output == ""


def test_fix_result_success():
    fr = FixResult(success=True, diff="--- a/main.py\n+++ b/main.py\n...", iterations=3)
    assert fr.success is True
    assert fr.iterations == 3


def test_fix_result_failure():
    fr = FixResult(success=False, reason="max_iterations_reached", iterations=5)
    assert fr.reason == "max_iterations_reached"


def test_guard_result_allowed():
    gr = GuardResult(allowed=True)
    assert gr.allowed is True
    assert gr.reason == ""


def test_guard_result_denied():
    gr = GuardResult(allowed=False, reason="blacklisted_path")
    assert gr.allowed is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'harness.llm.schemas'`

- [ ] **Step 3: Implement data models**

```python
# harness/llm/schemas.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional


@dataclass
class ToolCall:
    name: str
    args: dict


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None


@dataclass
class LLMResponse:
    type: Literal["tool_use", "fix_complete", "parse_error"]
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning: str = ""
    error: Optional[str] = None


@dataclass
class MemoryEntry:
    type: Literal["success", "rejected", "violation"]
    tool_call: ToolCall
    result: Optional[ToolResult] = None
    reason: Optional[str] = None


@dataclass
class FeedbackResult:
    stage: Literal["build", "test"]
    success: bool
    errors: list[str] = field(default_factory=list)
    raw_output: str = ""


@dataclass
class FixResult:
    success: bool
    diff: Optional[str] = None
    reason: Optional[str] = None
    iterations: int = 0


@dataclass
class GuardResult:
    allowed: bool
    reason: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_schemas.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add harness/llm/schemas.py tests/test_schemas.py
git commit -m "feat: add core data models (ToolCall, ToolResult, LLMResponse, MemoryEntry, FeedbackResult, FixResult, GuardResult)"
```

---

## Task 3: Configuration Loading

**Files:**
- Create: `harness/core/config.py`
- Test: `tests/test_config.py`
- Create: `.harness.yaml` (example)

**Interfaces:**
- Consumes: `harness/llm/schemas.py` (no types, standalone)
- Produces: `HarnessConfig`, `load_config()`, `GuardrailsConfig`, `FeedbackConfig`, `ConvergenceConfig`, `LLMConfig` — used by loop, guardrails, feedback, convergence, LLM client

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from harness.core.config import (
    HarnessConfig,
    GuardrailsConfig,
    ConvergenceConfig,
    LLMConfig,
    load_config,
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
        "convergence": {
            "stagnation_limit": 5,
            "no_edit_limit": 3,
        },
        "llm": {
            "provider": "openai_compatible",
            "model": "gpt-4",
            "base_url": "https://api.example.com/v1",
        },
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
    cfg = load_config(
        project_path=tmp_path,
        global_path=tmp_path / "nonexistent.yaml",
    )
    assert isinstance(cfg, HarnessConfig)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement configuration**

```python
# harness/core/config.py
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
    allowed_tools: list[str] = field(
        default_factory=lambda: ["read_file", "edit_file", "run_command", "grep", "glob"]
    )
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


def load_config(
    project_path: Optional[Path] = None,
    global_path: Optional[Path] = None,
) -> HarnessConfig:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: ALL PASS

- [ ] **Step 5: Create example .harness.yaml**

```yaml
# .harness.yaml (example project configuration)
max_iterations: 5
build_cmd: "python -m py_compile main.py"
test_cmd: "pytest"
build_timeout: 60
test_timeout: 120
allowed_tools:
  - read_file
  - edit_file
  - run_command
  - grep
  - glob
guardrails:
  blacklist:
    - .env
    - .git
    - secrets/
  max_diff_lines: 100
  require_approval_commands:
    - rm
    - del
    - drop
    - delete
  max_command_timeout: 120
  max_command_memory_mb: 512
  hitl_timeout: 300
convergence:
  stagnation_limit: 3
  no_edit_limit: 3
llm:
  provider: openai_compatible
  model: gpt-4o
  base_url: null
max_feedback_lines: 50
```

- [ ] **Step 6: Commit**

```bash
git add harness/core/config.py tests/test_config.py .harness.yaml
git commit -m "feat: add configuration loading with global + project override"
```

---

## Task 4: Memory Module

**Files:**
- Create: `harness/core/memory.py`
- Test: `tests/test_memory.py`

**Interfaces:**
- Consumes: `ToolCall`, `ToolResult`, `MemoryEntry` from `harness/llm/schemas.py`
- Produces: `Memory` class — used by `loop.py` for conversation history management

- [ ] **Step 1: Write failing tests**

```python
# tests/test_memory.py
import json
import tempfile
from pathlib import Path

import pytest

from harness.core.memory import Memory
from harness.llm.schemas import ToolCall, ToolResult


def test_append_success():
    mem = Memory()
    tc = ToolCall(name="read_file", args={"path": "main.py"})
    tr = ToolResult(success=True, data="content")
    mem.append(tc, tr)
    assert len(mem.history) == 1
    assert mem.history[0].type == "success"
    assert mem.history[0].reason is None


def test_append_rejection():
    mem = Memory()
    tc = ToolCall(name="read_file", args={"path": ".env"})
    mem.append_rejection(tc, "blacklisted_path")
    assert len(mem.history) == 1
    assert mem.history[0].type == "rejected"
    assert mem.history[0].reason == "blacklisted_path"


def test_append_violation():
    mem = Memory()
    tc = ToolCall(name="edit_file", args={})
    tr = ToolResult(success=True)
    mem.append_violation(tc, tr, "diff_too_large")
    assert mem.history[0].type == "violation"
    assert mem.history[0].reason == "diff_too_large"


def test_get_diff_from_history():
    mem = Memory()
    tc1 = ToolCall(name="edit_file", args={"path": "a.py"})
    tr1 = ToolResult(success=True, data={"diff": "--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-old\n+new"})
    mem.append(tc1, tr1)
    tc2 = ToolCall(name="read_file", args={"path": "b.py"})
    tr2 = ToolResult(success=True, data="content")
    mem.append(tc2, tr2)
    diff = mem.get_diff_from_history()
    assert "-old" in diff
    assert "+new" in diff


def test_to_prompt_context_limits_entries():
    mem = Memory()
    for i in range(30):
        tc = ToolCall(name=f"tool_{i}", args={})
        tr = ToolResult(success=True)
        mem.append(tc, tr)
    ctx = mem.to_prompt_context(max_entries=20)
    assert "tool_" in ctx
    lines = ctx.strip().split("\n")
    assert len(lines) == 20


def test_to_prompt_context_includes_rejections():
    mem = Memory()
    tc = ToolCall(name="edit_file", args={"path": ".env"})
    mem.append_rejection(tc, "blacklisted_path")
    ctx = mem.to_prompt_context()
    assert "REJECTED" in ctx
    assert "blacklisted_path" in ctx


def test_save_and_load(tmp_path):
    mem = Memory()
    tc = ToolCall(name="read_file", args={"path": "main.py"})
    tr = ToolResult(success=True, data="hello")
    mem.append(tc, tr)

    save_path = tmp_path / "memory.json"
    mem.save(save_path)
    assert save_path.exists()

    mem2 = Memory()
    mem2.load(save_path)
    assert len(mem2.history) == 1
    assert mem2.history[0].tool_call.name == "read_file"


def test_load_nonexistent_file(tmp_path):
    mem = Memory()
    mem.load(tmp_path / "nonexistent.json")
    assert len(mem.history) == 0


def test_empty_memory_prompt_context():
    mem = Memory()
    ctx = mem.to_prompt_context()
    assert ctx == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_memory.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement memory module**

```python
# harness/core/memory.py
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from harness.llm.schemas import MemoryEntry, ToolCall, ToolResult


class Memory:
    def __init__(self):
        self.history: list[MemoryEntry] = []

    def append(self, tool_call: ToolCall, result: ToolResult):
        self.history.append(MemoryEntry(type="success", tool_call=tool_call, result=result))

    def append_rejection(self, tool_call: ToolCall, reason: str):
        self.history.append(MemoryEntry(type="rejected", tool_call=tool_call, reason=reason))

    def append_violation(self, tool_call: ToolCall, result: ToolResult, reason: str):
        self.history.append(MemoryEntry(type="violation", tool_call=tool_call, result=result, reason=reason))

    def get_diff_from_history(self) -> str:
        diffs = []
        for entry in self.history:
            if entry.type == "success" and entry.tool_call.name == "edit_file" and entry.result:
                data = entry.result.data
                if isinstance(data, dict) and "diff" in data:
                    diffs.append(data["diff"])
        return "\n".join(diffs)

    def to_prompt_context(self, max_entries: int = 20) -> str:
        if not self.history:
            return ""
        recent = self.history[-max_entries:]
        lines = []
        for entry in recent:
            if entry.type == "success":
                summary = f"{entry.result.data}" if entry.result and entry.result.data else "ok"
                if isinstance(entry.result.data, dict):
                    summary = f"edited {entry.tool_call.args.get('path', '?')}"
                lines.append(f"[OK] {entry.tool_call.name}({entry.tool_call.args}) → {summary}")
            elif entry.type == "rejected":
                lines.append(f"[REJECTED] {entry.tool_call.name}({entry.tool_call.args}) reason: {entry.reason}")
            elif entry.type == "violation":
                lines.append(f"[VIOLATION] {entry.tool_call.name}({entry.tool_call.args}) reason: {entry.reason}")
        return "\n".join(lines)

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [self._entry_to_dict(e) for e in self.history]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: Path):
        if not path.exists():
            return
        with open(path) as f:
            data = json.load(f)
        self.history = [self._dict_to_entry(d) for d in data]

    @staticmethod
    def _entry_to_dict(entry: MemoryEntry) -> dict:
        return {
            "type": entry.type,
            "tool_call": {"name": entry.tool_call.name, "args": entry.tool_call.args},
            "result": asdict(entry.result) if entry.result else None,
            "reason": entry.reason,
        }

    @staticmethod
    def _dict_to_entry(d: dict) -> MemoryEntry:
        tc = ToolCall(name=d["tool_call"]["name"], args=d["tool_call"]["args"])
        tr = None
        if d.get("result") is not None:
            tr = ToolResult(**d["result"])
        return MemoryEntry(type=d["type"], tool_call=tc, result=tr, reason=d.get("reason"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_memory.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add harness/core/memory.py tests/test_memory.py
git commit -m "feat: add memory module with JSON persistence"
```

---

## Task 5: Tool Protocol & Dispatcher

**Files:**
- Create: `harness/tools/base.py`
- Create: `harness/tools/dispatcher.py`
- Test: `tests/test_dispatcher.py`

**Interfaces:**
- Consumes: `ToolCall`, `ToolResult` from `harness/llm/schemas.py`
- Produces: `Tool` protocol, `Dispatcher` class — used by `loop.py`, all individual tool implementations

- [ ] **Step 1: Write failing tests**

```python
# tests/test_dispatcher.py
import pytest

from harness.llm.schemas import ToolCall, ToolResult
from harness.tools.base import Tool
from harness.tools.dispatcher import Dispatcher


class AddTool(Tool):
    name = "add"
    description = "Add two numbers"
    schema = {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}}

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data=kwargs["a"] + kwargs["b"])


class FailTool(Tool):
    name = "fail"
    description = "Always fails"
    schema = {}

    def execute(self, **kwargs) -> ToolResult:
        raise ValueError("intentional failure")


def test_register_and_execute():
    d = Dispatcher(sandbox_path="/tmp")
    d.register(AddTool(sandbox_path="/tmp"))
    result = d.execute(ToolCall(name="add", args={"a": 2, "b": 3}))
    assert result.success is True
    assert result.data == 5


def test_unknown_tool():
    d = Dispatcher(sandbox_path="/tmp")
    result = d.execute(ToolCall(name="nonexistent", args={}))
    assert result.success is False
    assert "unknown_tool" in result.error


def test_tool_exception_caught():
    d = Dispatcher(sandbox_path="/tmp")
    d.register(FailTool(sandbox_path="/tmp"))
    result = d.execute(ToolCall(name="fail", args={}))
    assert result.success is False
    assert "intentional failure" in result.error


def test_get_tools_schema():
    d = Dispatcher(sandbox_path="/tmp")
    d.register(AddTool(sandbox_path="/tmp"))
    schemas = d.get_tools_schema()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "add"
    assert schemas[0]["description"] == "Add two numbers"


def test_multiple_tools():
    d = Dispatcher(sandbox_path="/tmp")
    d.register(AddTool(sandbox_path="/tmp"))
    d.register(FailTool(sandbox_path="/tmp"))
    schemas = d.get_tools_schema()
    assert len(schemas) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dispatcher.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Tool protocol**

```python
# harness/tools/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from harness.llm.schemas import ToolResult


class Tool(ABC):
    name: str
    description: str
    schema: dict[str, Any]
    sandbox_path: Path

    def __init__(self, sandbox_path: str | Path):
        self.sandbox_path = Path(sandbox_path)

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        ...
```

- [ ] **Step 4: Implement Dispatcher**

```python
# harness/tools/dispatcher.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from harness.llm.schemas import ToolCall, ToolResult
from harness.tools.base import Tool


class Dispatcher:
    def __init__(self, sandbox_path: str | Path):
        self.sandbox_path = Path(sandbox_path)
        self.registry: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self.registry[tool.name] = tool

    def execute(self, tool_call: ToolCall) -> ToolResult:
        tool = self.registry.get(tool_call.name)
        if not tool:
            return ToolResult(success=False, error=f"unknown_tool: {tool_call.name}")
        try:
            return tool.execute(**tool_call.args)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def get_tools_schema(self) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "schema": t.schema}
            for t in self.registry.values()
        ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_dispatcher.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add harness/tools/base.py harness/tools/dispatcher.py tests/test_dispatcher.py
git commit -m "feat: add tool protocol and dispatcher"
```

---

## Task 6: Tools — read_file, glob, grep

**Files:**
- Create: `harness/tools/read_file.py`
- Create: `harness/tools/glob_tool.py`
- Create: `harness/tools/grep_tool.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `Tool` protocol from `harness/tools/base.py`, `ToolResult` from `harness/llm/schemas.py`
- Produces: `ReadFileTool`, `GlobTool`, `GrepTool` — registered into Dispatcher

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tools.py
import os
import tempfile
from pathlib import Path

import pytest

from harness.llm.schemas import ToolResult


@pytest.fixture
def sandbox(tmp_path):
    (tmp_path / "main.py").write_text("def hello():\n    print('hello world')\n\ndef bye():\n    print('bye')\n")
    (tmp_path / "utils.py").write_text("def add(a, b):\n    return a + b\n")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "helper.py").write_text("def helper():\n    pass\n")
    return tmp_path


def test_read_file_success(sandbox):
    from harness.tools.read_file import ReadFileTool
    tool = ReadFileTool(sandbox_path=sandbox)
    result = tool.execute(path="main.py")
    assert result.success is True
    assert "def hello()" in result.data


def test_read_file_not_found(sandbox):
    from harness.tools.read_file import ReadFileTool
    tool = ReadFileTool(sandbox_path=sandbox)
    result = tool.execute(path="nonexistent.py")
    assert result.success is False
    assert "not found" in result.error.lower()


def test_read_file_outside_sandbox(sandbox):
    from harness.tools.read_file import ReadFileTool
    tool = ReadFileTool(sandbox_path=sandbox)
    result = tool.execute(path="../../../etc/passwd")
    assert result.success is False
    assert "sandbox" in result.error.lower()


def test_glob_finds_files(sandbox):
    from harness.tools.glob_tool import GlobTool
    tool = GlobTool(sandbox_path=sandbox)
    result = tool.execute(pattern="**/*.py")
    assert result.success is True
    files = result.data
    assert "main.py" in files
    assert "utils.py" in files
    assert "sub/helper.py" in files


def test_glob_no_matches(sandbox):
    from harness.tools.glob_tool import GlobTool
    tool = GlobTool(sandbox_path=sandbox)
    result = tool.execute(pattern="**/*.rs")
    assert result.success is True
    assert result.data == []


def test_glob_outside_sandbox(sandbox):
    from harness.tools.glob_tool import GlobTool
    tool = GlobTool(sandbox_path=sandbox)
    result = tool.execute(pattern="../../**/*.py")
    assert result.success is False
    assert "sandbox" in result.error.lower()


def test_grep_finds_pattern(sandbox):
    from harness.tools.grep_tool import GrepTool
    tool = GrepTool(sandbox_path=sandbox)
    result = tool.execute(pattern="def\\s+\\w+")
    assert result.success is True
    assert any("hello" in line for line in result.data)
    assert any("add" in line for line in result.data)


def test_grep_in_specific_file(sandbox):
    from harness.tools.grep_tool import GrepTool
    tool = GrepTool(sandbox_path=sandbox)
    result = tool.execute(pattern="def\\s+hello", path="main.py")
    assert result.success is True
    assert len(result.data) == 1
    assert "hello" in result.data[0]


def test_grep_no_matches(sandbox):
    from harness.tools.grep_tool import GrepTool
    tool = GrepTool(sandbox_path=sandbox)
    result = tool.execute(pattern="NONEXISTENT_PATTERN")
    assert result.success is True
    assert result.data == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ReadFileTool**

```python
# harness/tools/read_file.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from harness.llm.schemas import ToolResult
from harness.tools.base import Tool


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the contents of a file. Returns file content on success."
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "File path relative to sandbox"}},
        "required": ["path"],
    }

    def _resolve(self, path: str) -> Path | None:
        resolved = (self.sandbox_path / path).resolve()
        if not str(resolved).startswith(str(self.sandbox_path.resolve())):
            return None
        return resolved

    def execute(self, path: str, **kwargs) -> ToolResult:
        resolved = self._resolve(path)
        if resolved is None:
            return ToolResult(success=False, error="path_outside_sandbox")
        if not resolved.exists():
            return ToolResult(success=False, error=f"file_not_found: {path}")
        if not resolved.is_file():
            return ToolResult(success=False, error=f"not_a_file: {path}")
        return ToolResult(success=True, data=resolved.read_text())
```

- [ ] **Step 4: Implement GlobTool**

```python
# harness/tools/glob_tool.py
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

from harness.llm.schemas import ToolResult
from harness.tools.base import Tool


class GlobTool(Tool):
    name = "glob"
    description = "Find files matching a pattern. Returns list of relative paths."
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)"}},
        "required": ["pattern"],
    }

    def execute(self, pattern: str, **kwargs) -> ToolResult:
        sandbox_resolved = self.sandbox_path.resolve()
        if ".." in pattern and sandbox_resolved not in Path(sandbox_resolved / pattern).resolve().parents:
            return ToolResult(success=False, error="path_outside_sandbox")
        matches = []
        sandbox_path_obj = Path(sandbox_resolved)
        for p in sandbox_path_obj.rglob(pattern.replace("**/", "**")):
            if p.is_file():
                rel = p.relative_to(sandbox_path_obj)
                if ".." not in str(rel):
                    matches.append(str(rel))
        return ToolResult(success=True, data=sorted(matches))
```

- [ ] **Step 5: Implement GrepTool**

```python
# harness/tools/grep_tool.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from harness.llm.schemas import ToolResult
from harness.tools.base import Tool


class GrepTool(Tool):
    name = "grep"
    description = "Search file contents with regex. Returns list of matching lines (with file:line prefix)."
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern"},
            "path": {"type": "string", "description": "Optional file or directory to search in (relative to sandbox)"},
        },
        "required": ["pattern"],
    }

    def execute(self, pattern: str, path: str = None, **kwargs) -> ToolResult:
        sandbox_resolved = self.sandbox_path.resolve()
        search_root = sandbox_resolved
        if path:
            search_root = (sandbox_resolved / path).resolve()
            if not str(search_root).startswith(str(sandbox_resolved)):
                return ToolResult(success=False, error="path_outside_sandbox")
            if not search_root.exists():
                return ToolResult(success=False, error=f"path_not_found: {path}")

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolResult(success=False, error=f"invalid_regex: {e}")

        matches = []
        if search_root.is_file():
            files = [search_root]
        else:
            files = [p for p in search_root.rglob("*") if p.is_file()]

        for fpath in sorted(files):
            try:
                lines = fpath.read_text().splitlines()
            except (UnicodeDecodeError, PermissionError):
                continue
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    rel = fpath.relative_to(sandbox_resolved)
                    matches.append(f"{rel}:{i}: {line.strip()}")

        return ToolResult(success=True, data=matches)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_tools.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add harness/tools/read_file.py harness/tools/glob_tool.py harness/tools/grep_tool.py tests/test_tools.py
git commit -m "feat: add read_file, glob, and grep tools"
```

---

## Task 7: Tools — edit_file (3-state matching)

**Files:**
- Create: `harness/tools/edit_file.py`

**Interfaces:**
- Consumes: `Tool` protocol, `ToolResult`
- Produces: `EditFileTool` — registered into Dispatcher. Result `data` includes `{"diff": "..."}`.

- [ ] **Step 1: Add edit_file tests to test_tools.py**

```python
# Append to tests/test_tools.py
def test_edit_file_unique_match(sandbox):
    from harness.tools.edit_file import EditFileTool
    tool = EditFileTool(sandbox_path=sandbox)
    result = tool.execute(
        path="utils.py",
        old_string="def add(a, b):\n    return a + b",
        new_string="def add(a: int, b: int) -> int:\n    return a + b",
    )
    assert result.success is True
    assert "diff" in result.data
    content = (sandbox / "utils.py").read_text()
    assert "a: int" in content


def test_edit_file_no_match(sandbox):
    from harness.tools.edit_file import EditFileTool
    tool = EditFileTool(sandbox_path=sandbox)
    result = tool.execute(
        path="main.py",
        old_string="def nonexistent():\n    pass",
        new_string="def replaced():\n    pass",
    )
    assert result.success is False
    assert "no_match" in result.error


def test_edit_file_multiple_matches(sandbox, tmp_path):
    from harness.tools.edit_file import EditFileTool
    (sandbox / "dup.py").write_text("x = 1\nx = 1\nx = 1\n")
    tool = EditFileTool(sandbox_path=sandbox)
    result = tool.execute(
        path="dup.py",
        old_string="x = 1",
        new_string="x = 2",
    )
    assert result.success is False
    assert "multiple_matches" in result.error


def test_edit_file_outside_sandbox(sandbox):
    from harness.tools.edit_file import EditFileTool
    tool = EditFileTool(sandbox_path=sandbox)
    result = tool.execute(
        path="../../../etc/passwd",
        old_string="root",
        new_string="nobody",
    )
    assert result.success is False
    assert "sandbox" in result.error.lower()


def test_edit_file_produces_diff(sandbox):
    from harness.tools.edit_file import EditFileTool
    tool = EditFileTool(sandbox_path=sandbox)
    result = tool.execute(
        path="utils.py",
        old_string="def add(a, b):",
        new_string="def add(a: int, b: int):",
    )
    assert result.success is True
    assert "-def add(a, b):" in result.data["diff"]
    assert "+def add(a: int, b: int):" in result.data["diff"]
```

- [ ] **Step 2: Implement EditFileTool**

```python
# harness/tools/edit_file.py
from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from harness.llm.schemas import ToolResult
from harness.tools.base import Tool


class EditFileTool(Tool):
    name = "edit_file"
    description = "Replace an exact string match in a file. Fails if 0 or >1 matches."
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to sandbox"},
            "old_string": {"type": "string", "description": "Exact string to find"},
            "new_string": {"type": "string", "description": "Replacement string"},
        },
        "required": ["path", "old_string", "new_string"],
    }

    def _resolve(self, path: str) -> Path | None:
        resolved = (self.sandbox_path / path).resolve()
        if not str(resolved).startswith(str(self.sandbox_path.resolve())):
            return None
        return resolved

    def execute(self, path: str, old_string: str, new_string: str, **kwargs) -> ToolResult:
        resolved = self._resolve(path)
        if resolved is None:
            return ToolResult(success=False, error="path_outside_sandbox")
        if not resolved.exists():
            return ToolResult(success=False, error=f"file_not_found: {path}")

        content = resolved.read_text()
        count = content.count(old_string)

        if count == 0:
            return ToolResult(success=False, error="no_match")
        if count > 1:
            return ToolResult(success=False, error=f"multiple_matches: found {count} occurrences")

        new_content = content.replace(old_string, new_string, 1)
        resolved.write_text(new_content)

        diff_lines = list(difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        ))
        diff_str = "".join(diff_lines)

        return ToolResult(success=True, data={"diff": diff_str, "path": path})
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_tools.py -v -k edit_file`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add harness/tools/edit_file.py tests/test_tools.py
git commit -m "feat: add edit_file tool with 3-state matching"
```

---

## Task 8: Tools — run_command (with timeout)

**Files:**
- Create: `harness/tools/run_command.py`

**Interfaces:**
- Consumes: `Tool` protocol, `ToolResult`
- Produces: `RunCommandTool` — registered into Dispatcher. Returns `exit_code`, `stdout`, `stderr` in `data`.

- [ ] **Step 1: Add run_command tests to test_tools.py**

```python
# Append to tests/test_tools.py
def test_run_command_success(sandbox):
    from harness.tools.run_command import RunCommandTool
    tool = RunCommandTool(sandbox_path=sandbox)
    result = tool.execute(cmd="echo hello", timeout=10)
    assert result.success is True
    assert result.data["exit_code"] == 0
    assert "hello" in result.data["stdout"]


def test_run_command_failure_exit_code(sandbox):
    from harness.tools.run_command import RunCommandTool
    tool = RunCommandTool(sandbox_path=sandbox)
    result = tool.execute(cmd="false", timeout=10)
    assert result.success is True
    assert result.data["exit_code"] != 0


def test_run_command_timeout(sandbox):
    from harness.tools.run_command import RunCommandTool
    tool = RunCommandTool(sandbox_path=sandbox)
    result = tool.execute(cmd="sleep 60", timeout=1)
    assert result.success is False
    assert "timeout" in result.error.lower()


def test_run_command_captures_stderr(sandbox):
    from harness.tools.run_command import RunCommandTool
    tool = RunCommandTool(sandbox_path=sandbox)
    result = tool.execute(cmd="echo error >&2", timeout=10)
    assert result.success is True
    assert "error" in result.data["stderr"]


def test_run_command_runs_in_sandbox(sandbox):
    from harness.tools.run_command import RunCommandTool
    (sandbox / "hello.txt").write_text("hi")
    tool = RunCommandTool(sandbox_path=sandbox)
    result = tool.execute(cmd="cat hello.txt", timeout=10)
    assert result.success is True
    assert "hi" in result.data["stdout"]
```

- [ ] **Step 2: Implement RunCommandTool**

```python
# harness/tools/run_command.py
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from harness.llm.schemas import ToolResult
from harness.tools.base import Tool


class RunCommandTool(Tool):
    name = "run_command"
    description = "Execute a shell command in the sandbox directory. Returns exit_code, stdout, stderr."
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "cmd": {"type": "string", "description": "Shell command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 60)"},
        },
        "required": ["cmd"],
    }

    def execute(self, cmd: str, timeout: int = 60, **kwargs) -> ToolResult:
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.sandbox_path),
            )
            return ToolResult(
                success=True,
                data={
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                },
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"command_timeout_after_{timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_tools.py -v -k run_command`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add harness/tools/run_command.py tests/test_tools.py
git commit -m "feat: add run_command tool with timeout"
```

---

## Task 9: Guardrail Rules & Pre-Action Guards

**Files:**
- Create: `harness/guardrails/rules.py`
- Create: `harness/guardrails/pre_action.py`
- Test: `tests/test_guardrails.py`

**Interfaces:**
- Consumes: `ToolCall`, `ToolResult`, `GuardResult` from schemas; `GuardrailsConfig` from config
- Produces: `GuardrailRules`, `PreActionGuard` — used by `loop.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_guardrails.py
import pytest

from harness.core.config import GuardrailsConfig
from harness.guardrails.rules import GuardrailRules
from harness.guardrails.pre_action import PreActionGuard
from harness.llm.schemas import ToolCall


@pytest.fixture
def config():
    return GuardrailsConfig(
        blacklist=[".env", ".git", "secrets/"],
        max_diff_lines=100,
        require_approval_commands=["rm", "del", "drop", "delete"],
        max_command_timeout=30,
        max_command_memory_mb=256,
        hitl_timeout=120,
    )


@pytest.fixture
def mock_hitl_allow():
    class MockHitl:
        was_called = False
        def request_approval(self, tool_call, reason):
            self.was_called = True
            return "approve"
    return MockHitl()


@pytest.fixture
def mock_hitl_reject():
    class MockHitl:
        was_called = False
        def request_approval(self, tool_call, reason):
            self.was_called = True
            return "reject"
    return MockHitl()


class TestPreActionGuardBlacklist:
    def test_blacklist_blocks_env_file(self, config, mock_hitl_allow):
        guard = PreActionGuard(rules=config, hitl=mock_hitl_allow)
        call = ToolCall(name="read_file", args={"path": ".env"})
        result = guard.check(call)
        assert result.allowed is False
        assert "blacklist" in result.reason.lower()

    def test_blacklist_blocks_git_directory(self, config, mock_hitl_allow):
        guard = PreActionGuard(rules=config, hitl=mock_hitl_allow)
        call = ToolCall(name="read_file", args={"path": ".git/config"})
        result = guard.check(call)
        assert result.allowed is False

    def test_blacklist_blocks_secrets_directory(self, config, mock_hitl_allow):
        guard = PreActionGuard(rules=config, hitl=mock_hitl_allow)
        call = ToolCall(name="read_file", args={"path": "secrets/key.pem"})
        result = guard.check(call)
        assert result.allowed is False

    def test_allows_non_blacklisted_file(self, config, mock_hitl_allow):
        guard = PreActionGuard(rules=config, hitl=mock_hitl_allow)
        call = ToolCall(name="read_file", args={"path": "main.py"})
        result = guard.check(call)
        assert result.allowed is True


class TestPreActionGuardResourceLimits:
    def test_timeout_exceeded(self, config, mock_hitl_allow):
        guard = PreActionGuard(rules=config, hitl=mock_hitl_allow)
        call = ToolCall(name="run_command", args={"cmd": "echo hi", "timeout": 9999})
        result = guard.check(call)
        assert result.allowed is False
        assert "timeout" in result.reason.lower()

    def test_timeout_within_limit(self, config, mock_hitl_allow):
        guard = PreActionGuard(rules=config, hitl=mock_hitl_allow)
        call = ToolCall(name="run_command", args={"cmd": "echo hi", "timeout": 10})
        result = guard.check(call)
        assert result.allowed is True

    def test_timeout_default_allowed(self, config, mock_hitl_allow):
        guard = PreActionGuard(rules=config, hitl=mock_hitl_allow)
        call = ToolCall(name="run_command", args={"cmd": "echo hi"})
        result = guard.check(call)
        assert result.allowed is True


class TestPreActionGuardHITL:
    def test_hitl_trigger_on_dangerous_command(self, config, mock_hitl_allow):
        guard = PreActionGuard(rules=config, hitl=mock_hitl_allow)
        call = ToolCall(name="run_command", args={"cmd": "rm -rf /"})
        result = guard.check(call)
        assert mock_hitl_allow.was_called is True
        assert result.allowed is True

    def test_hitl_reject_blocks(self, config, mock_hitl_reject):
        guard = PreActionGuard(rules=config, hitl=mock_hitl_reject)
        call = ToolCall(name="run_command", args={"cmd": "rm -rf /"})
        result = guard.check(call)
        assert result.allowed is False
        assert "human_rejected" in result.reason

    def test_hitl_not_triggered_for_safe_command(self, config, mock_hitl_allow):
        guard = PreActionGuard(rules=config, hitl=mock_hitl_allow)
        call = ToolCall(name="run_command", args={"cmd": "python -c 'print(1)'"})
        result = guard.check(call)
        assert mock_hitl_allow.was_called is False
        assert result.allowed is True


class TestGuardrailRules:
    def test_is_blacklisted_env(self, config):
        rules = GuardrailRules(config)
        call = ToolCall(name="read_file", args={"path": ".env"})
        assert rules.is_blacklisted(call) is True

    def test_is_blacklisted_nested(self, config):
        rules = GuardrailRules(config)
        call = ToolCall(name="edit_file", args={"path": ".git/HEAD"})
        assert rules.is_blacklisted(call) is True

    def test_is_blacklisted_safe(self, config):
        rules = GuardrailRules(config)
        call = ToolCall(name="read_file", args={"path": "main.py"})
        assert rules.is_blacklisted(call) is False

    def test_exceeds_timeout_limit(self, config):
        rules = GuardrailRules(config)
        call = ToolCall(name="run_command", args={"cmd": "echo hi", "timeout": 9999})
        assert rules.exceeds_limits(call) is True

    def test_requires_approval(self, config):
        rules = GuardrailRules(config)
        call = ToolCall(name="run_command", args={"cmd": "rm -rf /"})
        assert rules.requires_approval(call) is True

    def test_does_not_require_approval_safe(self, config):
        rules = GuardrailRules(config)
        call = ToolCall(name="run_command", args={"cmd": "pytest"})
        assert rules.requires_approval(call) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_guardrails.py -v`
Expected: FAIL

- [ ] **Step 3: Implement GuardrailRules**

```python
# harness/guardrails/rules.py
from __future__ import annotations

from harness.core.config import GuardrailsConfig
from harness.llm.schemas import ToolCall


class GuardrailRules:
    def __init__(self, config: GuardrailsConfig):
        self.config = config

    def is_blacklisted(self, tool_call: ToolCall) -> bool:
        path = tool_call.args.get("path", "")
        for pattern in self.config.blacklist:
            if path == pattern or path.startswith(pattern + "/") or pattern.rstrip("/").endswith("/" + path.lstrip("/")):
                return True
            if "/" in pattern:
                prefix = pattern.rstrip("/")
                if path.startswith(prefix + "/") or path == prefix:
                    return True
            else:
                parts = path.split("/")
                if pattern in parts or path.startswith(pattern):
                    return True
        return False

    def exceeds_limits(self, tool_call: ToolCall) -> bool:
        if tool_call.name != "run_command":
            return False
        timeout = tool_call.args.get("timeout", 60)
        if timeout > self.config.max_command_timeout:
            return True
        return False

    def requires_approval(self, tool_call: ToolCall) -> bool:
        if tool_call.name != "run_command":
            return False
        cmd = tool_call.args.get("cmd", "")
        for dangerous in self.config.require_approval_commands:
            if dangerous in cmd.split():
                return True
            if cmd.strip().startswith(dangerous + " ") or cmd.strip() == dangerous:
                return True
        return False
```

- [ ] **Step 4: Implement PreActionGuard**

```python
# harness/guardrails/pre_action.py
from __future__ import annotations

from harness.core.config import GuardrailsConfig
from harness.guardrails.rules import GuardrailRules
from harness.llm.schemas import GuardResult, ToolCall


class PreActionGuard:
    def __init__(self, rules: GuardrailsConfig, hitl):
        self.rules = GuardrailRules(rules)
        self.hitl = hitl

    def check(self, tool_call: ToolCall) -> GuardResult:
        if self.rules.is_blacklisted(tool_call):
            return GuardResult(allowed=False, reason="blacklisted_path")

        if self.rules.exceeds_limits(tool_call):
            return GuardResult(allowed=False, reason="resource_limit_exceeded")

        if self.rules.requires_approval(tool_call):
            decision = self.hitl.request_approval(tool_call, reason="dangerous_command")
            if decision != "approve":
                return GuardResult(allowed=False, reason="human_rejected")

        return GuardResult(allowed=True)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_guardrails.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add harness/guardrails/rules.py harness/guardrails/pre_action.py tests/test_guardrails.py
git commit -m "feat: add guardrail rules and pre-action guards (blacklist, limits, HITL)"
```

---

## Task 10: Post-Action Guards

**Files:**
- Create: `harness/guardrails/post_action.py`

**Interfaces:**
- Consumes: `ToolCall`, `ToolResult`, `GuardResult`; `GuardrailsConfig` from config
- Produces: `PostActionGuard` — used by `loop.py` after tool execution

- [ ] **Step 1: Add post-action tests to test_guardrails.py**

```python
# Append to tests/test_guardrails.py
from harness.guardrails.post_action import PostActionGuard
from harness.llm.schemas import ToolResult


class TestPostActionGuard:
    def test_diff_within_limit(self, config):
        guard = PostActionGuard(rules=config)
        call = ToolCall(name="edit_file", args={"path": "main.py"})
        result = ToolResult(success=True, data={"diff": "line1\nline2\nline3"})
        gr = guard.check(call, result)
        assert gr.allowed is True

    def test_diff_exceeds_limit(self, config):
        config.max_diff_lines = 3
        guard = PostActionGuard(rules=config)
        call = ToolCall(name="edit_file", args={"path": "main.py"})
        result = ToolResult(success=True, data={"diff": "\n".join([f"line{i}" for i in range(10)])})
        gr = guard.check(call, result)
        assert gr.allowed is False
        assert "diff_too_large" in gr.reason

    def test_deletes_tests_rejected(self, config):
        guard = PostActionGuard(rules=config)
        call = ToolCall(name="edit_file", args={"path": "tests/test_main.py"})
        result = ToolResult(success=True, data={"diff": "-def test_something():\n-    assert True\n+pass"})
        gr = guard.check(call, result)
        assert gr.allowed is False
        assert "cannot_delete_tests" in gr.reason

    def test_non_edit_file_allowed(self, config):
        guard = PostActionGuard(rules=config)
        call = ToolCall(name="read_file", args={"path": "main.py"})
        result = ToolResult(success=True, data="content")
        gr = guard.check(call, result)
        assert gr.allowed is True

    def test_failed_tool_result_skipped(self, config):
        guard = PostActionGuard(rules=config)
        call = ToolCall(name="edit_file", args={})
        result = ToolResult(success=False, error="no_match")
        gr = guard.check(call, result)
        assert gr.allowed is True
```

- [ ] **Step 2: Implement PostActionGuard**

```python
# harness/guardrails/post_action.py
from __future__ import annotations

import re

from harness.core.config import GuardrailsConfig
from harness.llm.schemas import GuardResult, ToolCall, ToolResult


class PostActionGuard:
    def __init__(self, rules: GuardrailsConfig):
        self.config = rules

    def check(self, tool_call: ToolCall, result: ToolResult) -> GuardResult:
        if not result.success:
            return GuardResult(allowed=True)

        if tool_call.name != "edit_file":
            return GuardResult(allowed=True)

        data = result.data or {}
        diff_str = data.get("diff", "")
        if diff_str:
            diff_lines = [l for l in diff_str.split("\n") if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
            if len(diff_lines) > self.config.max_diff_lines:
                return GuardResult(allowed=False, reason=f"diff_too_large: {len(diff_lines)} lines > {self.config.max_diff_lines}")

        path = tool_call.args.get("path", "")
        if self._deletes_tests(diff_str, path):
            return GuardResult(allowed=False, reason="cannot_delete_tests")

        return GuardResult(allowed=True)

    def _deletes_tests(self, diff_str: str, path: str) -> bool:
        if "test" not in path.lower():
            return False
        removed_lines = [l for l in diff_str.split("\n") if l.startswith("-") and not l.startswith("---")]
        for line in removed_lines:
            stripped = line[1:].strip()
            if re.match(r"(def test_|class Test|assert )", stripped):
                return True
        return False
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_guardrails.py -v -k PostAction`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add harness/guardrails/post_action.py tests/test_guardrails.py
git commit -m "feat: add post-action guards (diff size, test deletion)"
```

---

## Task 11: HITL Mechanism

**Files:**
- Create: `harness/guardrails/hitl.py`
- Test: `tests/test_hitl.py`

**Interfaces:**
- Consumes: `ToolCall` from schemas
- Produces: `HitlHandler` protocol, `AutoApproveHitl`, `BlockingHitl` (for WebUI) — injected into `PreActionGuard`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_hitl.py
import threading
import pytest
from harness.guardrails.hitl import AutoApproveHitl, BlockingHitl
from harness.llm.schemas import ToolCall


def test_auto_approve():
    hitl = AutoApproveHitl()
    call = ToolCall(name="run_command", args={"cmd": "rm -rf /"})
    decision = hitl.request_approval(call, reason="dangerous")
    assert decision == "approve"


def test_blocking_hitl_approve():
    hitl = BlockingHitl(timeout=5)
    call = ToolCall(name="run_command", args={"cmd": "rm -rf /"})

    def approve():
        import time
        time.sleep(0.1)
        hitl.respond("approve")

    t = threading.Thread(target=approve)
    t.start()
    decision = hitl.request_approval(call, reason="dangerous")
    t.join()
    assert decision == "approve"


def test_blocking_hitl_reject():
    hitl = BlockingHitl(timeout=5)
    call = ToolCall(name="run_command", args={"cmd": "rm -rf /"})

    def reject():
        import time
        time.sleep(0.1)
        hitl.respond("reject")

    t = threading.Thread(target=reject)
    t.start()
    decision = hitl.request_approval(call, reason="dangerous")
    t.join()
    assert decision == "reject"


def test_blocking_hitl_timeout():
    hitl = BlockingHitl(timeout=1)
    call = ToolCall(name="run_command", args={"cmd": "rm -rf /"})
    decision = hitl.request_approval(call, reason="dangerous")
    assert decision == "timeout"


def test_blocking_hitl_captures_tool_call():
    hitl = BlockingHitl(timeout=5)
    call = ToolCall(name="run_command", args={"cmd": "rm -rf /"})

    def approve():
        import time
        time.sleep(0.1)
        assert hitl.pending_tool_call == call
        hitl.respond("approve")

    t = threading.Thread(target=approve)
    t.start()
    hitl.request_approval(call, reason="dangerous")
    t.join()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_hitl.py -v`
Expected: FAIL

- [ ] **Step 3: Implement HITL mechanism**

```python
# harness/guardrails/hitl.py
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Optional

from harness.llm.schemas import ToolCall


class HitlHandler(ABC):
    @abstractmethod
    def request_approval(self, tool_call: ToolCall, reason: str) -> str:
        ...


class AutoApproveHitl(HitlHandler):
    def request_approval(self, tool_call: ToolCall, reason: str) -> str:
        return "approve"


class BlockingHitl(HitlHandler):
    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.pending_tool_call: Optional[ToolCall] = None
        self.pending_reason: Optional[str] = None
        self._event = threading.Event()
        self._decision: Optional[str] = None
        self.on_request: Optional[callable] = None

    def request_approval(self, tool_call: ToolCall, reason: str) -> str:
        self.pending_tool_call = tool_call
        self.pending_reason = reason
        self._event.clear()
        self._decision = None

        if self.on_request:
            self.on_request(tool_call, reason)

        signalled = self._event.wait(timeout=self.timeout)
        self.pending_tool_call = None
        self.pending_reason = None

        if not signalled:
            return "timeout"
        return self._decision or "timeout"

    def respond(self, decision: str):
        self._decision = decision
        self._event.set()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_hitl.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add harness/guardrails/hitl.py tests/test_hitl.py
git commit -m "feat: add HITL mechanism (AutoApprove + BlockingHitl with timeout)"
```

---

## Task 12: Feedback Parsers

**Files:**
- Create: `harness/feedback/parsers.py`
- Test: `tests/test_parsers.py`

**Interfaces:**
- Consumes: nothing (pure functions)
- Produces: `Parsers` class — used by `FeedbackPipeline`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_parsers.py
import pytest
from harness.feedback.parsers import Parsers


class TestParseStderr:
    def test_python_syntax_error(self):
        stderr = """  File "main.py", line 42
    def foo(
            ^
SyntaxError: unexpected EOF"""
        errors = Parsers.parse_stderr(stderr, "")
        assert len(errors) > 0
        assert any("SyntaxError" in e for e in errors)

    def test_python_runtime_error(self):
        stderr = """Traceback (most recent call last):
  File "main.py", line 10, in <module>
    raise ValueError("bad input")
ValueError: bad input"""
        errors = Parsers.parse_stderr(stderr, "")
        assert any("ValueError" in e for e in errors)

    def test_empty_output(self):
        errors = Parsers.parse_stderr("", "")
        assert errors == []

    def test_no_errors(self):
        stderr = "Build complete.\nDone."
        errors = Parsers.parse_stderr(stderr, "")
        assert errors == []


class TestParseTestOutput:
    def test_pytest_failures(self):
        stdout = """=========================== FAILURES ===========================
___________________________ test_add ___________________________

    def test_add():
>       assert add(1, 2) == 4
E       assert 3 == 4

tests/test_main.py:5: AssertionError
========================= 2 failed, 1 passed =================="""
        failures = Parsers.parse_test_output("", stdout)
        assert len(failures) > 0
        assert any("FAIL" in f.upper() or "assert" in f.lower() for f in failures)

    def test_pytest_passed(self):
        stdout = "========================= 5 passed =========================="
        failures = Parsers.parse_test_output("", stdout)
        assert failures == []

    def test_mixed_stderr_stdout(self):
        stderr = "error: something broke"
        stdout = "FAILED test_one"
        errors = Parsers.parse_stderr(stderr, stdout)
        assert len(errors) > 0
```

- [ ] **Step 2: Implement parsers**

```python
# harness/feedback/parsers.py
from __future__ import annotations

import re


class Parsers:
    ERROR_PATTERNS = [
        re.compile(r"^(Traceback|.*Error:|.*Exception:)", re.IGNORECASE),
        re.compile(r"^.*error.*$", re.IGNORECASE),
        re.compile(r"^.*FAILED.*$", re.IGNORECASE),
        re.compile(r"^File .* line \d+", re.IGNORECASE),
    ]

    TEST_FAILURE_PATTERNS = [
        re.compile(r"^.*FAILED.*$"),
        re.compile(r"^.*AssertionError.*$"),
        re.compile(r"^>\s+assert"),
        re.compile(r"^E\s+", re.MULTILINE),
    ]

    @staticmethod
    def parse_stderr(stderr: str, stdout: str) -> list[str]:
        combined = (stderr + "\n" + stdout).strip()
        if not combined:
            return []
        lines = combined.split("\n")
        errors = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            for pattern in Parsers.ERROR_PATTERNS:
                if pattern.search(stripped):
                    errors.append(stripped)
                    break
        return errors

    @staticmethod
    def parse_test_output(stderr: str, stdout: str) -> list[str]:
        combined = (stderr + "\n" + stdout).strip()
        if not combined:
            return []

        passed_match = re.search(r"(\d+) passed", combined)
        failed_match = re.search(r"(\d+) failed", combined)
        if failed_match and int(failed_match.group(1)) > 0:
            failures = []
            lines = combined.split("\n")
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                for pattern in Parsers.TEST_FAILURE_PATTERNS:
                    if pattern.search(stripped):
                        failures.append(stripped)
                        break
            return failures if failures else [combined[:200]]

        if passed_match and not failed_match:
            return []

        errors = Parsers.parse_stderr(stderr, stdout)
        return errors
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_parsers.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add harness/feedback/parsers.py tests/test_parsers.py
git commit -m "feat: add feedback parsers (Python stderr + pytest output)"
```

---

## Task 13: Feedback Pipeline

**Files:**
- Create: `harness/feedback/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `Parsers` from parsers.py, `RunCommandTool` from tools, `HarnessConfig` from config; `FeedbackResult` from schemas
- Produces: `FeedbackPipeline` — called by `Agent.run()` in loop.py

- [ ] **Step 1: Write failing tests**

```python
# tests/test_pipeline.py
import pytest
from unittest.mock import MagicMock

from harness.core.config import HarnessConfig
from harness.feedback.pipeline import FeedbackPipeline
from harness.llm.schemas import ToolResult


@pytest.fixture
def config():
    return HarnessConfig(
        build_cmd="make build",
        test_cmd="pytest",
        build_timeout=60,
        test_timeout=120,
        max_feedback_lines=50,
    )


def test_build_failure_skips_test(config):
    mock_cmd = MagicMock()
    mock_cmd.execute.return_value = ToolResult(
        success=True,
        data={"exit_code": 1, "stderr": "SyntaxError: line 42", "stdout": ""},
    )
    pipeline = FeedbackPipeline(run_cmd=mock_cmd, config=config)
    result = pipeline.run()
    assert result.stage == "build"
    assert result.success is False
    assert any("SyntaxError" in e for e in result.errors)
    assert mock_cmd.execute.call_count == 1


def test_build_success_then_test_failure(config):
    mock_cmd = MagicMock()
    mock_cmd.execute.side_effect = [
        ToolResult(success=True, data={"exit_code": 0, "stderr": "", "stdout": "Build OK"}),
        ToolResult(success=True, data={"exit_code": 1, "stderr": "", "stdout": "FAILED test_one\nAssertionError: 1 != 2"}),
    ]
    pipeline = FeedbackPipeline(run_cmd=mock_cmd, config=config)
    result = pipeline.run()
    assert result.stage == "test"
    assert result.success is False
    assert mock_cmd.execute.call_count == 2


def test_build_and_test_both_pass(config):
    mock_cmd = MagicMock()
    mock_cmd.execute.side_effect = [
        ToolResult(success=True, data={"exit_code": 0, "stderr": "", "stdout": "Build OK"}),
        ToolResult(success=True, data={"exit_code": 0, "stderr": "", "stdout": "5 passed"}),
    ]
    pipeline = FeedbackPipeline(run_cmd=mock_cmd, config=config)
    result = pipeline.run()
    assert result.success is True
    assert result.stage == "test"


def test_no_build_cmd_configured():
    config = HarnessConfig(build_cmd=None, test_cmd="pytest")
    mock_cmd = MagicMock()
    pipeline = FeedbackPipeline(run_cmd=mock_cmd, config=config)
    result = pipeline.run()
    assert result.stage == "test"
    assert mock_cmd.execute.call_count == 1


def test_no_test_cmd_configured():
    config = HarnessConfig(build_cmd="make", test_cmd=None)
    mock_cmd = MagicMock()
    mock_cmd.execute.return_value = ToolResult(success=True, data={"exit_code": 0, "stderr": "", "stdout": "OK"})
    pipeline = FeedbackPipeline(run_cmd=mock_cmd, config=config)
    result = pipeline.run()
    assert result.success is True
    assert mock_cmd.execute.call_count == 1


def test_feedback_truncated_to_max_lines(config):
    config.max_feedback_lines = 3
    mock_cmd = MagicMock()
    long_errors = "\n".join([f"Error{i}: something wrong" for i in range(20)])
    mock_cmd.execute.return_value = ToolResult(
        success=True,
        data={"exit_code": 1, "stderr": long_errors, "stdout": ""},
    )
    pipeline = FeedbackPipeline(run_cmd=mock_cmd, config=config)
    result = pipeline.run()
    assert result.success is False
    assert len(result.errors) <= 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL

- [ ] **Step 3: Implement pipeline**

```python
# harness/feedback/pipeline.py
from __future__ import annotations

from harness.core.config import HarnessConfig
from harness.feedback.parsers import Parsers
from harness.llm.schemas import FeedbackResult, ToolResult
from harness.tools.run_command import RunCommandTool


class FeedbackPipeline:
    def __init__(self, run_cmd, config: HarnessConfig):
        self.run_cmd = run_cmd
        self.config = config

    def run(self) -> FeedbackResult:
        if self.config.build_cmd:
            build_result = self.run_cmd.execute(cmd=self.config.build_cmd, timeout=self.config.build_timeout)
            if build_result.success and build_result.data and build_result.data["exit_code"] != 0:
                errors = Parsers.parse_stderr(build_result.data["stderr"], build_result.data["stdout"])
                errors = errors[: self.config.max_feedback_lines]
                return FeedbackResult(
                    stage="build",
                    success=False,
                    errors=errors,
                    raw_output=build_result.data["stderr"] + build_result.data["stdout"],
                )

        if not self.config.test_cmd:
            return FeedbackResult(stage="test", success=True)

        test_result = self.run_cmd.execute(cmd=self.config.test_cmd, timeout=self.config.test_timeout)
        if test_result.success and test_result.data:
            if test_result.data["exit_code"] != 0:
                failures = Parsers.parse_test_output(test_result.data["stderr"], test_result.data["stdout"])
                if not failures:
                    failures = Parsers.parse_stderr(test_result.data["stderr"], test_result.data["stdout"])
                failures = failures[: self.config.max_feedback_lines]
                return FeedbackResult(
                    stage="test",
                    success=False,
                    errors=failures,
                    raw_output=test_result.data["stderr"] + test_result.data["stdout"],
                )

        return FeedbackResult(stage="test", success=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pipeline.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add harness/feedback/pipeline.py tests/test_pipeline.py
git commit -m "feat: add feedback pipeline (build → test with short-circuit)"
```

---

## Task 14: Convergence

**Files:**
- Create: `harness/feedback/convergence.py`
- Test: `tests/test_convergence.py`

**Interfaces:**
- Consumes: `FeedbackResult` from schemas; `ConvergenceConfig` from config
- Produces: `Convergence` class — used by `Agent.run()` in loop.py to decide continue/stop

- [ ] **Step 1: Write failing tests**

```python
# tests/test_convergence.py
import pytest

from harness.core.config import ConvergenceConfig
from harness.feedback.convergence import Convergence
from harness.llm.schemas import FeedbackResult


def fail(n_errors: int) -> FeedbackResult:
    return FeedbackResult(stage="build", success=False, errors=[f"err{i}" for i in range(n_errors)])


def success_result() -> FeedbackResult:
    return FeedbackResult(stage="test", success=True)


class TestMaxIterations:
    def test_within_limit(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=5, stagnation_limit=3, no_edit_limit=3))
        assert c.should_stop(attempt=1) is False
        assert c.should_stop(attempt=4) is False

    def test_at_limit(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=5, stagnation_limit=3, no_edit_limit=3))
        assert c.should_stop(attempt=5) is True
        assert c.stop_reason == "max_iterations_reached"


class TestStagnation:
    def test_stagnation_after_n_rounds(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=10, stagnation_limit=3, no_edit_limit=10))
        c.update(fail(5), had_edit=True)
        c.update(fail(5), had_edit=True)
        c.update(fail(5), had_edit=True)
        assert c.should_stop(attempt=3) is True
        assert c.stop_reason == "stagnation"

    def test_progress_resets_stagnation(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=10, stagnation_limit=3, no_edit_limit=10))
        c.update(fail(5), had_edit=True)
        c.update(fail(5), had_edit=True)
        c.update(fail(3), had_edit=True)
        assert c.should_stop(attempt=3) is False
        c.update(fail(3), had_edit=True)
        c.update(fail(3), had_edit=True)
        c.update(fail(3), had_edit=True)
        assert c.should_stop(attempt=6) is True


class TestNoEdits:
    def test_no_edit_stop(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=10, stagnation_limit=10, no_edit_limit=3))
        c.update(fail(5), had_edit=False)
        c.update(fail(5), had_edit=False)
        c.update(fail(5), had_edit=False)
        assert c.should_stop(attempt=3) is True
        assert c.stop_reason == "no_edits"

    def test_edit_resets_no_edit_count(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=10, stagnation_limit=10, no_edit_limit=3))
        c.update(fail(5), had_edit=False)
        c.update(fail(5), had_edit=False)
        c.update(fail(5), had_edit=True)
        assert c.should_stop(attempt=3) is False


class TestSuccess:
    def test_success_feedback_not_stopped(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=10, stagnation_limit=3, no_edit_limit=3))
        c.update(success_result(), had_edit=True)
        assert c.should_stop(attempt=1) is False
```

- [ ] **Step 2: Implement convergence**

```python
# harness/feedback/convergence.py
from __future__ import annotations

from harness.core.config import ConvergenceConfig
from harness.llm.schemas import FeedbackResult


class Convergence:
    def __init__(self, config: ConvergenceConfig):
        self.max_iterations = config.max_iterations
        self.stagnation_limit = config.stagnation_limit
        self.no_edit_limit = config.no_edit_limit
        self.stagnation_count = 0
        self.no_edit_count = 0
        self.prev_error_count: int | None = None
        self.stop_reason: str | None = None

    def update(self, feedback: FeedbackResult, had_edit: bool):
        curr = len(feedback.errors) if not feedback.success else 0

        if self.prev_error_count is not None:
            if curr < self.prev_error_count:
                self.stagnation_count = 0
            else:
                self.stagnation_count += 1
        self.prev_error_count = curr

        if had_edit:
            self.no_edit_count = 0
        else:
            self.no_edit_count += 1

    def should_stop(self, attempt: int) -> bool:
        if attempt >= self.max_iterations:
            self.stop_reason = "max_iterations_reached"
            return True
        if self.stagnation_count >= self.stagnation_limit:
            self.stop_reason = "stagnation"
            return True
        if self.no_edit_count >= self.no_edit_limit:
            self.stop_reason = "no_edits"
            return True
        return False
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_convergence.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add harness/feedback/convergence.py tests/test_convergence.py
git commit -m "feat: add convergence (stagnation, no_edits, max_iterations)"
```

---

## Task 15: LLM Client Protocol

**Files:**
- Create: `harness/llm/client.py`
- Test: `tests/test_loop.py` (mock LLM used in loop tests)

**Interfaces:**
- Consumes: `LLMResponse`, `ToolCall` from schemas
- Produces: `LLMClient` protocol, `MockLLM` — used by `Agent` in loop.py; `MockLLM` used in all tests

- [ ] **Step 1: Implement LLM client protocol and MockLLM**

```python
# harness/llm/client.py
from __future__ import annotations

from typing import Protocol

from harness.llm.schemas import LLMResponse


class LLMClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        ...


class MockLLM:
    def __init__(self, responses: list[LLMResponse]):
        self.responses = list(responses)
        self.call_count = 0
        self.last_messages: list[dict] = []

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        self.last_messages = messages
        self.call_count += 1
        if self.responses:
            return self.responses.pop(0)
        return LLMResponse(type="parse_error", error="no more mock responses")
```

- [ ] **Step 2: Quick smoke test**

Run: `python -c "from harness.llm.client import MockLLM; from harness.llm.schemas import LLMResponse; m = MockLLM([LLMResponse(type='fix_complete', reasoning='done')]); r = m.complete([]); print(r.type); assert r.type == 'fix_complete'; print('OK')"`
Expected: `fix_complete\nOK`

- [ ] **Step 3: Commit**

```bash
git add harness/llm/client.py
git commit -m "feat: add LLMClient protocol and MockLLM"
```

---

## Task 16: Agent Main Loop

**Files:**
- Create: `harness/core/loop.py`
- Test: `tests/test_loop.py`

**Interfaces:**
- Consumes: `LLMClient`, `MockLLM` from client.py; all schemas; `Dispatcher` from tools; `PreActionGuard`, `PostActionGuard` from guardrails; `Memory` from memory; `FeedbackPipeline` from feedback; `Convergence` from convergence; `HarnessConfig` from config
- Produces: `Agent` class — the main entry point for running bug fixes

This is the integration task that ties everything together.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_loop.py
import pytest
from pathlib import Path

from harness.core.config import HarnessConfig, GuardrailsConfig, ConvergenceConfig
from harness.core.memory import Memory
from harness.feedback.convergence import Convergence
from harness.feedback.pipeline import FeedbackPipeline
from harness.guardrails.hitl import AutoApproveHitl
from harness.guardrails.pre_action import PreActionGuard
from harness.guardrails.post_action import PostActionGuard
from harness.llm.client import MockLLM
from harness.llm.schemas import (
    LLMResponse, ToolCall, ToolResult, FeedbackResult,
)
from harness.tools.dispatcher import Dispatcher
from harness.tools.base import Tool


class MockTool(Tool):
    name = "mock_tool"
    description = "mock"
    schema = {}
    def execute(self, **kwargs):
        return ToolResult(success=True, data=kwargs.get("result", "ok"))


@pytest.fixture
def sandbox(tmp_path):
    return tmp_path


@pytest.fixture
def config():
    return HarnessConfig(
        max_iterations=5,
        build_cmd="make",
        test_cmd="pytest",
        max_feedback_lines=50,
        guardrails=GuardrailsConfig(),
        convergence=ConvergenceConfig(max_iterations=5, stagnation_limit=3, no_edit_limit=3),
    )


@pytest.fixture
def make_agent(sandbox, config):
    def _make(responses, feedback_results=None):
        llm = MockLLM(responses)
        dispatcher = Dispatcher(sandbox_path=sandbox)
        dispatcher.register(MockTool(sandbox_path=sandbox))
        hitl = AutoApproveHitl()
        pre_guard = PreActionGuard(rules=config.guardrails, hitl=hitl)
        post_guard = PostActionGuard(rules=config.guardrails)
        memory = Memory()

        mock_pipeline = MockPipeline(feedback_results or [])
        convergence = Convergence(config=config.convergence)

        from harness.core.loop import Agent
        return Agent(
            llm=llm,
            dispatcher=dispatcher,
            pre_guard=pre_guard,
            post_guard=post_guard,
            memory=memory,
            pipeline=mock_pipeline,
            convergence=convergence,
            config=config,
        ), llm
    return _make


class MockPipeline:
    def __init__(self, results):
        self.results = list(results)
    def run(self):
        if self.results:
            return self.results.pop(0)
        return FeedbackResult(stage="test", success=True)


class TestAgentFixComplete:
    def test_fix_complete_returns_success(self, make_agent):
        resp = LLMResponse(type="fix_complete", reasoning="bug fixed")
        agent, llm = make_agent([resp])
        result = agent.run("fix the bug")
        assert result.success is True
        assert result.iterations == 1
        assert llm.call_count == 1


class TestAgentWithToolCalls:
    def test_tool_calls_then_fix(self, make_agent):
        tc = ToolCall(name="mock_tool", args={"result": "done"})
        resp1 = LLMResponse(type="tool_use", tool_calls=[tc])
        resp2 = LLMResponse(type="fix_complete")
        agent, _ = make_agent([resp1, resp2], [
            FeedbackResult(stage="build", success=False, errors=["err1"]),
        ])
        result = agent.run("fix the bug")
        assert result.success is True


class TestAgentConvergence:
    def test_max_iterations_stop(self, make_agent):
        responses = [LLMResponse(type="tool_use", tool_calls=[ToolCall(name="mock_tool", args={})]) for _ in range(10)]
        agent, _ = make_agent(responses, [
            FeedbackResult(stage="build", success=False, errors=["e"]) for _ in range(10)
        ])
        result = agent.run("impossible bug")
        assert result.success is False
        assert "max_iterations_reached" in result.reason

    def test_stagnation_stop(self, make_agent):
        responses = [LLMResponse(type="tool_use", tool_calls=[ToolCall(name="mock_tool", args={})]) for _ in range(10)]
        agent, _ = make_agent(responses, [
            FeedbackResult(stage="build", success=False, errors=["err"] * 5) for _ in range(10)
        ])
        result = agent.run("stuck bug")
        assert result.success is False


class TestAgentGuardrails:
    def test_rejected_tool_recorded_in_memory(self, sandbox, config):
        config.guardrails.blacklist = [".env"]
        llm = MockLLM([
            LLMResponse(type="tool_use", tool_calls=[ToolCall(name="read_file", args={"path": ".env"})]),
            LLMResponse(type="fix_complete"),
        ])
        dispatcher = Dispatcher(sandbox_path=sandbox)
        hitl = AutoApproveHitl()
        pre_guard = PreActionGuard(rules=config.guardrails, hitl=hitl)
        post_guard = PostActionGuard(rules=config.guardrails)
        memory = Memory()
        convergence = Convergence(config=config.convergence)
        mock_pipeline = MockPipeline([FeedbackResult(stage="test", success=True)])

        from harness.core.loop import Agent
        agent = Agent(
            llm=llm, dispatcher=dispatcher,
            pre_guard=pre_guard, post_guard=post_guard,
            memory=memory, pipeline=mock_pipeline,
            convergence=convergence, config=config,
        )
        result = agent.run("fix bug")
        assert len(memory.history) == 1
        assert memory.history[0].type == "rejected"


class TestAgentParseError:
    def test_parse_error_skips_iteration(self, make_agent):
        responses = [
            LLMResponse(type="parse_error", error="bad JSON"),
            LLMResponse(type="fix_complete"),
        ]
        agent, llm = make_agent(responses)
        result = agent.run("fix bug")
        assert result.success is True
        assert llm.call_count == 2
```

- [ ] **Step 2: Implement Agent loop**

```python
# harness/core/loop.py
from __future__ import annotations

from harness.core.config import HarnessConfig
from harness.core.memory import Memory
from harness.feedback.convergence import Convergence
from harness.feedback.pipeline import FeedbackPipeline
from harness.guardrails.pre_action import PreActionGuard
from harness.guardrails.post_action import PostActionGuard
from harness.llm.schemas import FixResult, ToolResult
from harness.tools.dispatcher import Dispatcher


class Agent:
    def __init__(self, llm, dispatcher, pre_guard, post_guard, memory, pipeline, convergence, config):
        self.llm = llm
        self.dispatcher = dispatcher
        self.pre_guard = pre_guard
        self.post_guard = post_guard
        self.memory = memory
        self.pipeline = pipeline
        self.convergence = convergence
        self.config = config

    def run(self, bug_report: str, web_notifier=None) -> FixResult:
        feedback_context = ""
        for attempt in range(self.config.max_iterations):
            prompt = self._build_prompt(bug_report, feedback_context)
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.complete(messages, tools=self.dispatcher.get_tools_schema())

            if response.type == "parse_error":
                if web_notifier:
                    web_notifier.send_event({"type": "parse_error", "error": response.error})
                continue

            if response.type == "fix_complete":
                diff = self.memory.get_diff_from_history()
                if web_notifier:
                    web_notifier.send_event({"type": "fix_complete"})
                return FixResult(success=True, diff=diff, iterations=attempt + 1)

            had_edit = False
            for tool_call in response.tool_calls:
                pre_result = self.pre_guard.check(tool_call)
                if not pre_result.allowed:
                    self.memory.append_rejection(tool_call, pre_result.reason)
                    if web_notifier:
                        web_notifier.send_event({"type": "tool_rejected", "tool": tool_call.name, "reason": pre_result.reason})
                    continue

                result = self.dispatcher.execute(tool_call)
                if web_notifier:
                    web_notifier.send_event({"type": "tool_executed", "tool": tool_call.name})

                if result.success and tool_call.name == "edit_file":
                    post_result = self.post_guard.check(tool_call, result)
                    if not post_result.allowed:
                        self.memory.append_violation(tool_call, result, post_result.reason)
                        if web_notifier:
                            web_notifier.send_event({"type": "tool_violated", "tool": tool_call.name, "reason": post_result.reason})
                        continue

                self.memory.append(tool_call, result)
                if tool_call.name == "edit_file" and result.success:
                    had_edit = True

            feedback = self.pipeline.run()
            if web_notifier:
                web_notifier.send_event({"type": "feedback", "stage": feedback.stage, "success": feedback.success})

            if feedback.success:
                diff = self.memory.get_diff_from_history()
                return FixResult(success=True, diff=diff, iterations=attempt + 1)

            self.convergence.update(feedback, had_edit=had_edit)
            if self.convergence.should_stop(attempt + 1):
                return FixResult(success=False, reason=self.convergence.stop_reason, iterations=attempt + 1)

            feedback_context = self._build_feedback_context(feedback, attempt + 1)

        return FixResult(success=False, reason="max_iterations_reached", iterations=self.config.max_iterations)

    def _build_prompt(self, bug_report: str, feedback_context: str) -> str:
        parts = [
            "You are a bug-fixing agent. Read the bug report and fix the code.",
            f"## Bug Report\n{bug_report}",
        ]
        history = self.memory.to_prompt_context()
        if history:
            parts.append(f"## Previous Actions\n{history}")
        if feedback_context:
            parts.append(f"## Feedback\n{feedback_context}")
        parts.append("Use tools to read, understand, and fix the code. If fixed, respond with fix_complete.")
        return "\n\n".join(parts)

    def _build_feedback_context(self, feedback, attempt: int) -> str:
        error_lines = feedback.errors[:self.config.max_feedback_lines]
        return f"Attempt {attempt}/{self.config.max_iterations} — {feedback.stage} FAILED:\n" + "\n".join(error_lines)
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_loop.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add harness/core/loop.py tests/test_loop.py
git commit -m "feat: add agent main loop (integrates all dimensions)"
```

---

## Task 17: Credentials Module

**Files:**
- Create: `harness/security/credentials.py`
- Create: `harness/security/setup.py`
- Test: `tests/test_credentials.py`

**Interfaces:**
- Consumes: nothing (standalone)
- Produces: `CredentialStore`, `first_run_setup()` — used by app startup

- [ ] **Step 1: Write failing tests**

```python
# tests/test_credentials.py
import os
import pytest
from unittest.mock import patch, MagicMock

from harness.security.credentials import CredentialStore


@pytest.fixture
def env_store(tmp_path):
    env_file = tmp_path / ".env"
    return CredentialStore(service_name="test-harness", env_file=env_file)


class TestCredentialStore:
    def test_store_and_load_from_env(self, env_store, tmp_path):
        with patch("harness.security.credentials.keyring", side_effect=Exception("no keyring")):
            env_store.store("TEST_KEY", "test_value")
            val = env_store.load("TEST_KEY")
            assert val == "test_value"

    def test_load_missing_returns_none(self, env_store):
        val = env_store.load("NONEXISTENT_KEY")
        assert val is None

    def test_delete_from_env(self, env_store):
        with patch("harness.security.credentials.keyring", side_effect=Exception("no keyring")):
            env_store.store("DEL_KEY", "value")
            env_store.delete("DEL_KEY")
            assert env_store.load("DEL_KEY") is None

    def test_status_stored(self, env_store):
        with patch("harness.security.credentials.keyring", side_effect=Exception("no keyring")):
            env_store.store("STATUS_KEY", "value")
            assert env_store.status("STATUS_KEY") == "stored"

    def test_status_not_set(self, env_store):
        assert env_store.status("MISSING") == "not_set"

    def test_env_file_not_plaintext_visible(self, env_store, tmp_path):
        import stat
        with patch("harness.security.credentials.keyring", side_effect=Exception("no keyring")):
            env_store.store("KEY", "value")
        mode = os.stat(env_store.env_file).st_mode
        assert not (mode & stat.S_IROTH)
```

- [ ] **Step 2: Implement credentials**

```python
# harness/security/credentials.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    import keyring
except ImportError:
    keyring = None

from dotenv import dotenv_values, set_key as dotenv_set_key, unset_key as dotenv_unset_key


class CredentialStore:
    def __init__(self, service_name: str = "harness-agent", env_file: Optional[Path] = None):
        self.service = service_name
        self.env_file = env_file or Path.cwd() / ".env"

    def store(self, key: str, value: str):
        if keyring:
            try:
                keyring.set_password(self.service, key, value)
                return
            except Exception:
                pass
        self.env_file.parent.mkdir(parents=True, exist_ok=True)
        self.env_file.touch(mode=0o600)
        os.chmod(self.env_file, 0o600)
        dotenv_set_key(str(self.env_file), key, value)

    def load(self, key: str) -> Optional[str]:
        if keyring:
            try:
                val = keyring.get_password(self.service, key)
                if val is not None:
                    return val
            except Exception:
                pass
        if self.env_file.exists():
            values = dotenv_values(str(self.env_file))
            return values.get(key)
        return os.getenv(key)

    def delete(self, key: str):
        if keyring:
            try:
                keyring.delete_password(self.service, key)
                return
            except Exception:
                pass
        if self.env_file.exists():
            dotenv_unset_key(str(self.env_file), key)

    def status(self, key: str) -> str:
        val = self.load(key)
        return "stored" if val is not None else "not_set"
```

- [ ] **Step 3: Implement first-run setup**

```python
# harness/security/setup.py
from __future__ import annotations

import getpass

from harness.security.credentials import CredentialStore


def first_run_setup(store: CredentialStore):
    if store.load("LLM_API_KEY"):
        return

    print("LLM_API_KEY not found. Running first-time setup.")
    key = getpass.getpass("Enter LLM API Key: ")
    if key:
        store.store("LLM_API_KEY", key)
        print("Key stored securely.")
    else:
        print("No key provided. Agent will not be able to call LLM.")
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_credentials.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add harness/security/credentials.py harness/security/setup.py tests/test_credentials.py
git commit -m "feat: add credential store (keyring + .env) with first-run setup"
```

---

## Task 18: WebUI (FastAPI + HTMX + WebSocket)

**Files:**
- Create: `harness/web/app.py`
- Create: `harness/web/api.py`
- Create: `harness/web/templates/index.html`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `Agent` loop, `BlockingHitl` for approval; all schemas
- Produces: FastAPI app, WebSocket endpoint, HITL approval flow

- [ ] **Step 1: Write failing tests**

```python
# tests/test_web.py
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, MagicMock

from harness.web.app import create_app


@pytest.fixture
def app():
    return create_app(config=None)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_index_page(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Bug Report" in resp.text or "bug" in resp.text.lower()


@pytest.mark.asyncio
async def test_status_endpoint(client):
    resp = await client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "state" in data


@pytest.mark.asyncio
async def test_run_endpoint_requires_bug_report(client):
    resp = await client.post("/api/run", json={})
    assert resp.status_code in (400, 422)
```

- [ ] **Step 2: Implement FastAPI app**

```python
# harness/web/app.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from harness.web.api import router


def create_app(config=None) -> FastAPI:
    app = FastAPI(title="Coding Agent Harness")
    app.state.config = config
    app.include_router(router)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return """<!DOCTYPE html>
<html>
<head>
    <title>Coding Agent Harness</title>
    <script src="https://unpkg.com/htmx.org@2.0"></script>
</head>
<body>
    <h1>Coding Agent Harness</h1>
    <form hx-post="/api/run" hx-target="#result">
        <textarea name="bug_report" placeholder="Describe the bug..." rows="5" cols="60"></textarea>
        <br><button type="submit">Fix Bug</button>
    </form>
    <div id="result"></div>
    <div id="hitl-modal" style="display:none;">
        <h3>Approval Required</h3>
        <p id="hitl-reason"></p>
        <button onclick="respondHitl('approve')">Approve</button>
        <button onclick="respondHitl('reject')">Reject</button>
    </div>
    <script>
    const ws = new WebSocket('ws://' + location.host + '/ws');
    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'approval_request') {
            document.getElementById('hitl-modal').style.display = 'block';
            document.getElementById('hitl-reason').textContent = data.reason;
        }
        if (data.type === 'tool_executed' || data.type === 'feedback') {
            document.getElementById('result').innerHTML += '<p>' + JSON.stringify(data) + '</p>';
        }
    };
    function respondHitl(decision) {
        ws.send(JSON.stringify({type: 'hitl_response', decision: decision}));
        document.getElementById('hitl-modal').style.display = 'none';
    }
    </script>
</body>
</html>"""

    return app
```

```python
# harness/web/api.py
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_state = {"state": "idle", "bug_report": None}
_ws_connections: list[WebSocket] = []


@router.get("/api/status")
async def status():
    return _state


@router.post("/api/run")
async def run(bug_report: dict = None):
    report = None
    if bug_report and bug_report.get("bug_report"):
        report = bug_report["bug_report"]
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="bug_report required")
    _state["state"] = "running"
    _state["bug_report"] = report
    return {"status": "started", "bug_report": report}


@router.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    _ws_connections.append(ws)
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "hitl_response":
                for conn in _ws_connections:
                    await conn.send_json({"type": "hitl_decision", "decision": data["decision"]})
    except WebSocketDisconnect:
        _ws_connections.remove(ws)


def broadcast(event: dict):
    import asyncio
    for ws in _ws_connections:
        asyncio.create_task(ws.send_json(event))
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_web.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add harness/web/app.py harness/web/api.py tests/test_web.py
git commit -m "feat: add WebUI (FastAPI + HTMX + WebSocket, 3 MVP features)"
```

---

## Task 19: Mechanism Demo Script

**Files:**
- Create: `demos/mechanism_demo.py`

**Interfaces:**
- Consumes: Agent, MockLLM, all modules
- Produces: runnable demo script showing 3 scenarios (per §A.6)

- [ ] **Step 1: Implement demo script**

```python
# demos/mechanism_demo.py
"""
Mechanism Demo — demonstrates 3 required scenarios with mock LLM:
1. Guardrail blocks a dangerous action (§A.6-①)
2. Feedback loop causes agent to change behavior (§A.6-②)
3. Convergence stops after stagnation (§A.6-③, deep dimension)

Run: python -m demos.mechanism_demo
"""
from __future__ import annotations

from pathlib import Path
import tempfile

from harness.core.config import HarnessConfig, GuardrailsConfig, ConvergenceConfig
from harness.core.memory import Memory
from harness.feedback.convergence import Convergence
from harness.feedback.pipeline import FeedbackPipeline
from harness.guardrails.hitl import AutoApproveHitl
from harness.guardrails.pre_action import PreActionGuard
from harness.guardrails.post_action import PostActionGuard
from harness.llm.client import MockLLM
from harness.llm.schemas import LLMResponse, ToolCall, ToolResult, FeedbackResult
from harness.tools.dispatcher import Dispatcher
from harness.tools.base import Tool
from harness.core.loop import Agent


class PrintTool(Tool):
    name = "edit_file"
    description = "mock edit"
    schema = {}
    def execute(self, **kwargs):
        return ToolResult(success=True, data={"diff": "-old\n+new", "path": kwargs.get("path", "test.py")})


class AutoRejectHitl:
    was_called = False
    def request_approval(self, tool_call, reason):
        self.was_called = True
        return "reject"


class FixedPipeline:
    def __init__(self, results):
        self.results = list(results)
    def run(self):
        if self.results:
            return self.results.pop(0)
        return FeedbackResult(stage="test", success=True)


def demo1_guardrail_blocks():
    print("\n" + "=" * 60)
    print("DEMO 1: Guardrail blocks dangerous action")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp)
        config = HarnessConfig(
            max_iterations=3,
            guardrails=GuardrailsConfig(
                blacklist=[".env"],
                require_approval_commands=["rm"],
            ),
            convergence=ConvergenceConfig(max_iterations=3, stagnation_limit=10, no_edit_limit=10),
        )
        hitl = AutoRejectHitl()
        pre_guard = PreActionGuard(rules=config.guardrails, hitl=hitl)
        post_guard = PostActionGuard(rules=config.guardrails)
        memory = Memory()
        llm = MockLLM([
            LLMResponse(type="tool_use", tool_calls=[
                ToolCall(name="run_command", args={"cmd": "rm -rf /"}),
                ToolCall(name="read_file", args={"path": ".env"}),
            ]),
            LLMResponse(type="fix_complete"),
        ])
        dispatcher = Dispatcher(sandbox_path=sandbox)
        convergence = Convergence(config=config.convergence)
        pipeline = FixedPipeline([FeedbackResult(stage="test", success=True)])

        agent = Agent(
            llm=llm, dispatcher=dispatcher,
            pre_guard=pre_guard, post_guard=post_guard,
            memory=memory, pipeline=pipeline,
            convergence=convergence, config=config,
        )
        result = agent.run("fix bug")

        print(f"HITL triggered: {hitl.was_called}")
        print(f"Memory entries: {len(memory.history)}")
        for e in memory.history:
            print(f"  - {e.type}: {e.tool_call.name} {e.reason or ''}")
        print(f"Result: success={result.success}, iterations={result.iterations}")
        assert hitl.was_called is True
        assert memory.history[0].type == "rejected"
        assert memory.history[0].reason == "human_rejected"
        assert memory.history[1].type == "rejected"
        assert memory.history[1].reason == "blacklisted_path"
        print("✓ DEMO 1 PASSED: Guardrails correctly blocked dangerous operations")


def demo2_feedback_loop():
    print("\n" + "=" * 60)
    print("DEMO 2: Feedback loop changes agent behavior")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp)
        config = HarnessConfig(
            max_iterations=5,
            build_cmd="make",
            test_cmd="pytest",
            guardrails=GuardrailsConfig(),
            convergence=ConvergenceConfig(max_iterations=5, stagnation_limit=10, no_edit_limit=10),
        )
        llm = MockLLM([
            LLMResponse(type="tool_use", tool_calls=[ToolCall(name="edit_file", args={"path": "main.py"})]),
            LLMResponse(type="tool_use", tool_calls=[ToolCall(name="edit_file", args={"path": "main.py"})]),
            LLMResponse(type="fix_complete"),
        ])
        dispatcher = Dispatcher(sandbox_path=sandbox)
        dispatcher.register(PrintTool(sandbox_path=sandbox))
        memory = Memory()
        hitl = AutoApproveHitl()
        pre_guard = PreActionGuard(rules=config.guardrails, hitl=hitl)
        post_guard = PostActionGuard(rules=config.guardrails)
        convergence = Convergence(config=config.convergence)

        pipeline = FixedPipeline([
            FeedbackResult(stage="build", success=False, errors=["SyntaxError: line 10"]),
            FeedbackResult(stage="build", success=False, errors=["NameError: undefined variable"]),
        ])

        agent = Agent(
            llm=llm, dispatcher=dispatcher,
            pre_guard=pre_guard, post_guard=post_guard,
            memory=memory, pipeline=pipeline,
            convergence=convergence, config=config,
        )
        result = agent.run("fix the bug")

        print(f"LLM called {llm.call_count} times")
        print(f"Last messages contained feedback: {'Feedback' in str(llm.last_messages)}")
        print(f"Result: success={result.success}")
        assert llm.call_count == 3
        assert "Feedback" in str(llm.last_messages)
        print("✓ DEMO 2 PASSED: Feedback loop injected errors into LLM prompt")


def demo3_convergence_stagnation():
    print("\n" + "=" * 60)
    print("DEMO 3: Convergence stops after stagnation (deep dimension)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp)
        config = HarnessConfig(
            max_iterations=10,
            build_cmd="make",
            test_cmd="pytest",
            guardrails=GuardrailsConfig(),
            convergence=ConvergenceConfig(max_iterations=10, stagnation_limit=3, no_edit_limit=10),
        )
        responses = [
            LLMResponse(type="tool_use", tool_calls=[ToolCall(name="edit_file", args={"path": "main.py"})])
            for _ in range(10)
        ]
        llm = MockLLM(responses)
        dispatcher = Dispatcher(sandbox_path=sandbox)
        dispatcher.register(PrintTool(sandbox_path=sandbox))
        memory = Memory()
        hitl = AutoApproveHitl()
        pre_guard = PreActionGuard(rules=config.guardrails, hitl=hitl)
        post_guard = PostActionGuard(rules=config.guardrails)
        convergence = Convergence(config=config.convergence)

        errors = [FeedbackResult(stage="build", success=False, errors=["same_error"] * 5) for _ in range(10)]
        pipeline = FixedPipeline(errors)

        agent = Agent(
            llm=llm, dispatcher=dispatcher,
            pre_guard=pre_guard, post_guard=post_guard,
            memory=memory, pipeline=pipeline,
            convergence=convergence, config=config,
        )
        result = agent.run("stuck bug")

        print(f"Result: success={result.success}, reason={result.reason}, iterations={result.iterations}")
        assert result.success is False
        assert result.reason == "stagnation"
        assert result.iterations >= 3
        print("✓ DEMO 3 PASSED: Convergence stopped after 3 stagnant rounds")


if __name__ == "__main__":
    demo1_guardrail_blocks()
    demo2_feedback_loop()
    demo3_convergence_stagnation()
    print("\n" + "=" * 60)
    print("ALL DEMOS PASSED ✓")
    print("=" * 60)
```

- [ ] **Step 2: Run demo**

Run: `python demos/mechanism_demo.py`
Expected: All 3 demos print PASSED

- [ ] **Step 3: Commit**

```bash
git add demos/mechanism_demo.py
git commit -m "feat: add mechanism demo (guardrail, feedback loop, convergence)"
```

---

## Task 20: Docker

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

**Interfaces:**
- Consumes: entire project
- Produces: runnable Docker image

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY harness/ harness/
COPY demos/ demos/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "harness.web.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create .dockerignore**

```
__pycache__
*.pyc
.env
.venv
.git
.pytest_cache
dist
*.egg-info
docs
tests
```

- [ ] **Step 3: Build image**

Run: `docker build -t harness-agent .`
Expected: SUCCESS

- [ ] **Step 4: Run smoke test**

Run: `docker run --rm -d -p 8080:8000 harness-agent && sleep 2 && curl http://localhost:8080/api/status && docker stop $(docker ps -q)`
Expected: `{"state":"idle","bug_report":null}`

- [ ] **Step 5: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: add Docker distribution"
```

---

## Task 21: CI (.gitlab-ci.yml)

**Files:**
- Create: `.gitlab-ci.yml`

**Interfaces:**
- Consumes: test suite
- Produces: CI pipeline with unit-test job

- [ ] **Step 1: Create CI config**

```yaml
stages:
  - test
  - build

unit-test:
  stage: test
  image: python:3.11-slim
  before_script:
    - pip install -e ".[dev]"
  script:
    - pytest tests/ -v
  artifacts:
    reports:
      junit: pytest-report.xml

docker-build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t harness-agent .
  only:
    - main
```

- [ ] **Step 2: Commit**

```bash
git add .gitlab-ci.yml
git commit -m "ci: add gitlab CI config (unit-test + docker-build)"
```

---

## Task 22: Final Integration Smoke Test

**Files:**
- Modify: all (run full suite)

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Run mechanism demo**

Run: `python demos/mechanism_demo.py`
Expected: ALL DEMOS PASSED

- [ ] **Step 3: Verify imports work**

Run: `python -c "from harness.core.loop import Agent; from harness.web.app import create_app; from harness.security.credentials import CredentialStore; print('All imports OK')"`
Expected: `All imports OK`

- [ ] **Step 4: Create README.md**

```markdown
# Coding Agent Harness

A self-coded Python agent harness that fixes bugs through a feedback-driven loop
with guardrails, HITL approval, memory, and configuration.

## Install

\`\`\`bash
pip install -e ".[dev]"
\`\`\`

## Run

\`\`\`bash
# Configure API key (see Security below)
uvicorn harness.web.app:create_app --factory --port 8000
\`\`\`

Open http://localhost:8000 in browser.

## Docker

\`\`\`bash
docker build -t harness-agent .
docker run -p 8000:8000 --env-file .env harness-agent
\`\`\`

## Test

\`\`\`bash
pytest tests/ -v
\`\`\`

## Mechanism Demo

\`\`\`bash
python demos/mechanism_demo.py
\`\`\`

## Security

- API key stored via OS keyring (primary) or `.env` (fallback)
- `.env` file is **plaintext** — not recommended for production
- In Docker: prefer `--env-file` over `-e` (avoids shell history)
- **Sandbox**: path restriction only, not a security boundary
- Dangerous commands (rm, del, etc.) require human approval via WebUI

## Configuration

Create `.harness.yaml` in project root. See `.harness.yaml` example for all options.

## Architecture

Sequential pipeline: LLM → tool calls → guardrails → execute → feedback → convergence → repeat.

Deep dimension: **Feedback Loop** — build→test pipeline with parser, convergence tracking (stagnation detection, no-edit detection, hard iteration limit).
```

- [ ] **Step 5: Final commit**

```bash
git add README.md
git commit -m "docs: add README with install, run, docker, security, architecture"
```

---

## Dependencies Map

```
Task 1  (Scaffolding)
Task 2  (Schemas)           → depends on Task 1
Task 3  (Config)            → depends on Task 1
Task 4  (Memory)            → depends on Task 2
Task 5  (Tool Protocol)     → depends on Task 2
Task 6  (Simple Tools)      → depends on Task 5
Task 7  (edit_file)         → depends on Task 5
Task 8  (run_command)       → depends on Task 5
Task 9  (Pre Guards)        → depends on Tasks 2, 3
Task 10 (Post Guards)       → depends on Tasks 2, 3
Task 11 (HITL)              → depends on Task 2
Task 12 (Parsers)           → independent of 2-11
Task 13 (Pipeline)          → depends on Tasks 8, 12, 3
Task 14 (Convergence)       → depends on Tasks 2, 3
Task 15 (LLM Client)        → depends on Task 2
Task 16 (Agent Loop)        → depends on ALL (5-15)
Task 17 (Credentials)       → depends on Task 1 only
Task 18 (WebUI)             → depends on Tasks 16, 11
Task 19 (Demo)              → depends on Task 16
Task 20 (Docker)            → depends on Task 18
Task 21 (CI)                → depends on Task 16
Task 22 (Smoke Test)        → depends on ALL

Parallelizable groups:
- Tasks 3, 4, 5, 11, 12, 17 can all run after Task 2
- Tasks 6, 7, 8 can run in parallel after Task 5
- Tasks 9, 10 can run in parallel after Tasks 2, 3
- Task 19, 21 after Task 16 (parallel)
```
