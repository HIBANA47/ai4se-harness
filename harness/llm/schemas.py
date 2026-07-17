from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

@dataclass
class ToolCall:
    name: str
    args: dict

@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None

@dataclass
class LLMResponse:
    type: Literal["tool_use", "fix_complete", "parse_error"]
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning: str = ""
    error: Optional[str] = None

@dataclass
class MemoryEntry:
    type: Literal["success", "rejected", "violation"]
    tool_call: ToolCall
    result: Optional[ToolResult] = None
    reason: Optional[str] = None

@dataclass
class FeedbackResult:
    stage: Literal["build", "test"]
    success: bool
    errors: list[str] = field(default_factory=list)
    raw_output: str = ""

@dataclass
class FixResult:
    success: bool
    diff: Optional[str] = None
    reason: Optional[str] = None
    iterations: int = 0

@dataclass
class GuardResult:
    allowed: bool
    reason: str = ""