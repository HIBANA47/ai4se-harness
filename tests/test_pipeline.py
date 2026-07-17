import pytest
from unittest.mock import MagicMock
from harness.core.config import HarnessConfig
from harness.feedback.pipeline import FeedbackPipeline
from harness.llm.schemas import ToolResult

@pytest.fixture
def config():
    return HarnessConfig(build_cmd="make build", test_cmd="pytest", build_timeout=60, test_timeout=120, max_feedback_lines=50)

def test_build_failure_skips_test(config):
    mock_cmd = MagicMock()
    mock_cmd.execute.return_value = ToolResult(success=True, data={"exit_code": 1, "stderr": "SyntaxError: line 42", "stdout": ""})
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
    mock_cmd.execute.return_value = ToolResult(success=True, data={"exit_code": 0, "stderr": "", "stdout": "5 passed"})
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
    mock_cmd.execute.return_value = ToolResult(success=True, data={"exit_code": 1, "stderr": long_errors, "stdout": ""})
    pipeline = FeedbackPipeline(run_cmd=mock_cmd, config=config)
    result = pipeline.run()
    assert result.success is False
    assert len(result.errors) <= 3