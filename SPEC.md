# Coding Agent Harness — Design Specification

**Date:** 2026-07-16  
**Project:** AI4SE Final Project A  
**Author:** hibana  
**Status:** Draft for Review

---

## 1. Problem Statement

### What Problem Are We Solving?

LLMs can generate code, but they cannot reliably fix bugs in real codebases. A bare LLM has no memory of what it tried, no way to verify its changes, no guardrails against destructive actions, and no mechanism to learn from failures.

A **Coding Agent Harness** wraps an LLM with engineering mechanisms that transform it from a stateless code generator into a reliable software development agent.

### Why Is This Worth Building?

When LLMs can do most of the coding work, the engineer's value shifts to the **harness layer**: governance, feedback, context management, safety, and distribution. This project provides first-hand understanding of what makes an agentic system production-ready rather than just a demo.

### Target Users

- **Developers** who want automated bug fixing for projects in any language
- **Educators** who need a teaching tool to demonstrate agentic SE concepts

---

## 2. User Stories

1. **As a developer**, I want to submit a bug description and have the agent automatically attempt to fix it in any language project, so I save time on routine bug fixes.

2. **As a developer**, I want the agent to verify its fixes by running tests, so I don't have to manually test every attempt.

3. **As a developer**, I want the agent to stop trying after a configurable number of failed attempts, so it doesn't waste resources on unsolvable bugs.

4. **As a team lead**, I want the agent to require approval before executing dangerous commands (like deleting files), so we maintain security control.

5. **As a developer**, I want the agent to remember what it tried in previous iterations, so it doesn't repeat failed strategies.

6. **As a project manager**, I want to configure agent behavior via a YAML file, so I can customize it per project without modifying code.

7. **As a security-conscious developer**, I want my API keys stored securely using OS keychain, so they don't leak into git history or logs.

8. **As a developer**, I want to see the agent's tool calls and test results in real-time via a web UI, so I can monitor progress without polling.

9. **As a team lead**, I want to approve or reject dangerous operations (e.g. file deletion) via a web UI popup, so I maintain human oversight.

---

## 3. Functional Specification

### 3.1 Agent Core Loop (`harness/core/loop.py`)

**Input:** Bug description (string)  
**Behavior:**  
- Orchestrates the fix attempt loop (max iterations configurable)
- Each iteration: call LLM → execute tool calls → run feedback pipeline → check convergence (progress, edit activity)
- Supports real-time monitoring via WebUI WebSocket
- Returns structured `FixResult` (success/failure, diff, iteration count, reason)

**Output:** `FixResult` dataclass  
**Boundary Conditions:**  
- LLM returns `type="parse_error"` → skip iteration, log error, continue
- `type="tool_use"` with empty `tool_calls` → skip iteration, record as no-op
- LLM returns `type="fix_complete"` → exit early with success
- Max iterations exceeded → exit with `max_iterations_reached`

**Error Handling:**  
- Tool execution exceptions → catch, log, continue iteration
- LLM call failures (network, auth) → propagate to caller with clear error

---

### 3.2 Tool Dispatch (`harness/tools/dispatcher.py`)

**Input:** `ToolCall` (tool name + arguments)  
**Behavior:**  
- Registry-based dispatch (no if-else chains)
- Validates tool exists before execution
- Catches and wraps tool exceptions as `ToolResult(success=False, error=...)`

**Output:** `ToolResult` (success flag, result data, error string)  
**Available Tools:**
- `read_file(path)` — read file content, restricted to sandbox
- `edit_file(path, old_string, new_string)` — exact string replacement
- `run_command(cmd, timeout?)` — execute shell command with timeout
- `grep(pattern, path?)` — regex content search
- `glob(pattern, path?)` — filename pattern matching

**Boundary Conditions:**  
- Unknown tool → `ToolResult(success=False, error="unknown_tool")`
- Path outside sandbox → `ToolResult(success=False, error="path_outside_sandbox")`
- `edit_file` with 0 matches of `old_string` → `ToolResult(success=False, error="no_match")`
- `edit_file` with multiple matches of `old_string` → `ToolResult(success=False, error="multiple_matches")` (require more context)
- `edit_file` with exactly 1 match → execute replacement

**Error Handling:** All exceptions caught and returned as structured error

---

### 3.3 Memory (`harness/core/memory.py`)

**Input:** `ToolCall` + `ToolResult` or rejection/violation events  
**Behavior:**  
- Stores chronological history of all tool executions
- Tracks rejected operations (pre-action guards) separately
- Tracks post-action violations separately
- Generates diff from `edit_file` history
- Summarizes recent history for LLM prompt (last 20 entries)

