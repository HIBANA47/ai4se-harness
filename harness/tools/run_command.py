from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Any
from harness.llm.schemas import ToolResult
from harness.tools.base import Tool

class RunCommandTool(Tool):
    name = "run_command"
    description = "Execute a shell command in the sandbox directory. Returns exit_code, stdout, stderr."
    schema: dict[str, Any] = {"type": "object", "properties": {"cmd": {"type": "string"}, "timeout": {"type": "integer", "description": "Timeout in seconds (default 60)"}}, "required": ["cmd"]}

    def execute(self, cmd: str, timeout: int = 60, **kwargs) -> ToolResult:
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=str(self.sandbox_path))
            return ToolResult(success=True, data={"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"command_timeout_after_{timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))