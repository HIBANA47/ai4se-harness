import pytest
from harness.core.config import GuardrailsConfig
from harness.guardrails.rules import GuardrailRules
from harness.guardrails.pre_action import PreActionGuard
from harness.guardrails.post_action import PostActionGuard
from harness.llm.schemas import ToolCall, ToolResult

@pytest.fixture
def config():
    return GuardrailsConfig(blacklist=[".env", ".git", "secrets/"], max_diff_lines=100, require_approval_commands=["rm", "del", "drop", "delete"], max_command_timeout=30, max_command_memory_mb=256, hitl_timeout=120)

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
        assert "resource_limit" in result.reason.lower()

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
        result = ToolResult(success=True, data={"diff": "\n".join(["+" + ("line%d" % i) for i in range(10)])})
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