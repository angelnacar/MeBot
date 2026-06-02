# =============================================================================
# config.py — Configuration constants for Mebot
# =============================================================================
"""Configuration constants and enums for Mebot CV chatbot."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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

_INPUT_GUARD_MAX_TOKENS = 400
_QUALITY_MAX_TOKENS = 300
_AGENT_MAX_TOKENS = 2048


# =============================================================================
# Model Configuration
# =============================================================================


@dataclass(frozen=True)
class ModelConfig:
    """Configuración de un modelo LLM.

    Attributes:
        provider: Nombre del proveedor ('ollama').
        name: Nombre del modelo.
    """

    provider: str
    name: str


class Role(Enum):
    """Roles disponibles para los modelos LLM en el pipeline.

    Attributes:
        INPUT_GUARD: Evaluación combinada de tópico y toxicidad.
        EVALUATOR: Evaluación de calidad de la respuesta generada.
        AGENT: Agente principal con capacidad de tool calling.
        RERUN: Regeneración de respuesta con feedback del evaluador.
    """

    INPUT_GUARD = "input_guard"
    EVALUATOR = "evaluator"
    AGENT = "agent"
    RERUN = "rerun"


_AGENT_MODEL = "deepseek-v4-pro:cloud"
_SUPPORT_MODEL = "minimax-m3:cloud"

_MODEL_CONFIG: dict[Role, ModelConfig] = {
    Role.INPUT_GUARD: ModelConfig("ollama", _SUPPORT_MODEL),
    Role.EVALUATOR: ModelConfig("ollama", _SUPPORT_MODEL),
    Role.AGENT: ModelConfig("ollama", _AGENT_MODEL),
    Role.RERUN: ModelConfig("ollama", _SUPPORT_MODEL),
}
