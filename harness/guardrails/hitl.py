from __future__ import annotations
import threading
from abc import ABC, abstractmethod
from typing import Optional
from harness.llm.schemas import ToolCall

class HitlHandler(ABC):
    @abstractmethod
    def request_approval(self, tool_call: ToolCall, reason: str) -> str:
        ...

class AutoApproveHitl(HitlHandler):
    def request_approval(self, tool_call: ToolCall, reason: str) -> str:
        return "approve"

class BlockingHitl(HitlHandler):
    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.pending_tool_call: Optional[ToolCall] = None
        self.pending_reason: Optional[str] = None
        self._event = threading.Event()
        self._decision: Optional[str] = None
        self.on_request: Optional[callable] = None

    def request_approval(self, tool_call: ToolCall, reason: str) -> str:
        self.pending_tool_call = tool_call
        self.pending_reason = reason
        self._event.clear()
        self._decision = None
        if self.on_request:
            self.on_request(tool_call, reason)
        signalled = self._event.wait(timeout=self.timeout)
        self.pending_tool_call = None
        self.pending_reason = None
        if not signalled:
            return "timeout"
        return self._decision or "timeout"

    def respond(self, decision: str):
        self._decision = decision
        self._event.set()