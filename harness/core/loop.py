from __future__ import annotations
from harness.core.config import HarnessConfig
from harness.core.memory import Memory
from harness.feedback.convergence import Convergence
from harness.feedback.pipeline import FeedbackPipeline
from harness.guardrails.pre_action import PreActionGuard
from harness.guardrails.post_action import PostActionGuard
from harness.llm.schemas import FixResult
from harness.tools.dispatcher import Dispatcher


class Agent:
    def __init__(self, llm, dispatcher, pre_guard, post_guard, memory, pipeline, convergence, config):
        self.llm = llm
        self.dispatcher = dispatcher
        self.pre_guard = pre_guard
        self.post_guard = post_guard
        self.memory = memory
        self.pipeline = pipeline
        self.convergence = convergence
        self.config = config

    def run(self, bug_report: str, web_notifier=None) -> FixResult:
        feedback_context = ""
        for attempt in range(self.config.max_iterations):
            prompt = self._build_prompt(bug_report, feedback_context)
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.complete(messages, tools=self.dispatcher.get_tools_schema())

            if response.type == "parse_error":
                if web_notifier:
                    web_notifier.send_event({"type": "parse_error", "error": response.error})
                continue

            if response.type == "fix_complete":
                diff = self.memory.get_diff_from_history()
                if web_notifier:
                    web_notifier.send_event({"type": "fix_complete"})
                return FixResult(success=True, diff=diff, iterations=attempt + 1)

            had_edit = False
            for tool_call in response.tool_calls:
                pre_result = self.pre_guard.check(tool_call)
                if not pre_result.allowed:
                    self.memory.append_rejection(tool_call, pre_result.reason)
                    if web_notifier:
                        web_notifier.send_event({"type": "tool_rejected", "tool": tool_call.name, "reason": pre_result.reason})
                    continue

                result = self.dispatcher.execute(tool_call)
                if web_notifier:
                    web_notifier.send_event({"type": "tool_executed", "tool": tool_call.name})

                if result.success and tool_call.name == "edit_file":
                    post_result = self.post_guard.check(tool_call, result)
                    if not post_result.allowed:
                        self.memory.append_violation(tool_call, result, post_result.reason)
                        if web_notifier:
                            web_notifier.send_event({"type": "tool_violated", "tool": tool_call.name, "reason": post_result.reason})
                        continue

                self.memory.append(tool_call, result)
                if tool_call.name == "edit_file" and result.success:
                    had_edit = True

            feedback = self.pipeline.run()
            if web_notifier:
                web_notifier.send_event({"type": "feedback", "stage": feedback.stage, "success": feedback.success})

            if feedback.success:
                diff = self.memory.get_diff_from_history()
                return FixResult(success=True, diff=diff, iterations=attempt + 1)

            self.convergence.update(feedback, had_edit=had_edit)
            if self.convergence.should_stop(attempt + 1):
                return FixResult(success=False, reason=self.convergence.stop_reason, iterations=attempt + 1)

            feedback_context = self._build_feedback_context(feedback, attempt + 1)

        return FixResult(success=False, reason="max_iterations_reached", iterations=self.config.max_iterations)

    def _build_prompt(self, bug_report: str, feedback_context: str) -> str:
        parts = [
            "You are a bug-fixing agent. Read the bug report and fix the code.",
            f"## Bug Report\n{bug_report}",
        ]
        history = self.memory.to_prompt_context()
        if history:
            parts.append(f"## Previous Actions\n{history}")
        if feedback_context:
            parts.append(f"## Feedback\n{feedback_context}")
        parts.append("Use tools to read, understand, and fix the code. If fixed, respond with fix_complete.")
        return "\n\n".join(parts)

    def _build_feedback_context(self, feedback, attempt: int) -> str:
        error_lines = feedback.errors[:self.config.max_feedback_lines]
        return f"Attempt {attempt}/{self.config.max_iterations} — {feedback.stage} FAILED:\n" + "\n".join(error_lines)