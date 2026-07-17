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