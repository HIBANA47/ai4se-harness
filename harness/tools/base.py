from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from harness.llm.schemas import ToolResult

class Tool(ABC):
    name: str
    description: str
    schema: dict[str, Any]
    sandbox_path: Path

    def __init__(self, sandbox_path: str | Path):
        self.sandbox_path = Path(sandbox_path)

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        ...