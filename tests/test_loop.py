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


class MockEditTool(Tool):
    name = "edit_file"
    description = "edit file"
    schema = {}
    def execute(self, **kwargs):
        return ToolResult(success=True, data={"diff": "mock diff", "path": kwargs.get("path", "")})


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
            llm=llm, dispatcher=dispatcher,
            pre_guard=pre_guard, post_guard=post_guard,
            memory=memory, pipeline=mock_pipeline,
            convergence=convergence, config=config,
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
        agent, _ = make_agent([resp1, resp2], [FeedbackResult(stage="build", success=False, errors=["err1"])])
        result = agent.run("fix the bug")
        assert result.success is True


class TestAgentConvergence:
    def test_max_iterations_stop(self, sandbox, config):
        responses = [LLMResponse(type="tool_use", tool_calls=[ToolCall(name="edit_file", args={"path": "x.py", "pattern": "a", "replacement": "b"})]) for _ in range(10)]
        feedbacks = [
            FeedbackResult(stage="build", success=False, errors=["e1"]),
            FeedbackResult(stage="build", success=False, errors=["e1", "e2"]),
            FeedbackResult(stage="build", success=False, errors=["e1"]),
            FeedbackResult(stage="build", success=False, errors=["e1", "e2"]),
            FeedbackResult(stage="build", success=False, errors=["e1"]),
            FeedbackResult(stage="build", success=False, errors=["e1", "e2"]),
            FeedbackResult(stage="build", success=False, errors=["e1"]),
            FeedbackResult(stage="build", success=False, errors=["e1", "e2"]),
            FeedbackResult(stage="build", success=False, errors=["e1"]),
            FeedbackResult(stage="build", success=False, errors=["e1", "e2"]),
        ]
        llm = MockLLM(responses)
        dispatcher = Dispatcher(sandbox_path=sandbox)
        dispatcher.register(MockEditTool(sandbox_path=sandbox))
        hitl = AutoApproveHitl()
        pre_guard = PreActionGuard(rules=config.guardrails, hitl=hitl)
        post_guard = PostActionGuard(rules=config.guardrails)
        memory = Memory()
        convergence = Convergence(config=config.convergence)
        mock_pipeline = MockPipeline(feedbacks)
        from harness.core.loop import Agent
        agent = Agent(
            llm=llm, dispatcher=dispatcher,
            pre_guard=pre_guard, post_guard=post_guard,
            memory=memory, pipeline=mock_pipeline,
            convergence=convergence, config=config,
        )
        result = agent.run("impossible bug")
        assert result.success is False
        assert "max_iterations_reached" in result.reason

    def test_stagnation_stop(self, make_agent):
        responses = [LLMResponse(type="tool_use", tool_calls=[ToolCall(name="mock_tool", args={})]) for _ in range(10)]
        agent, _ = make_agent(responses, [FeedbackResult(stage="build", success=False, errors=["err"] * 5) for _ in range(10)])
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