**Output:** Structured history, diff extraction, prompt-ready context  
**Storage:**  
- During session: in-memory list
- At session end: persisted to `~/.cache/harness/memory.json` (cross-session retrieval)
- At session start: load previous history if exists for same sandbox

---

### 3.4 Guardrails (`harness/guardrails/`)

**Pre-Action Guards:**
- **Blacklist:** Reject operations on paths matching `.env`, `.git`, `secrets/`, etc.
- **Resource Limits:** Reject `run_command` exceeding timeout or memory limits
- **HITL:** Pause and wait for human approval on dangerous commands (`rm`, `del`, `drop`, `delete`)

**Post-Action Guards:**
- **Diff Size:** Reject edits producing > `max_diff_lines` lines
- **Test Deletion:** Reject edits that delete test files or test functions

**Behavior:**
- Each guard is a pure function: `(tool_call, result?) → GuardResult`
- Guards are chainable and configurable via YAML
- HITL uses synchronous blocking — agent waits for WebUI user response
- HITL timeout: if no response within `hitl_timeout` seconds (default 300), auto-reject and continue

**Output:** `GuardResult(allowed: bool, reason: str)`

---

### 3.5 Feedback Pipeline (`harness/feedback/pipeline.py`)

**Input:** None (uses current sandbox state)  
**Behavior:**  
1. **Build Stage:** Run `build_cmd` from config, parse stderr/stdout for errors
2. **Test Stage (only if build passes):** Run `test_cmd`, parse test failures
3. Return `FeedbackResult(stage, success, errors, raw_output)`

**Output:** `FeedbackResult` with structured errors and raw output  
**Boundary Conditions:**  
- Build fails → skip test stage, return build errors
- Test command not configured → skip test stage
- Error output too long → truncate to `max_feedback_lines` (default 50, configurable in `.harness.yaml`)

---

### 3.6 Convergence (`harness/feedback/convergence.py`)

**Input:** `FeedbackResult` + whether this round had a valid `edit_file` call  
**Behavior:**  
- Tracks error count changes across iterations
- Detects stagnation (no progress for N consecutive rounds)
- Detects unproductive rounds (no valid `edit_file` calls for N consecutive rounds)
- Hard stop at `max_iterations`

**Decision Logic:**
```
Continue if:
  - attempt < max_iterations
  - stagnation_count < stagnation_limit
  - no_edit_count < no_edit_limit

Stop reasons:
  - max_iterations_reached
  - stagnation
  - no_edits
```

---

### 3.7 Configuration (`harness/core/config.py`)

**Loading Order:**
1. Global config: `~/.config/harness/global.yaml` (optional)
2. Project config: `./.harness.yaml` (optional, overrides global)

**Configurable Fields:**
- `max_iterations`
- `build_cmd`, `test_cmd`
- `build_timeout`, `test_timeout`
- `allowed_tools` (whitelist)
- `guardrails` (blacklist, limits, approval commands, hitl_timeout)
- `convergence` (stagnation_limit, no_edit_limit)
- `llm` (provider, model, base_url)
- `max_feedback_lines` (default 50)

---

### 3.8 Security & Credentials (`harness/security/`)

**Storage:**
- Primary: OS keychain via `keyring` library
- Fallback: `.env` file (with documented plaintext risk)

**Operations:**
- `store(key, value)` — save securely
- `load(key)` — retrieve (keyring → .env fallback)
- `delete(key)` — remove
- `status(key)` — check if set (no plaintext echo)

**First-Run Setup:**
- Detect missing credentials
- Prompt user via `getpass()` (hidden input)
- Store in keychain

**Required Keys:** `LLM_API_KEY`, optionally `LLM_BASE_URL`

---

### 3.9 WebUI (`harness/web/`)

**Tech Stack:** FastAPI + HTMX (no JS build step)

**MVP Features (3 only):**
- **Bug Report Form:** Submit bug description to trigger agent
- **Real-Time Log:** WebSocket stream of tool calls, results, feedback
- **HITL Modal:** Popup when agent requests dangerous action, approve/reject buttons

**Deferred:** Final diff display (can be added post-MVP if time permits)

**API Endpoints:**
- `POST /api/run` — start agent with bug report
- `GET /api/status` — current agent state
- `WEBSOCKET /ws` — bidirectional real-time communication

---

## 4. Non-Functional Requirements

### 4.1 Performance
- Agent loop should complete within 5 minutes for typical bugs
- Tool executions respect configured timeouts
- WebSocket updates deliver within 100ms

### 4.2 Security
- API keys never logged or shown in WebUI
- Sandbox restricts file access to project directory
- Shell commands run with resource limits (timeout, memory)
- No credentials in git history

