# =============================================================================
# prompt_loader.py — Prompt loading and rendering for Mebot
# =============================================================================
"""Load and render system prompts from Jinja2 templates."""

from __future__ import annotations

from pathlib import Path

from jinja2.sandbox import SandboxedEnvironment


class PromptLoader:
    """Carga y renderiza system prompts desde archivos Jinja2.

    Usa SandboxedEnvironment para prevenir SSTI (Server-Side Template Injection).
    """

    _cache: dict[str, SandboxedEnvironment] = {}

    @classmethod
    def reset_cache(cls) -> None:
        """Resetea el cache - útil para testing."""
        cls._cache.clear()

    @classmethod
    def load(cls, path: Path) -> SandboxedEnvironment:
        key = str(path.resolve())
        if key not in cls._cache:
            env = SandboxedEnvironment()
            cls._cache[key] = env.from_string(path.read_text(encoding="utf-8"))
        return cls._cache[key]

    @classmethod
    def render(cls, path: Path, **kwargs: str) -> str:
        return cls.load(path).render(**kwargs)


# Rutas de prompts
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_PATH_MEBEST = _PROMPTS_DIR / "meBest.md"
_PATH_TOXICITY = _PROMPTS_DIR / "user_toxicity.md"
_PATH_QUALITY = _PROMPTS_DIR / "agent_quality.md"
_PATH_TOPIC_GUARDRAIL = _PROMPTS_DIR / "topic_guardrail.md"
_PATH_QUALITY_FACTS = _PROMPTS_DIR / "quality_facts.md"


# ── System prompts ─────────────────────────────────────────────────────────────


def system_prompt() -> str:
    """Returns the main system prompt for the agent."""
    return PromptLoader.render(_PATH_MEBEST)


def toxicity_prompt(message: str, history: list[dict[str, str]]) -> str:
    """Returns the toxicity evaluation prompt."""
    return PromptLoader.render(_PATH_TOXICITY, message=message, history=history)


def quality_facts_context() -> str:
    """Loads the factual context for quality evaluation."""
    return PromptLoader.render(_PATH_QUALITY_FACTS)


def quality_prompt(message: str, history: list[dict[str, str]], reply: str) -> str:
    """Returns the quality evaluation prompt."""
    return PromptLoader.render(
        _PATH_QUALITY,
        agent_context=quality_facts_context(),
        history=history,
        message=message,
        reply=reply,
    )


def topic_guardrail_prompt(message: str, history: list[dict[str, str]]) -> str:
    """Returns the topic guardrail evaluation prompt."""
    return PromptLoader.render(_PATH_TOPIC_GUARDRAIL, message=message, history=history)
