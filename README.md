# Coding Agent Harness

A self-coded Python agent harness for automated bug fixing. Wraps an LLM with engineering mechanisms (guardrails, feedback loop, memory, configuration) to create a reliable coding agent.

## Install

```bash
git clone https://github.com/HIBANA47/ai4se-harness.git
cd ai4se-harness
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
source .venv/bin/activate
uvicorn harness.web.app:create_app --factory --port 8000
```

Open http://localhost:8000 in browser.

## Docker

```bash
docker build -t harness-agent .
docker run -p 8000:8000 --env-file .env harness-agent
```

## Test

```bash
pytest tests/ -v
```

## Mechanism Demo

```bash
python demos/mechanism_demo.py
```

## Security

- **API key storage**: OS keychain via `keyring` (primary), `.env` file (fallback, plaintext risk documented)
- **Docker key passing**: prefer `--env-file` over `-e` (avoids shell history)
- **Sandbox**: path restriction only — convenience boundary, not a security boundary. For production, use process-level isolation (nsjail, Docker-in-Docker)
- **Credentials**: never logged, never committed to git

## Configuration

Project-level config via `.harness.yaml` (gitignored). Example at `.harness.example.yaml` (committed).

Global config at `~/.config/harness/global.yaml` (optional).

## Architecture

Sequential pipeline: LLM → tool calls → guardrails (pre/post) → execute → feedback (build → test) → convergence → repeat.

**Six dimensions:**
1. **Agent Loop** — orchestrates the fix-attempt cycle
2. **Tool Dispatch** — registry-based dispatch for 5 tools (read_file, edit_file, run_command, grep, glob)
3. **Memory** — conversation history with JSON persistence
4. **Guardrails** — blacklist, resource limits, HITL approval, diff size, test deletion protection
5. **Feedback Loop** (deep dimension) — build→test pipeline with error parsing, convergence tracking (stagnation, no-edits, max iterations)
6. **Configuration** — global + project-level YAML override

## Directory Structure

```
harness/
├── core/          # Agent loop, config, memory
├── llm/           # LLM client protocol, schemas
├── tools/         # 5 tools (read_file, edit_file, run_command, grep, glob)
├── guardrails/    # Pre/post action guards, HITL
├── feedback/      # Pipeline, parsers, convergence
├── security/      # Credential store (keyring + .env)
└── web/           # FastAPI + HTMX WebUI
tests/             # 117 mock-LLM unit tests
demos/             # Mechanism demo script
```

## Requirements

- Python >= 3.11
- LLM API key (OpenAI-compatible, school platform)