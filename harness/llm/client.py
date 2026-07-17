from __future__ import annotations
from typing import Protocol
from harness.llm.schemas import LLMResponse

class LLMClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        ...

class MockLLM:
    def __init__(self, responses: list[LLMResponse]):
        self.responses = list(responses)
        self.call_count = 0
        self.last_messages: list[dict] = []

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        self.last_messages = messages
        self.call_count += 1
        if self.responses:
            return self.responses.pop(0)
        return LLMResponse(type="parse_error", error="no more mock responses")