**Threat Model:**
| Threat | Mitigation |
|--------|-----------|
| API key in git | `.env` gitignored, keyring preferred |
| Malicious shell command | Resource limits + HITL for dangerous ops |
| File access abuse | Sandbox path validation |
| Credential leak in logs | Structured logging sanitizes secrets |

### 4.3 Usability
- WebUI responsive, no page reloads
- Clear error messages for all failure modes
- First-run setup guides key configuration

### 4.4 Observability
- All tool calls logged with timestamps
- Feedback pipeline results logged
- Convergence decisions logged (why continue/stop)

---

## 5. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        WebUI (FastAPI)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Bug Form     │  │ Real-Time Log│  │ HITL Modal        │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ WebSocket
┌─────────────────────────────────────────────────────────────┐
│                      Agent Core (loop.py)                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  while attempt < max_iterations:                       │ │
│  │    prompt = build_prompt(report, memory, feedback)     │ │
│  │    response = llm.complete(prompt)                     │ │
│  │    for tool_call in response.tool_calls:               │ │
│  │      pre_guard.check(tool_call)  ← HITL may pause     │ │
│  │      result = dispatcher.execute(tool_call)            │ │
│  │      post_guard.check(tool_call, result)               │ │
│  │      memory.append(...)                                │ │
│  │    feedback = pipeline.run()                           │ │
│  │    convergence.update(feedback, had_edit)              │ │
│  │    if should_stop(): break                             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. User submits bug via WebUI
2. Agent loop starts, streams progress via WebSocket
3. LLM generates tool calls → dispatcher executes → memory records
4. Guardrails intercept unsafe operations (HITL pops up in WebUI)
5. Feedback pipeline runs build/test, returns errors
6. Convergence decides continue or stop
7. Final result (success diff or failure reason) sent to WebUI

---

## 6. Data Model

### Core Entities

```python
@dataclass
class ToolCall:
    name: str
    args: dict

@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None

@dataclass
class LLMResponse:
    type: Literal["tool_use", "fix_complete", "parse_error"]
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning: str = ""
    error: Optional[str] = None  # populated when type="parse_error"

@dataclass
class MemoryEntry:
    type: Literal["success", "rejected", "violation"]
    tool_call: ToolCall
    result: Optional[ToolResult] = None
    reason: Optional[str] = None

@dataclass
class FeedbackResult:
    stage: Literal["build", "test"]
    success: bool
    errors: list[str] = field(default_factory=list)
    raw_output: str = ""

@dataclass
class FixResult:
    success: bool
    diff: Optional[str] = None
    reason: Optional[str] = None
    iterations: int = 0

@dataclass
class GuardResult:
    allowed: bool
    reason: str = ""
```

---

## 7. Credentials & Distribution

### Credentials Design

**Storage Strategy:**
- **Primary:** `keyring` library → OS keychain (macOS Keychain / Windows Credential Manager / Linux Secret Service)
- **Fallback:** `.env` file with `python-dotenv` (documented as plaintext risk)

**First-Run Flow:**
```
1. Load credentials
2. If LLM_API_KEY missing:
   - Prompt: "Enter LLM API Key: " (hidden via getpass)
   - Store in keyring
   - Print: "Key stored securely in OS keychain"
3. If keyring unavailable:
   - Warn: "Keyring unavailable, using .env (plaintext risk)"
   - Write to .env (chmod 600)
```

**Operations:**
- View status: `harness config status` → "LLM_API_KEY: stored"
- Update: `harness config set LLM_API_KEY` → prompt new value
- Delete: `harness config delete LLM_API_KEY` → remove from keychain

### Distribution

**Primary: Docker**

`Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install .
COPY harness/ harness/
COPY templates/ templates/
EXPOSE 8000
CMD ["uvicorn", "harness.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Run Commands:**
```bash
# Build
docker build -t harness-agent .

# Run (preferred: --env-file, not in shell history)
docker run -p 8000:8000 --env-file .env harness-agent

# Or via volume mount (most secure)
docker run -p 8000:8000 -v /run/secrets:/run/secrets harness-agent

# Dev only: -e flag (enters shell history — NOT for production)
docker run -p 8000:8000 -e LLM_API_KEY=sk-... harness-agent
```

**Key Configuration in Docker:**
- Via `--env-file` (preferred for production, avoids shell history)
- Via volume mount to `/run/secrets/` (most secure)
- Via `-e` flag (development only — warn documented in README)

**CI/CD:**
- `.gitlab-ci.yml` with `unit-test` job
- Docker build job
- Last CI run must pass

### Cloud Deployment

**Platform:** Railway (free student tier, supports Docker deploy)

**Steps:**
1. Push Docker image to GitHub Container Registry (via CI)
2. Railway app pulls image from GHCR
3. Set `LLM_API_KEY` via Railway dashboard (environment variable, not in code)
4. Public URL auto-assigned (e.g. `https://harness-agent.railway.app`)

