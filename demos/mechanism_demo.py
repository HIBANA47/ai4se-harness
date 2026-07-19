"""
Mechanism Demo — demonstrates 3 required scenarios with mock LLM:
1. Guardrail blocks a dangerous action (§A.6-①)
2. Feedback loop causes agent to change behavior (§A.6-②)
3. Convergence stops after stagnation (§A.6-③, deep dimension)

Run: python demos/mechanism_demo.py
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