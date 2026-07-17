from __future__ import annotations
import difflib
from pathlib import Path
from typing import Any
from harness.llm.schemas import ToolResult
from harness.tools.base import Tool

class EditFileTool(Tool):
    name = "edit_file"
    description = "Replace an exact string match in a file. Fails if 0 or >1 matches."
    schema: dict[str, Any] = {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["path", "old_string", "new_string"]}

    def _resolve(self, path: str) -> Path | None:
        resolved = (self.sandbox_path / path).resolve()
        if not str(resolved).startswith(str(self.sandbox_path.resolve())):
            return None
        return resolved

    def execute(self, path: str, old_string: str, new_string: str, **kwargs) -> ToolResult:
        resolved = self._resolve(path)
        if resolved is None:
            return ToolResult(success=False, error="path_outside_sandbox")
        if not resolved.exists():
            return ToolResult(success=False, error=f"file not found: {path}")
        content = resolved.read_text()
        count = content.count(old_string)
        if count == 0:
            return ToolResult(success=False, error="no_match")
        if count > 1:
            return ToolResult(success=False, error=f"multiple_matches: found {count} occurrences")
        new_content = content.replace(old_string, new_string, 1)
        resolved.write_text(new_content)
        diff_lines = list(difflib.unified_diff(content.splitlines(keepends=True), new_content.splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{path}"))
        diff_str = "".join(diff_lines)
        return ToolResult(success=True, data={"diff": diff_str, "path": path})