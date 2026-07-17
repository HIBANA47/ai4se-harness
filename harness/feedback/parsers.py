from __future__ import annotations
import re

class Parsers:
    ERROR_PATTERNS = [
        re.compile(r"^(Traceback|.*Error:|.*Exception:)", re.IGNORECASE),
        re.compile(r"^.*error.*$", re.IGNORECASE),
        re.compile(r"^.*FAILED.*$", re.IGNORECASE),
        re.compile(r"^File .* line \d+", re.IGNORECASE),
    ]

    TEST_FAILURE_PATTERNS = [
        re.compile(r"^.*FAILED.*$"),
        re.compile(r"^.*AssertionError.*$"),
        re.compile(r"^>\s+assert"),
        re.compile(r"^E\s+", re.MULTILINE),
    ]

    @staticmethod
    def parse_stderr(stderr: str, stdout: str) -> list[str]:
        combined = (stderr + "\n" + stdout).strip()
        if not combined:
            return []
        lines = combined.split("\n")
        errors = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            for pattern in Parsers.ERROR_PATTERNS:
                if pattern.search(stripped):
                    errors.append(stripped)
                    break
        return errors

    @staticmethod
    def parse_test_output(stderr: str, stdout: str) -> list[str]:
        combined = (stderr + "\n" + stdout).strip()
        if not combined:
            return []
        passed_match = re.search(r"(\d+) passed", combined)
        failed_match = re.search(r"(\d+) failed", combined)
        if failed_match and int(failed_match.group(1)) > 0:
            failures = []
            lines = combined.split("\n")
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                for pattern in Parsers.TEST_FAILURE_PATTERNS:
                    if pattern.search(stripped):
                        failures.append(stripped)
                        break
            return failures if failures else [combined[:200]]
        if passed_match and not failed_match:
            return []
        errors = Parsers.parse_stderr(stderr, stdout)
        return errors