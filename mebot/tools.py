# =============================================================================
# tools.py — Tool registry and handlers for Mebot
# =============================================================================
"""Tool registration, schemas, and handler functions."""

from __future__ import annotations

import json
import logging
from typing import Any

from jsonschema import ValidationError, validate

from .pushover import _pushover

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Registry
# =============================================================================


class ToolRegistry:
    """Registro de herramientas disponibles para el agente.

    Solo permite ejecutar funciones explícitamente registradas.
    """

    _ALLOWED_TOOLS: set[str] = {"record_user_details", "record_unknown_question"}

    def __init__(self) -> None:
        self._functions: dict[str, Any] = {}

    def register(self, name: str, fn: Any) -> None:
        self._functions[name] = fn

    def call(self, name: str, **kwargs: Any) -> dict[str, Any]:
        if name not in self._ALLOWED_TOOLS:
            return {"error": f"tool '{name}' not allowed"}
        fn = self._functions[name]
        try:
            return fn(**kwargs)
        except Exception as exc:
            logger.error("Error ejecutando '%s': %s", name, exc)
            return {"error": str(exc)}


_tool_registry = ToolRegistry()


def _get_tool_schema(name: str) -> dict[str, Any] | None:
    """Devuelve el schema JSON del tool o None si no existe."""
    for entry in TOOLS_SCHEMA:
        func = entry.get("function", {})
        if func.get("name") == name:
            return {"type": "object", **func.get("parameters", {})}
    return None


# =============================================================================
# Tool Handlers
# =============================================================================


def record_user_details(
    email: str,
    name: str = "Nombre no proporcionado",
    notes: str = "not provided",
) -> dict[str, str]:
    """Registra detalles de contacto del usuario via Pushover."""
    _pushover(f"Contacto registrado → {name} | {email} | {notes}")
    return {"recorded": "ok"}


def record_unknown_question(question: str) -> dict[str, str]:
    """Registra preguntas no respondidas para revisión."""
    _pushover(f"Pregunta sin respuesta → {question}")
    return {"recorded": "ok"}


# Registrar en el registry global
_tool_registry.register("record_user_details", record_user_details)
_tool_registry.register("record_unknown_question", record_unknown_question)


# =============================================================================
# Tool Schema for LLM
# =============================================================================


TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "record_user_details",
            "description": (
                "Úsala SOLAMENTE cuando el usuario proporcione SU email voluntariamente "
                "para ser contactado. Registra nombre, email y contexto de la conversación. "
                "No la uses si el usuario no ha dado su email explícitamente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Email del usuario."},
                    "name": {
                        "type": "string",
                        "description": "Nombre del usuario, si lo ha dado.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Contexto relevante para el seguimiento.",
                    },
                },
                "required": ["email"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_unknown_question",
            "description": (
                "Úsala cuando no puedas responder una pregunta del usuario. "
                "Registra la pregunta para revisión posterior."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Pregunta sin respuesta."},
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
]
