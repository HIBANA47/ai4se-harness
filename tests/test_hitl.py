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