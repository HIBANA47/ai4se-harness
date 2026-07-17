from __future__ import annotations
from pathlib import Path
from typing import Any
from harness.llm.schemas import ToolResult
from harness.tools.base import Tool

class GlobTool(Tool):
    name = "glob"
    description = "Find files matching a pattern. Returns list of relative paths."
    schema: dict[str, Any] = {"type": "object", "properties": {"pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)"}}, "required": ["pattern"]}

    def execute(self, pattern: str, **kwargs) -> ToolResult:
        sandbox_resolved = self.sandbox_path.resolve()
        if ".." in pattern:
            test_path = (sandbox_resolved / pattern).resolve()
            try:
                test_path.relative_to(sandbox_resolved)
            except ValueError:
                return ToolResult(success=False, error="path_outside_sandbox")
        matches = []
        for p in sandbox_resolved.rglob(pattern):
            if p.is_file():
                rel = p.relative_to(sandbox_resolved)
                matches.append(str(rel))
        return ToolResult(success=True, data=sorted(matches))