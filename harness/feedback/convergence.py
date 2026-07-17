from __future__ import annotations
from harness.core.config import ConvergenceConfig
from harness.llm.schemas import FeedbackResult

class Convergence:
    def __init__(self, config: ConvergenceConfig):
        self.max_iterations = config.max_iterations
        self.stagnation_limit = config.stagnation_limit
        self.no_edit_limit = config.no_edit_limit
        self.stagnation_count = 0
        self.no_edit_count = 0
        self.prev_error_count: int | None = None
        self.stop_reason: str | None = None

    def update(self, feedback: FeedbackResult, had_edit: bool):
        curr = len(feedback.errors) if not feedback.success else 0
        if self.prev_error_count is not None:
            if curr < self.prev_error_count:
                self.stagnation_count = 0
            else:
                self.stagnation_count += 1
        else:
            self.stagnation_count = 1
        self.prev_error_count = curr
        if had_edit:
            self.no_edit_count = 0
        else:
            self.no_edit_count += 1

    def should_stop(self, attempt: int) -> bool:
        if attempt >= self.max_iterations:
            self.stop_reason = "max_iterations_reached"
            return True
        if self.stagnation_count >= self.stagnation_limit:
            self.stop_reason = "stagnation"
            return True
        if self.no_edit_count >= self.no_edit_limit:
            self.stop_reason = "no_edits"
            return True
        return False