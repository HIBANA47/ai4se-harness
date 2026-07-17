from __future__ import annotations
from pathlib import Path
from typing import Any
from harness.llm.schemas import ToolCall, ToolResult
from harness.tools.base import Tool

class Dispatcher:
    def __init__(self, sandbox_path: str | Path):
        self.sandbox_path = Path(sandbox_path)
        self.registry: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self.registry[tool.name] = tool

    def execute(self, tool_call: ToolCall) -> ToolResult:
        tool = self.registry.get(tool_call.name)
        if not tool:
            return ToolResult(success=False, error=f"unknown_tool: {tool_call.name}")
        try:
            return tool.execute(**tool_call.args)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def get_tools_schema(self) -> list[dict[str, Any]]:
        return [{"name": t.name, "description": t.description, "schema": t.schema} for t in self.registry.values()]