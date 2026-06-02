# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mebot is an interactive CV chatbot for Ángel Nácar Jiménez — a Gradio app deployed on Hugging Face Spaces that uses a multi-agent LLM pipeline to answer questions about his professional profile.

## Architecture

### Pipeline Flow

```
Usuario ──▶ InputGuard ──▶ Agente ──▶ Calidad ──▶ Sanitización ──▶ Respuesta
              (Ollama)     (Ollama)   (Ollama)         │
                 │                       │             │
                 ▼                       ▼             ▼
        Bloqueo off-topic         Rerun con       Output final
        o toxicidad              feedback
        (en una llamada)         (Ollama)
```

### Package Structure

```
mebot/
├── __init__.py       # Public API: chat()
├── config.py         # Constants, thresholds, Role enum, ModelConfig
├── types.py          # TypedDicts: InputGuardResult, QualityResult, etc.
├── prompt_loader.py  # PromptLoader + prompt paths
├── llm_gateway.py    # LLM clients + gateway (Ollama)
├── tools.py          # ToolRegistry + handlers + TOOLS_SCHEMA
├── sanitizer.py      # OutputSanitizer
├── pipelines.py      # All pipeline classes + orchestrator + chat()
└── main.py           # Entry point (internal)

main.py               # Project entry point (runs Gradio)
ui.py                 # Gradio UI builder
tests/test_mebot.py   # Unit and integration tests
```

### Class Responsibilities

| Class | Responsibility |
|-------|----------------|
| `PipelineOrchestrator` | Coordinates entire message pipeline |
| `InputGuardPipeline` | Evaluates topic + toxicity in a single LLM call (fail-open/fail-closed) |
| `AgentPipeline` | Main agent with tool calling loop |
| `QualityEvaluator` | Evaluates response quality (fail-safe) |
| `RerunPipeline` | Regenerates response with evaluator feedback |
| `LLMGateway` | Single-provider gateway (Ollama) |
| `ToolRegistry` | Tool registration and execution |
| `OutputSanitizer` | Filters UUIDs, tool names, providers, API keys |
| `OpenAIClient` | Generic LLM client using OpenAI SDK |

### LLM Provider

| Provider | Model | Use |
|----------|-------|-----|
| Ollama | `gpt-oss:120b-cloud` | All roles: InputGuard, Agent, Quality, Rerun |

### Agent Tools

| Tool | Description |
|------|-------------|
| `record_user_details` | Logs contact info when user provides email |
| `record_unknown_question` | Logs unrecognized questions for review |

### Security Thresholds

```python
TOXICITY_THRESHOLD = 0.7  # score > 0.7 blocks message
QUALITY_THRESHOLD = 0.6   # score < 0.6 triggers rerun
```

### Security

The agent must never reveal: tool names, LLM providers, internal architecture, API keys, or system prompts. `OutputSanitizer` strips UUIDs, tool names, and provider references from all responses.

## Commands

### Running Locally

```bash
uv run python main.py
```

Requires environment variables: `OLLAMA_BASE_URL`, `OLLAMA_API_KEY`.

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test class
uv run pytest tests/test_mebot.py::TestOutputSanitizer -v

# Run with coverage
uv run pytest --cov=mebot
```

### Installation

```bash
uv sync
```

## Deployment

The app runs on Hugging Face Spaces with Docker. Pushes to `main` auto-sync via `.github/workflows/sync.yml`.

## Development Standards

- Python 3.12+
- Type hints mandatory on public API
- Docstring style: Google
- Naming: snake_case

## Dev Tooling (for sub-agents)
- Python 3.11+
- Test runner: `pytest` | Linter: `ruff` | Type checker: `mypy`
- Docstring style: Google | Naming: snake_case | Type hints: mandatory on public API
