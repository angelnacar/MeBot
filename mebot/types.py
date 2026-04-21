# =============================================================================
# types.py — TypedDicts for Mebot
# =============================================================================
"""Type definitions for Mebot CV chatbot."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class ToxicityResult(TypedDict):
    """Resultado de la evaluación de toxicidad de un mensaje.

    Attributes:
        classification: Clasificación del contenido ('toxic' o 'safe').
        toxicity_score: Puntuación de toxicidad entre 0.0 y 1.0.
        reason: Explicación breve del resultado.
    """

    classification: str
    toxicity_score: float
    reason: str


class QualityResult(TypedDict):
    """Resultado de la evaluación de calidad de una respuesta.

    Attributes:
        classification: Clasificación de calidad ('good' o 'needs_improvement').
        quality_score: Puntuación de calidad entre 0.0 y 1.0.
        issues: Lista de problemas identificados.
        suggestion: Sugerencia para mejorar la respuesta.
    """

    classification: str
    quality_score: float
    issues: list[str]
    suggestion: str


class ToolCallResult(TypedDict):
    """Resultado de una llamada a herramienta del agente.

    Attributes:
        role: Rol del mensaje ('assistant').
        content: Contenido de la respuesta.
        tool_call_id: Identificador único de la llamada a herramienta.
    """

    role: str
    content: str
    tool_call_id: str


class RateLimitConfig(TypedDict):
    """Configuración de rate limiting para un modelo.

    Attributes:
        rpm: Requests per minute limit.
        rpd: Requests per day limit.
    """

    rpm: int
    rpd: int
