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
                return GuardResult(allowed=False, reason="diff_too_large: %d lines > %d" % (len(diff_lines), self.config.max_diff_lines))
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