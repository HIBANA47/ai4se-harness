from __future__ import annotations
from pathlib import Path
from typing import Any
from harness.llm.schemas import ToolResult
from harness.tools.base import Tool

class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the contents of a file. Returns file content on success."
    schema: dict[str, Any] = {"type": "object", "properties": {"path": {"type": "string", "description": "File path relative to sandbox"}}, "required": ["path"]}

    def _resolve(self, path: str) -> Path | None:
        resolved = (self.sandbox_path / path).resolve()
        if not str(resolved).startswith(str(self.sandbox_path.resolve())):
            return None
        return resolved

    def execute(self, path: str, **kwargs) -> ToolResult:
        resolved = self._resolve(path)
        if resolved is None:
            return ToolResult(success=False, error="path_outside_sandbox")
        if not resolved.exists():
            return ToolResult(success=False, error=f"file not found: {path}")
        if not resolved.is_file():
            return ToolResult(success=False, error=f"not_a_file: {path}")
        return ToolResult(success=True, data=resolved.read_text())