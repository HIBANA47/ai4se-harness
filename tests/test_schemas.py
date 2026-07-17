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