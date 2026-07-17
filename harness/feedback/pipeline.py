from __future__ import annotations
from harness.core.config import HarnessConfig
from harness.feedback.parsers import Parsers
from harness.llm.schemas import FeedbackResult

class FeedbackPipeline:
    def __init__(self, run_cmd, config: HarnessConfig):
        self.run_cmd = run_cmd
        self.config = config

    def run(self) -> FeedbackResult:
        if self.config.build_cmd:
            build_result = self.run_cmd.execute(cmd=self.config.build_cmd, timeout=self.config.build_timeout)
            if build_result.success and build_result.data and build_result.data["exit_code"] != 0:
                errors = Parsers.parse_stderr(build_result.data["stderr"], build_result.data["stdout"])
                errors = errors[:self.config.max_feedback_lines]
                return FeedbackResult(stage="build", success=False, errors=errors, raw_output=build_result.data["stderr"] + build_result.data["stdout"])
        if not self.config.test_cmd:
            return FeedbackResult(stage="test", success=True)
        test_result = self.run_cmd.execute(cmd=self.config.test_cmd, timeout=self.config.test_timeout)
        if test_result.success and test_result.data:
            if test_result.data["exit_code"] != 0:
                failures = Parsers.parse_test_output(test_result.data["stderr"], test_result.data["stdout"])
                if not failures:
                    failures = Parsers.parse_stderr(test_result.data["stderr"], test_result.data["stdout"])
                failures = failures[:self.config.max_feedback_lines]
                return FeedbackResult(stage="test", success=False, errors=failures, raw_output=test_result.data["stderr"] + test_result.data["stdout"])
        return FeedbackResult(stage="test", success=True)