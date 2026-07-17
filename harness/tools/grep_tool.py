from __future__ import annotations
import re
from pathlib import Path
from typing import Any
from harness.llm.schemas import ToolResult
from harness.tools.base import Tool

class GrepTool(Tool):
    name = "grep"
    description = "Search file contents with regex. Returns list of matching lines (with file:line prefix)."
    schema: dict[str, Any] = {"type": "object", "properties": {"pattern": {"type": "string", "description": "Regex pattern"}, "path": {"type": "string", "description": "Optional file or directory to search in"}}, "required": ["pattern"]}

    def execute(self, pattern: str, path: str = None, **kwargs) -> ToolResult:
        sandbox_resolved = self.sandbox_path.resolve()
        search_root = sandbox_resolved
        if path:
            search_root = (sandbox_resolved / path).resolve()
            if not str(search_root).startswith(str(sandbox_resolved)):
                return ToolResult(success=False, error="path_outside_sandbox")
            if not search_root.exists():
                return ToolResult(success=False, error=f"path_not_found: {path}")
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolResult(success=False, error=f"invalid_regex: {e}")
        matches = []
        if search_root.is_file():
            files = [search_root]
        else:
            files = [p for p in search_root.rglob("*") if p.is_file()]
        for fpath in sorted(files):
            try:
                lines = fpath.read_text().splitlines()
            except (UnicodeDecodeError, PermissionError):
                continue
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    rel = fpath.relative_to(sandbox_resolved)
                    matches.append(f"{rel}:{i}: {line.strip()}")
        return ToolResult(success=True, data=matches)