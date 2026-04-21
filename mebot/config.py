# =============================================================================
# config.py — Configuration constants for Mebot
# =============================================================================
"""Configuration constants and enums for Mebot CV chatbot."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .types import RateLimitConfig


# =============================================================================
# Threshold constants
# =============================================================================

TOXICITY_THRESHOLD = 0.7
QUALITY_THRESHOLD = 0.6
TOXICITY_BLOCK_MSG = (
    "Lo siento, no puedo continuar con esta conversación en estos términos. "
    "Si tienes alguna pregunta profesional, estaré encantado de ayudarte."
)

# =============================================================================
# Token limits per pipeline
# =============================================================================

_TOXICITY_MAX_TOKENS = 150
_QUALITY_MAX_TOKENS = 300
_AGENT_MAX_TOKENS = 2048


# =============================================================================
# Rate Limiting Configuration
# =============================================================================
#
# Límites gratuitos Groq (tier gratuito):
#   gpt-oss-20b  → 30 RPM / 8K RPD
#   gpt-oss-120b → 30 RPM / 8K RPD
#
# Factor de seguridad 80%: forzamos fallback antes del 429.

_SAFETY_FACTOR = 0.80

_GROQ_LIMITS: dict[str, RateLimitConfig] = {
    "openai/gpt-oss-20b": {"rpm": 30, "rpd": 8_000},
    "openai/gpt-oss-120b": {"rpm": 30, "rpd": 8_000},
}


# =============================================================================
# Model Configuration
# =============================================================================


@dataclass(frozen=True)
class ModelConfig:
    """Configuración de un modelo LLM.

    Attributes:
        provider: Nombre del proveedor ('groq', 'ollama').
        name: Nombre del modelo.
    """

    provider: str
    name: str


class Role(Enum):
    """Roles disponibles para los modelos LLM en el pipeline.

    Cada rol utiliza modelos específicos y tiene configuraciones
    de rate limiting independientes.

    Attributes:
        TOXICITY: Evaluación de toxicidad del mensaje de entrada.
        EVALUATOR: Evaluación de calidad de la respuesta generada.
        AGENT: Agente principal con capacidad de tool calling.
        RERUN: Regeneración de respuesta con feedback del evaluador.
    """

    TOXICITY = "toxicity"
    EVALUATOR = "evaluator"
    AGENT = "agent"
    RERUN = "rerun"


_MODEL_CONFIG: dict[Role, tuple[ModelConfig, ModelConfig]] = {
    Role.TOXICITY: (
        ModelConfig("groq", "llama-3.1-8b-instant"),
        ModelConfig("ollama", "gpt-oss:120b-cloud"),
    ),
    Role.EVALUATOR: (
        ModelConfig("groq", "llama-3.1-8b-instant"),
        ModelConfig("ollama", "gpt-oss:120b-cloud"),
    ),
    Role.AGENT: (
        ModelConfig("groq", "llama-3.1-8b-instant"),
        ModelConfig("ollama", "gpt-oss:120b-cloud"),
    ),
    Role.RERUN: (
        ModelConfig("ollama", "gpt-oss:120b-cloud"),
        ModelConfig("ollama", "gpt-oss:120b-cloud"),
    ),
}
