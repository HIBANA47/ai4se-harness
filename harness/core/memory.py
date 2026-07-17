from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional
from harness.llm.schemas import MemoryEntry, ToolCall, ToolResult


class Memory:
    def __init__(self):
        self.history: list[MemoryEntry] = []

    def append(self, tool_call: ToolCall, result: ToolResult):
        self.history.append(MemoryEntry(type="success", tool_call=tool_call, result=result))

    def append_rejection(self, tool_call: ToolCall, reason: str):
        self.history.append(MemoryEntry(type="rejected", tool_call=tool_call, reason=reason))

    def append_violation(self, tool_call: ToolCall, result: ToolResult, reason: str):
        self.history.append(MemoryEntry(type="violation", tool_call=tool_call, result=result, reason=reason))

    def get_diff_from_history(self) -> str:
        diffs = []
        for entry in self.history:
            if entry.type == "success" and entry.tool_call.name == "edit_file" and entry.result:
                data = entry.result.data
                if isinstance(data, dict) and "diff" in data:
                    diffs.append(data["diff"])
        return "\n".join(diffs)

    def to_prompt_context(self, max_entries: int = 20) -> str:
        if not self.history:
            return ""
        recent = self.history[-max_entries:]
        lines = []
        for entry in recent:
            if entry.type == "success":
                summary = f"{entry.result.data}" if entry.result and entry.result.data else "ok"
                if isinstance(entry.result.data, dict):
                    summary = f"edited {entry.tool_call.args.get('path', '?')}"
                lines.append(f"[OK] {entry.tool_call.name}({entry.tool_call.args}) → {summary}")
            elif entry.type == "rejected":
                lines.append(f"[REJECTED] {entry.tool_call.name}({entry.tool_call.args}) reason: {entry.reason}")
            elif entry.type == "violation":
                lines.append(f"[VIOLATION] {entry.tool_call.name}({entry.tool_call.args}) reason: {entry.reason}")
        return "\n".join(lines)

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [self._entry_to_dict(e) for e in self.history]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: Path):
        if not path.exists():
            return
        with open(path) as f:
            data = json.load(f)
        self.history = [self._dict_to_entry(d) for d in data]

    @staticmethod
    def _entry_to_dict(entry: MemoryEntry) -> dict:
        return {
            "type": entry.type,
            "tool_call": {"name": entry.tool_call.name, "args": entry.tool_call.args},
            "result": asdict(entry.result) if entry.result else None,
            "reason": entry.reason,
        }

    @staticmethod
    def _dict_to_entry(d: dict) -> MemoryEntry:
        tc = ToolCall(name=d["tool_call"]["name"], args=d["tool_call"]["args"])
        tr = None
        if d.get("result") is not None:
            tr = ToolResult(**d["result"])
        return MemoryEntry(type=d["type"], tool_call=tc, result=tr, reason=d.get("reason"))