**Architecture:**
- Single container instance (no scaling needed for demo)
- WebSocket works over wss:// automatically
- FastAPI handles concurrent connections

**README will document:**
- Public URL
- Railway deployment dashboard link
- How to set API key via Railway env vars
- Known limits (free tier memory, cold start latency)

---

## 8. Tech Stack & Rationale

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python | Course requirement; rich ecosystem for LLM tooling |
| Web Framework | FastAPI | Async-native, WebSocket built-in, lightweight |
| Frontend | HTMX | No JS build step, progressive enhancement, Python-only stack |
| Config | PyYAML | Human-readable, hierarchical merge supported |
| Credentials | keyring + python-dotenv | OS-native security + dev fallback |
| Distribution | Docker | Single-command deployment, isolation, CI-friendly |
| Testing | pytest | De facto standard, good async support |

**LLM Provider:** OpenAI-compatible API via school platform (specific `base_url` TBD). Authentication via Bearer token (`LLM_API_KEY`). Structured output (JSON mode) preferred for tool call reliability. The `LLMClient` protocol abstracts provider details, so any OpenAI-compatible endpoint works without code changes.

---

## 9. Acceptance Criteria

Each feature is "done" when:

1. **Agent Loop:** Bug report submitted → agent attempts fixes → returns success/failure with diff/reason
2. **Tool Dispatch:** All 5 tools registered and execute correctly inside sandbox
3. **Memory:** Tool call history preserved, diff extracted, prompt context generated, cross-session JSON persistence works
4. **Guardrails:** Pre/post guards reject unsafe ops, HITL pauses and waits for user
5. **Feedback Pipeline:** Build errors parsed, test failures parsed, structured result returned
6. **Convergence:** Stagnation, no-edits, and max iterations all trigger stop correctly
7. **Configuration:** Global + project config loaded and merged correctly
8. **Credentials:** Key stored in keyring, loaded with .env fallback, never logged
9. **WebUI:** Bug form works, real-time log streams, HITL modal appears (MVP 3 features only)
10. **Docker:** `docker build` succeeds, `docker run` starts agent, API key configurable
11. **CI:** `unit-test` job passes, Docker build job succeeds, last run is green
12. **Mechanism Demo:** Three scenarios reproducible with mock LLM (guardrail block, feedback loop, convergence decision)
13. **Cloud Deployment:** App accessible via public URL with WebUI functional
14. **Reflection:** `REFLECTION.md` (1500-2500 words) written personally, not AI-generated

---

## 10. Risks & Open Questions

### Risks

1. **LLM Prompt Quality** — Agent performance heavily depends on prompt engineering. We may need significant iteration to get reliable tool calls.
   - *Mitigation:* Use structured output (JSON mode) to reduce parsing errors.

2. **Feedback Signal Noise** — Build/test errors may be verbose and hard to parse into concise feedback.
   - *Mitigation:* Generic parsers extracting key lines; limit feedback to N error lines.

3. **HITL Blocking UX** — Synchronous blocking means agent cannot do anything while waiting for user response.
   - *Mitigation:* WebUI clearly shows "waiting for approval" state; timeout after 5 minutes (configurable).

4. **Scope Creep** — Six dimensions + WebUI + credentials + CI is a lot for one semester.
   - *Mitigation:* Strict MVP mindset. Advanced features (multi-language parsing, async HITL) deferred.

5. **Sandbox Is Not Security Isolation** — The path restriction and HITL approach is a **convenience sandbox**, not a security sandbox. `run_command` can execute arbitrary shell commands, and the HITL blacklist is necessarily incomplete. A determined attacker or a sufficiently creative LLM could bypass it.
   - *Mitigation:* Document clearly in README that this is not a security boundary. For production use, a process-level sandbox (e.g. `nsjail`, Docker-in-Docker) would be needed. Deferred for MVP.

### Open Questions

1. **School LLM Platform API Format** — Exact endpoint and auth format TBD. The `LLMClient` protocol abstracts this, so we can implement once details are known.

2. **Sandbox Isolation Level** — Current design uses path restriction. Should we also use process isolation (e.g., `nsjail`)? Deferred for MVP.

