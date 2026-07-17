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
    tr1 = ToolResult(success=True, data={"diff": "--- a/a.py\n+++ b/a.py\n-old\n+new"})
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