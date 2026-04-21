# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mebot is an interactive CV chatbot for Ángel Nácar Jiménez — a Gradio app deployed on Hugging Face Spaces that uses a multi-agent LLM pipeline to answer questions about his professional profile.

## Architecture

### Pipeline Flow

```
Usuario ──▶ TopicGuardrail ──▶ Toxicidad ──▶ Agente ──▶ Calidad ──▶ Sanitización ──▶ Respuesta
                    │            (Groq)       (Groq)    (Groq)         │
                    │               │                       │         │
                    ▼               ▼                       ▼         │
            Reconducción     Bloqueo si           Rerun con         │
            off-topic        score > 0.7         feedback          ▼
                                                (Ollama)       Output final
```

### Package Structure

```
mebot/
├── __init__.py       # Public API: chat()
├── config.py         # Constants, thresholds, Role enum, ModelConfig
├── types.py          # TypedDicts: ToxicityResult, QualityResult, etc.
├── prompt_loader.py  # PromptLoader + prompt paths
├── llm_gateway.py    # LLM clients + gateway + RateLimitTracker
├── tools.py          # ToolRegistry + handlers + TOOLS_SCHEMA
├── sanitizer.py      # OutputSanitizer
├── pushover.py       # Pushover notifications
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
| `AgentPipeline` | Main agent with tool calling loop |
| `ToxicityPipeline` | Evaluates input toxicity (fail-open) |
| `QualityEvaluator` | Evaluates response quality (fail-safe) |
| `TopicGuardrail` | Blocks off-topic questions |
| `RerunPipeline` | Regenerates response with evaluator feedback |
| `LLMGateway` | Automatic provider selection with fallback |
| `RateLimitTracker` | Thread-safe rate limiting with 80% safety factor |
| `ToolRegistry` | Tool registration and execution |
| `OutputSanitizer` | Filters UUIDs, tool names, providers, API keys |
| `OpenAIClient` | Generic LLM client using OpenAI SDK |

### LLM Providers

| Provider | Model | Use | Rate Limit |
|----------|-------|-----|------------|
| Groq | `llama-3.1-8b-instant` | Toxicity, Quality, Agent | 80% safety factor |
| Ollama | `gpt-oss:120b-cloud` | Fallback and Rerun | — |

### Agent Tools

| Tool | Description |
|------|-------------|
| `record_user_details` | Logs contact info via Pushover when user provides email |
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

Requires environment variables: `GROQ_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_API_KEY`, `PUSHOVER_USER`, `PUSHOVER_TOKEN`.

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