3. **Memory Persistence Level** — MVP uses JSON file persistence for cross-session retrieval. Should we add indexing or selective recall (e.g. "only load history for this specific project")? Deferred — flat list is sufficient for MVP.

---

## 11. Domain & Mechanism Design (Coding Agent Harness Specific)

### 11.1 Feedback Signals (Objective, Deterministic)

| Signal | Source | How It's Engineered |
|--------|--------|---------------------|
| Build errors | `build_cmd` stderr/stdout | Parser extracts error lines, returns structured `FeedbackResult` |
| Test failures | `test_cmd` stderr/stdout | Parser matches "FAILED", "AssertionError", etc. |
| Diff size | `edit_file` result | Post-action guard counts lines, rejects if > limit |

**Parser Design:** Generic interface (match error patterns by regex/keyword rules), but MVP ships with Python-specific rules only (`pytest` output, Python traceback format). The rule set is configurable per project via `.harness.yaml`, so adding support for other languages is an extension point, not a redesign.

**Key Point:** These are **code mechanisms**, not prompt requests. A parser function extracts errors deterministically. No reliance on LLM to "check if the build succeeded."

### 11.2 Dangerous Actions (Require Human Approval)

| Action Pattern | Reason | HITL Behavior |
|----------------|--------|---------------|
| `rm -rf`, `del`, `drop`, `delete` | Destructive file/command | Pause, show details in WebUI, wait for approve/reject |
| Shell commands with `sudo`, `chmod 777` | Privilege escalation | Pause, show command, wait for approval |
| Network requests (`curl`, `wget` to external) | Data exfiltration risk | Pause, show URL, wait for approval |

**Key Point:** HITL is a **code mechanism** — `hitl.request_approval()` blocks the agent loop and waits for WebSocket response. Not a prompt saying "be careful with dangerous commands."

### 11.3 Tools Required

| Tool | Purpose | Why Necessary |
|------|---------|---------------|
| `read_file` | Read source code | Agent must understand context before fixing |
| `edit_file` | Apply fixes | The actual mechanism for code changes |
| `run_command` | Build + test + debug | Essential for feedback loop and exploration |
| `grep` | Find code patterns | Locate errors, function definitions, etc. |
| `glob` | Find files | Locate test files, configs, related modules |

### 11.4 Memory Needs

| What to Remember | Why | How |
|------------------|-----|-----|
| Tool call history | LLM needs to know what it tried | Chronological list, last 20 summarized for prompt |
| Rejected operations | Avoid repeating blocked actions | Separate list with reasons |
| Edit diffs | Show final result | Extracted from `edit_file` history |
| Cross-session history | "What did I try last time?" | Persisted to `~/.cache/harness/memory.json` at session end |

**Key Point:** Memory is **in-memory list with JSON file persistence**. No vector store or retrieval complexity for MVP — just serialize/deserialize the history list.

### 11.5 Deep Dimension: Feedback Loop

**Why Feedback Loop?**

1. **Natural fit for bug fixing** — The fix→build→test→retry cycle is the core activity
2. **Rich engineering surface** — Parsers, convergence logic, multi-stage pipeline
3. **Deterministic testability** — Mock LLM can simulate "attempt N produces X errors"
4. **Demonstrates self-correction** — The most compelling agentic behavior

**Engineering Depth:**

- **Pipeline:** Two-stage (build → test), short-circuit on build failure
- **Parsers:** Generic interface (regex/keyword rules), Python-specific rules for MVP
- **Convergence:** Three stop conditions (hard limit, stagnation, no valid edits)
- **Feedback Injection:** Structured error summary injected into next prompt

**Mock Test Coverage:**
- Pipeline short-circuits on build failure
- Convergence stops after N stagnant rounds
- Hard limit triggers at `max_iterations`
- No-edit stop triggers after N rounds without valid `edit_file`
- Progress resets stagnation counter

---

## Summary

This design delivers a **Coding Agent Harness** with:

✅ Self-coded agent loop (no framework dependency)  
✅ Six dimensions all implemented (main loop, tools, memory, guardrails, feedback, config)  
✅ Feedback loop as the deep dimension  
✅ HITL for dangerous actions  
✅ WebUI for monitoring and approval  
✅ Secure credential storage  
✅ Docker distribution  
✅ Cloud deployment (Railway, public URL)  
✅ Comprehensive mock-LLM unit tests  
✅ Mechanism demo script  
✅ REFLECTION.md (1500-2500 words, personally written)  

The harness turns an LLM into a reliable bug-fixing agent through **engineering mechanisms** (code), not **prompt requests** (hints to the LLM). Every mechanism is unit-testable with mock LLM, satisfying the course's "remove real LLM, what's left?" criterion.
