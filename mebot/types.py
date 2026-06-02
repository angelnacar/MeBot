# =============================================================================
# types.py — TypedDicts for Mebot
# =============================================================================
"""Type definitions for Mebot CV chatbot."""

from __future__ import annotations

from typing import TypedDict


class InputGuardResult(TypedDict):
    """Resultado combinado de evaluación de tópico y toxicidad.

    Attributes:
        topic: Clasificación de tópico ('ACCEPTABLE' o 'OFF_TOPIC').
        topic_confidence: Confianza de la clasificación entre 0.0 y 1.0.
        toxicity: Clasificación de toxicidad ('ACCEPTABLE' o 'NOT_ACCEPTABLE').
        toxicity_score: Puntuación de toxicidad entre 0.0 y 1.0.
        reason: Explicación breve del resultado.
        suggested_redirect: Mensaje de reconducción si el tópico es OFF_TOPIC.
    """

    topic: str
    topic_confidence: float
    toxicity: str
    toxicity_score: float
    reason: str
    suggested_redirect: str


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
        role: Rol del mensaje ('tool').
        content: Contenido de la respuesta.
        tool_call_id: Identificador único de la llamada a herramienta.
    """

    role: str
    content: str
    tool_call_id: str
