import os
from pathlib import Path
import pytest
from harness.llm.schemas import ToolResult

@pytest.fixture
def sandbox(tmp_path):
    (tmp_path / "main.py").write_text("def hello():\n    print('hello world')\n\ndef bye():\n    print('bye')\n")
    (tmp_path / "utils.py").write_text("def add(a, b):\n    return a + b\n")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "helper.py").write_text("def helper():\n    pass\n")
    return tmp_path

def test_read_file_success(sandbox):
    from harness.tools.read_file import ReadFileTool
    tool = ReadFileTool(sandbox_path=sandbox)
    result = tool.execute(path="main.py")
    assert result.success is True
    assert "def hello()" in result.data

def test_read_file_not_found(sandbox):
    from harness.tools.read_file import ReadFileTool
    tool = ReadFileTool(sandbox_path=sandbox)
    result = tool.execute(path="nonexistent.py")
    assert result.success is False
    assert "not found" in result.error.lower()

def test_read_file_outside_sandbox(sandbox):
    from harness.tools.read_file import ReadFileTool
    tool = ReadFileTool(sandbox_path=sandbox)
    result = tool.execute(path="../../../etc/passwd")
    assert result.success is False
    assert "sandbox" in result.error.lower()

def test_glob_finds_files(sandbox):
    from harness.tools.glob_tool import GlobTool
    tool = GlobTool(sandbox_path=sandbox)
    result = tool.execute(pattern="**/*.py")
    assert result.success is True
    files = result.data
    assert "main.py" in files
    assert "utils.py" in files
    assert "sub/helper.py" in files

def test_glob_no_matches(sandbox):
    from harness.tools.glob_tool import GlobTool
    tool = GlobTool(sandbox_path=sandbox)
    result = tool.execute(pattern="**/*.rs")
    assert result.success is True
    assert result.data == []

def test_glob_outside_sandbox(sandbox):
    from harness.tools.glob_tool import GlobTool
    tool = GlobTool(sandbox_path=sandbox)
    result = tool.execute(pattern="../../**/*.py")
    assert result.success is False
    assert "sandbox" in result.error.lower()

def test_grep_finds_pattern(sandbox):
    from harness.tools.grep_tool import GrepTool
    tool = GrepTool(sandbox_path=sandbox)
    result = tool.execute(pattern="def\\s+\\w+")
    assert result.success is True
    assert any("hello" in line for line in result.data)
    assert any("add" in line for line in result.data)

def test_grep_in_specific_file(sandbox):
    from harness.tools.grep_tool import GrepTool
    tool = GrepTool(sandbox_path=sandbox)
    result = tool.execute(pattern="def\\s+hello", path="main.py")
    assert result.success is True
    assert len(result.data) == 1
    assert "hello" in result.data[0]

def test_grep_no_matches(sandbox):
    from harness.tools.grep_tool import GrepTool
    tool = GrepTool(sandbox_path=sandbox)
    result = tool.execute(pattern="NONEXISTENT_PATTERN")
    assert result.success is True
    assert result.data == []

def test_edit_file_unique_match(sandbox):
    from harness.tools.edit_file import EditFileTool
    tool = EditFileTool(sandbox_path=sandbox)
    result = tool.execute(path="utils.py", old_string="def add(a, b):\n    return a + b", new_string="def add(a: int, b: int) -> int:\n    return a + b")
    assert result.success is True
    assert "diff" in result.data
    content = (sandbox / "utils.py").read_text()
    assert "a: int" in content

def test_edit_file_no_match(sandbox):
    from harness.tools.edit_file import EditFileTool
    tool = EditFileTool(sandbox_path=sandbox)
    result = tool.execute(path="main.py", old_string="def nonexistent():\n    pass", new_string="def replaced():\n    pass")
    assert result.success is False
    assert "no_match" in result.error

def test_edit_file_multiple_matches(sandbox):
    from harness.tools.edit_file import EditFileTool
    (sandbox / "dup.py").write_text("x = 1\nx = 1\nx = 1\n")
    tool = EditFileTool(sandbox_path=sandbox)
    result = tool.execute(path="dup.py", old_string="x = 1", new_string="x = 2")
    assert result.success is False
    assert "multiple_matches" in result.error

def test_edit_file_outside_sandbox(sandbox):
    from harness.tools.edit_file import EditFileTool
    tool = EditFileTool(sandbox_path=sandbox)
    result = tool.execute(path="../../../etc/passwd", old_string="root", new_string="nobody")
    assert result.success is False
    assert "sandbox" in result.error.lower()

def test_edit_file_produces_diff(sandbox):
    from harness.tools.edit_file import EditFileTool
    tool = EditFileTool(sandbox_path=sandbox)
    result = tool.execute(path="utils.py", old_string="def add(a, b):", new_string="def add(a: int, b: int):")
    assert result.success is True
    assert "-def add(a, b):" in result.data["diff"]
    assert "+def add(a: int, b: int):" in result.data["diff"]

def test_run_command_success(sandbox):
    from harness.tools.run_command import RunCommandTool
    tool = RunCommandTool(sandbox_path=sandbox)
    result = tool.execute(cmd="echo hello", timeout=10)
    assert result.success is True
    assert result.data["exit_code"] == 0
    assert "hello" in result.data["stdout"]

def test_run_command_failure_exit_code(sandbox):
    from harness.tools.run_command import RunCommandTool
    tool = RunCommandTool(sandbox_path=sandbox)
    result = tool.execute(cmd="false", timeout=10)
    assert result.success is True
    assert result.data["exit_code"] != 0

def test_run_command_timeout(sandbox):
    from harness.tools.run_command import RunCommandTool
    tool = RunCommandTool(sandbox_path=sandbox)
    result = tool.execute(cmd="sleep 2", timeout=1)
    assert result.success is False
    assert "timeout" in result.error.lower()

def test_run_command_captures_stderr(sandbox):
    from harness.tools.run_command import RunCommandTool
    tool = RunCommandTool(sandbox_path=sandbox)
    result = tool.execute(cmd="echo error >&2", timeout=10)
    assert result.success is True
    assert "error" in result.data["stderr"]

def test_run_command_runs_in_sandbox(sandbox):
    from harness.tools.run_command import RunCommandTool
    (sandbox / "hello.txt").write_text("hi")
    tool = RunCommandTool(sandbox_path=sandbox)
    result = tool.execute(cmd="cat hello.txt", timeout=10)
    assert result.success is True
    assert "hi" in result.data["stdout"]