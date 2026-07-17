import pytest
from harness.core.config import ConvergenceConfig
from harness.feedback.convergence import Convergence
from harness.llm.schemas import FeedbackResult

def fail(n_errors: int) -> FeedbackResult:
    return FeedbackResult(stage="build", success=False, errors=[f"err{i}" for i in range(n_errors)])

def success_result() -> FeedbackResult:
    return FeedbackResult(stage="test", success=True)

class TestMaxIterations:
    def test_within_limit(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=5, stagnation_limit=3, no_edit_limit=3))
        assert c.should_stop(attempt=1) is False
        assert c.should_stop(attempt=4) is False

    def test_at_limit(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=5, stagnation_limit=3, no_edit_limit=3))
        assert c.should_stop(attempt=5) is True
        assert c.stop_reason == "max_iterations_reached"

class TestStagnation:
    def test_stagnation_after_n_rounds(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=10, stagnation_limit=3, no_edit_limit=10))
        c.update(fail(5), had_edit=True)
        c.update(fail(5), had_edit=True)
        c.update(fail(5), had_edit=True)
        assert c.should_stop(attempt=3) is True
        assert c.stop_reason == "stagnation"

    def test_progress_resets_stagnation(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=10, stagnation_limit=3, no_edit_limit=10))
        c.update(fail(5), had_edit=True)
        c.update(fail(5), had_edit=True)
        c.update(fail(3), had_edit=True)
        assert c.should_stop(attempt=3) is False
        c.update(fail(3), had_edit=True)
        c.update(fail(3), had_edit=True)
        c.update(fail(3), had_edit=True)
        assert c.should_stop(attempt=6) is True

class TestNoEdits:
    def test_no_edit_stop(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=10, stagnation_limit=10, no_edit_limit=3))
        c.update(fail(5), had_edit=False)
        c.update(fail(5), had_edit=False)
        c.update(fail(5), had_edit=False)
        assert c.should_stop(attempt=3) is True
        assert c.stop_reason == "no_edits"

    def test_edit_resets_no_edit_count(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=10, stagnation_limit=10, no_edit_limit=3))
        c.update(fail(5), had_edit=False)
        c.update(fail(5), had_edit=False)
        c.update(fail(5), had_edit=True)
        assert c.should_stop(attempt=3) is False

class TestSuccess:
    def test_success_feedback_not_stopped(self):
        c = Convergence(config=ConvergenceConfig(max_iterations=10, stagnation_limit=3, no_edit_limit=3))
        c.update(success_result(), had_edit=True)
        assert c.should_stop(attempt=1) is False