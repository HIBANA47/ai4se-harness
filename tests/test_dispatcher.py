import pytest
from harness.llm.schemas import ToolCall, ToolResult
from harness.tools.base import Tool
from harness.tools.dispatcher import Dispatcher

class AddTool(Tool):
    name = "add"
    description = "Add two numbers"
    schema = {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}}
    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data=kwargs["a"] + kwargs["b"])

class FailTool(Tool):
    name = "fail"
    description = "Always fails"
    schema = {}
    def execute(self, **kwargs) -> ToolResult:
        raise ValueError("intentional failure")

def test_register_and_execute():
    d = Dispatcher(sandbox_path="/tmp")
    d.register(AddTool(sandbox_path="/tmp"))
    result = d.execute(ToolCall(name="add", args={"a": 2, "b": 3}))
    assert result.success is True
    assert result.data == 5

def test_unknown_tool():
    d = Dispatcher(sandbox_path="/tmp")
    result = d.execute(ToolCall(name="nonexistent", args={}))
    assert result.success is False
    assert "unknown_tool" in result.error

def test_tool_exception_caught():
    d = Dispatcher(sandbox_path="/tmp")
    d.register(FailTool(sandbox_path="/tmp"))
    result = d.execute(ToolCall(name="fail", args={}))
    assert result.success is False
    assert "intentional failure" in result.error

def test_get_tools_schema():
    d = Dispatcher(sandbox_path="/tmp")
    d.register(AddTool(sandbox_path="/tmp"))
    schemas = d.get_tools_schema()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "add"

def test_multiple_tools():
    d = Dispatcher(sandbox_path="/tmp")
    d.register(AddTool(sandbox_path="/tmp"))
    d.register(FailTool(sandbox_path="/tmp"))
    schemas = d.get_tools_schema()
    assert len(schemas) == 2