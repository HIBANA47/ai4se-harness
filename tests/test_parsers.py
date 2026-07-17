import pytest
from harness.feedback.parsers import Parsers

class TestParseStderr:
    def test_python_syntax_error(self):
        stderr = '  File "main.py", line 42\n    def foo(\n            ^\nSyntaxError: unexpected EOF'
        errors = Parsers.parse_stderr(stderr, "")
        assert len(errors) > 0
        assert any("SyntaxError" in e for e in errors)

    def test_python_runtime_error(self):
        stderr = 'Traceback (most recent call last):\n  File "main.py", line 10, in <module>\n    raise ValueError("bad input")\nValueError: bad input'
        errors = Parsers.parse_stderr(stderr, "")
        assert any("ValueError" in e for e in errors)

    def test_empty_output(self):
        errors = Parsers.parse_stderr("", "")
        assert errors == []

    def test_no_errors(self):
        stderr = "Build complete.\nDone."
        errors = Parsers.parse_stderr(stderr, "")
        assert errors == []

class TestParseTestOutput:
    def test_pytest_failures(self):
        stdout = "=========================== FAILURES ===========================\n___________________________ test_add ___________________________\n\n    def test_add():\n>       assert add(1, 2) == 4\nE       assert 3 == 4\n\ntests/test_main.py:5: AssertionError\n========================= 2 failed, 1 passed =================="
        failures = Parsers.parse_test_output("", stdout)
        assert len(failures) > 0

    def test_pytest_passed(self):
        stdout = "========================= 5 passed =========================="
        failures = Parsers.parse_test_output("", stdout)
        assert failures == []

    def test_mixed_stderr_stdout(self):
        stderr = "error: something broke"
        stdout = "FAILED test_one"
        errors = Parsers.parse_stderr(stderr, stdout)
        assert len(errors) > 0