from __future__ import annotations
from harness.core.config import GuardrailsConfig
from harness.llm.schemas import ToolCall

class GuardrailRules:
    def __init__(self, config: GuardrailsConfig):
        self.config = config

    def is_blacklisted(self, tool_call: ToolCall) -> bool:
        path = tool_call.args.get("path", "")
        for pattern in self.config.blacklist:
            if path == pattern or path.startswith(pattern):
                return True
        return False

    def exceeds_limits(self, tool_call: ToolCall) -> bool:
        if tool_call.name != "run_command":
            return False
        timeout = tool_call.args.get("timeout")
        if timeout is not None and timeout > self.config.max_command_timeout:
            return True
        return False

    def requires_approval(self, tool_call: ToolCall) -> bool:
        if tool_call.name != "run_command":
            return False
        cmd = tool_call.args.get("cmd", "")
        for dangerous in self.config.require_approval_commands:
            if dangerous in cmd.split() or cmd.strip().startswith(dangerous + " "):
                return True
        return False