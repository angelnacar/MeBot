# =============================================================================
# pipelines.py — Multi-agent pipelines for Mebot
# =============================================================================
"""Pipeline classes for input guard, quality, agent, rerun, and orchestration."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from .config import (
    _AGENT_MAX_TOKENS,
    _INPUT_GUARD_MAX_TOKENS,
    _QUALITY_MAX_TOKENS,
    QUALITY_THRESHOLD,
    TOXICITY_BLOCK_MSG,
    TOXICITY_THRESHOLD,
    Role,
)
from .llm_gateway import LLMResponse, _llm_gateway
from .prompt_loader import input_guard_prompt, quality_prompt, system_prompt
from .sanitizer import OutputSanitizer
from .tools import TOOLS_SCHEMA, _get_tool_schema, _tool_registry
from .types import InputGuardResult, QualityResult, ToolCallResult

try:
    from jsonschema import ValidationError, validate
except ImportError:
    validate = None  # type: ignore
    ValidationError = Exception  # type: ignore

logger = logging.getLogger(__name__)

Messages = list[dict[str, str]]

# =============================================================================
# Output Sanitizer (singleton)
# =============================================================================

_output_sanitizer = OutputSanitizer()


# =============================================================================
# Helper Functions
# =============================================================================


def _sanitize_history(history: Messages) -> Messages:
    """Extrae solo role+content del historial de Gradio (descarta metadatos)."""
    clean: Messages = []
    for m in history:
        if isinstance(m, dict) and "role" in m and "content" in m:
            clean.append({"role": m["role"], "content": m.get("content") or ""})
    return clean


def _parse_json(raw: str | None, label: str) -> dict[str, Any] | None:
    """Parse JSON defensivo contra content=None, string vacío, o bloques markdown."""
    if not raw:
        logger.warning("%s: content vacío o None", label)
        return None

    cleaned = raw.strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) >= 2:
            cleaned = parts[1].strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("%s: JSONDecodeError — raw=%r — %s", label, raw[:300], exc)
        return None


# =============================================================================
# InputGuardPipeline
# =============================================================================


class InputGuardPipeline:
    """Evalúa tópico y toxicidad del mensaje en una sola llamada LLM.

    Combina TopicGuardrail y ToxicityPipeline en un único round-trip para
    reducir la latencia antes de que el agente principal genere su respuesta.

    Comportamiento ante fallos:
    - JSON vacío o inválido → fail-open (mensaje permitido).
    - Error de red/servicio → fail-closed (mensaje bloqueado por seguridad).
    """

    OFF_TOPIC_MSG = (
        "Solo puedo responder preguntas sobre el perfil profesional de Ángel Nácar, "
        "su experiencia, habilidades, proyectos o cómo contactar con él. "
        "¿Tienes alguna duda sobre alguno de estos temas?"
    )

    def evaluate(self, message: str, history: Messages) -> tuple[bool, str, InputGuardResult]:
        """Evalúa el mensaje y devuelve resultado combinado.

        Returns:
            (is_allowed, block_message, guard_result)
            Si is_allowed=True, block_message está vacío.
        """
        try:
            content = _llm_gateway.complete(
                Role.INPUT_GUARD,
                [
                    {
                        "role": "system",
                        "content": (
                            "Eres un clasificador de seguridad. "
                            "Responde SOLO con JSON válido, sin texto adicional."
                        ),
                    },
                    {"role": "user", "content": input_guard_prompt(message, history)},
                ],
                max_tokens=_INPUT_GUARD_MAX_TOKENS,
                temperature=0.0,
            )
            parsed = _parse_json(content, "input_guard")
            if parsed is not None:
                result = InputGuardResult(
                    topic=parsed.get("topic", "ACCEPTABLE"),
                    topic_confidence=float(parsed.get("topic_confidence", 0.0)),
                    toxicity=parsed.get("toxicity", "ACCEPTABLE"),
                    toxicity_score=float(parsed.get("toxicity_score", 0.0)),
                    reason=parsed.get("reason", ""),
                    suggested_redirect=parsed.get("suggested_redirect", ""),
                )

                # Verificar tópico primero
                if result["topic"] == "OFF_TOPIC" and result["topic_confidence"] >= 0.5:
                    logger.warning(
                        "InputGuard → OFF_TOPIC (confidence=%.2f) | %s",
                        result["topic_confidence"],
                        result["reason"],
                    )
                    redirect = result["suggested_redirect"] or self.OFF_TOPIC_MSG
                    return False, redirect, result

                # Verificar toxicidad
                if result["toxicity_score"] > TOXICITY_THRESHOLD:
                    logger.warning(
                        "InputGuard → TOXIC (score=%.2f) | %s",
                        result["toxicity_score"],
                        result["reason"],
                    )
                    return False, TOXICITY_BLOCK_MSG, result

                logger.debug(
                    "InputGuard → OK (topic=%s conf=%.2f, toxicity=%.2f) | %s",
                    result["topic"],
                    result["topic_confidence"],
                    result["toxicity_score"],
                    result["reason"],
                )
                return True, "", result

            # JSON vacío → fail-open
            logger.warning("InputGuardPipeline: JSON vacío, permitiendo mensaje")
            return True, "", _default_guard_result()

        except RuntimeError as exc:
            if "truncated" in str(exc).lower():
                # Truncado por max_tokens: JSON incompleto, no es error de servicio → fail-open
                logger.warning("InputGuardPipeline: respuesta truncada, permitiendo mensaje — %s", exc)
                return True, "", _default_guard_result()
            logger.error("InputGuardPipeline falló: %s", exc)
            return False, TOXICITY_BLOCK_MSG, InputGuardResult(
                topic="ACCEPTABLE",
                topic_confidence=0.0,
                toxicity="NOT_ACCEPTABLE",
                toxicity_score=1.0,
                reason="evaluador no disponible — bloqueado por seguridad",
                suggested_redirect="",
            )
        except Exception as exc:
            logger.error("InputGuardPipeline falló: %s", exc)
            # Fail-closed ante error real de red/servicio
            return False, TOXICITY_BLOCK_MSG, InputGuardResult(
                topic="ACCEPTABLE",
                topic_confidence=0.0,
                toxicity="NOT_ACCEPTABLE",
                toxicity_score=1.0,
                reason="evaluador no disponible — bloqueado por seguridad",
                suggested_redirect="",
            )


def _default_guard_result() -> InputGuardResult:
    return InputGuardResult(
        topic="ACCEPTABLE",
        topic_confidence=0.0,
        toxicity="ACCEPTABLE",
        toxicity_score=0.0,
        reason="sin respuesta del evaluador",
        suggested_redirect="",
    )


# =============================================================================
# QualityEvaluator
# =============================================================================


class QualityEvaluator:
    """Evalúa la calidad de la respuesta del agente.

    Fallback: si falla, retorna GOOD con score 1.0 (fail-safe).
    """

    def evaluate(self, reply: str, message: str, history: Messages) -> QualityResult:
        """Evalúa la respuesta y devuelve el resultado.

        Fail-safe: si falla, aceptamos la respuesta.
        """
        try:
            content = _llm_gateway.complete(
                Role.EVALUATOR,
                [
                    {"role": "system", "content": quality_prompt(message, history, reply)},
                    {
                        "role": "user",
                        "content": "Evalúa la respuesta según las instrucciones y devuelve el JSON.",
                    },
                ],
                max_tokens=_QUALITY_MAX_TOKENS,
                temperature=0.0,
            )
            parsed = _parse_json(content, "quality")
            if parsed is not None:
                return QualityResult(
                    classification=parsed.get("classification", "GOOD"),
                    quality_score=float(parsed.get("quality_score", 1.0)),
                    issues=list(parsed.get("issues") or []),
                    suggestion=str(parsed.get("suggestion") or ""),
                )
            logger.warning("QualityEvaluator: contenido vacío o JSON inválido, tratando como GOOD")
        except Exception as exc:
            logger.error("QualityEvaluator falló: %s", exc)

        # Fail-safe
        return QualityResult(
            classification="GOOD",
            quality_score=1.0,
            issues=[],
            suggestion="",
        )


# =============================================================================
# AgentPipeline
# =============================================================================


@dataclass
class AgentResponse:
    """Respuesta del agente principal."""

    content: str
    tool_calls_executed: int = 0


class AgentPipeline:
    """Agente principal con tool-calling.

    Ejecuta un loop de tool_calls hasta que el modelo genere contenido textual.
    """

    MAX_ITERATIONS = 10

    def run(self, message: str, history: Messages) -> AgentResponse:
        """Ejecuta el agente principal con tool loop.

        Retorna AgentResponse con contenido y contador de tools ejecutadas.
        """
        messages: Messages = (
            [{"role": "system", "content": system_prompt()}]
            + _sanitize_history(history)
            + [{"role": "user", "content": message}]
        )

        tool_calls_executed = 0

        for iteration in range(self.MAX_ITERATIONS):
            try:
                llm_response = _llm_gateway.complete(
                    Role.AGENT,
                    messages,
                    tools=TOOLS_SCHEMA,
                    max_tokens=_AGENT_MAX_TOKENS,
                    temperature=0.0,
                    raw=True,
                )
            except Exception as exc:
                logger.error("AgentPipeline iteración %d falló: %s", iteration, exc)
                return AgentResponse(
                    content="Lo siento, ha ocurrido un error. Por favor, inténtalo de nuevo.",
                    tool_calls_executed=tool_calls_executed,
                )

            content = llm_response.content

            # Si el modelo devolvió tool_calls en el mensaje (API de OpenAI)
            if llm_response.tool_calls:
                tool_calls_executed += 1
                tool_results = self._execute_tools(llm_response.tool_calls)
                messages.append(
                    {
                        "role": "assistant",
                        "content": content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            if hasattr(tc, "function")
                            else tc
                            for tc in llm_response.tool_calls
                        ],
                    }
                )
                messages.extend(tool_results)
                continue

            # Si content tiene JSON con tool_calls (formato alternativo)
            parsed = _parse_json(content, f"agent-{iteration}")
            if parsed is None:
                if content.strip():
                    return AgentResponse(
                        content=content.strip(),
                        tool_calls_executed=tool_calls_executed,
                    )
                continue

            tool_calls_data = parsed.get("tool_calls")
            if tool_calls_data:
                tool_calls_executed += 1
                tool_results = self._execute_tools(tool_calls_data)
                messages.append(
                    {
                        "role": "assistant",
                        "content": parsed.get("content") or "",
                        "tool_calls": tool_calls_data,
                    }
                )
                messages.extend(tool_results)
                continue

            # Respuesta textual directa
            if content.strip():
                return AgentResponse(
                    content=content.strip(),
                    tool_calls_executed=tool_calls_executed,
                )

        logger.error("Sin respuesta textual tras %d iteraciones", self.MAX_ITERATIONS)
        return AgentResponse(
            content="Lo siento, no he podido generar una respuesta. Por favor, inténtalo de nuevo.",
            tool_calls_executed=tool_calls_executed,
        )

    @staticmethod
    def _normalize_tool_call(tc: Any) -> tuple[str, dict[str, Any], str]:
        """Normaliza tool call (Pydantic o dict) a tupla (name, args, tool_id)."""
        if hasattr(tc, "function") and hasattr(tc, "id"):
            name = tc.function.name
            args_str = tc.function.arguments
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
            tool_id = tc.id
        else:
            name = tc.get("name") or tc.get("function", {}).get("name", "")
            args_raw = tc.get("arguments") or tc.get("function", {}).get("arguments", "{}")
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            tool_id = tc.get("id", "")
        return name, args, tool_id

    def _execute_tools(self, tool_calls_data: Any) -> list[ToolCallResult]:
        """Ejecuta las herramientas solicitadas y devuelve los resultados."""
        results: list[ToolCallResult] = []
        if not isinstance(tool_calls_data, list):
            return results

        for tc in tool_calls_data:
            name, args, tool_id = self._normalize_tool_call(tc)

            if not name:
                continue

            logger.info("Tool → %s", name)

            tool_schema = _get_tool_schema(name)
            if tool_schema:
                try:
                    validate(instance=args, schema=tool_schema)
                except ValidationError as e:
                    logger.error("Args validation failed for '%s': %s", name, e)
                    results.append(
                        ToolCallResult(
                            role="tool",
                            content=json.dumps({"error": "invalid arguments"}),
                            tool_call_id=tool_id or f"call_{name}",
                        )
                    )
                    continue

            args_for_call = {k: v for k, v in args.items() if k != "name"}
            result = _tool_registry.call(name, **args_for_call)

            results.append(
                ToolCallResult(
                    role="tool",
                    content=json.dumps(result),
                    tool_call_id=tool_id or f"call_{name}",
                )
            )
        return results


# =============================================================================
# RerunPipeline
# =============================================================================


class RerunPipeline:
    """Regenera la respuesta incorporando feedback del evaluador."""

    def run(
        self,
        original_reply: str,
        message: str,
        history: Messages,
        feedback: str,
    ) -> str:
        """Regenera la respuesta con el feedback del evaluador."""
        augmented = (
            f"{system_prompt()}\n\n"
            "## Respuesta anterior rechazada por control de calidad\n\n"
            f"**Respuesta rechazada:**\n{original_reply}\n\n"
            f"**Motivo del rechazo:**\n{feedback}\n\n"
            "Genera una nueva respuesta corrigiendo los problemas indicados. "
            "Mantén el mismo tono profesional y cercano."
        )
        messages: Messages = (
            [{"role": "system", "content": augmented}] + history + [{"role": "user", "content": message}]
        )
        try:
            return _llm_gateway.complete(Role.RERUN, messages)
        except Exception as exc:
            logger.error("RerunPipeline falló: %s — manteniendo original", exc)
            return original_reply


# =============================================================================
# PipelineOrchestrator
# =============================================================================


class PipelineOrchestrator:
    """Orquestador central del pipeline multi-agente.

    Coordina: InputGuard → Agent → Quality → Rerun opcional.
    """

    def __init__(self) -> None:
        self._guard = InputGuardPipeline()
        self._agent = AgentPipeline()
        self._quality = QualityEvaluator()
        self._rerun = RerunPipeline()

    def chat(self, message: str, history: Messages) -> str:
        """Ejecuta el pipeline completo y devuelve la respuesta sanitizada."""
        # ── Paso 1: Input Guard (tópico + toxicidad) ────────────────────────────
        is_allowed, block_msg, guard_result = self._guard.evaluate(message, history)
        if not is_allowed:
            logger.warning("Mensaje BLOQUEADO por InputGuard: %s", message[:100])
            return block_msg

        logger.info(
            "InputGuard → OK | topic=%s (conf=%.2f) | toxicity=%.2f | %s",
            guard_result["topic"],
            guard_result["topic_confidence"],
            guard_result["toxicity_score"],
            guard_result["reason"],
        )

        # ── Paso 2: Agente principal ───────────────────────────────────────────
        agent_response = self._agent.run(message, history)
        reply = agent_response.content

        # ── Paso 3: Calidad ──────────────────────────────────────────────────────
        quality_result = self._quality.evaluate(reply, message, history)
        logger.info(
            "Calidad → %s | score=%.2f | issues=%s",
            quality_result["classification"],
            quality_result["quality_score"],
            quality_result["issues"],
        )

        # ── Paso 4: Rerun si es necesario ──────────────────────────────────────
        if quality_result["quality_score"] < QUALITY_THRESHOLD:
            feedback = (
                quality_result["suggestion"]
                if quality_result["suggestion"]
                else "; ".join(quality_result["issues"])
            )
            logger.warning(
                "Respuesta RECHAZADA (score=%.2f) → rerun. Feedback: %s",
                quality_result["quality_score"],
                feedback,
            )
            reply = self._rerun.run(reply, message, history, feedback)

        return _output_sanitizer.sanitize(reply)


# Instancia global del orquestador
_orchestrator = PipelineOrchestrator()


# =============================================================================
# Public API — chat()
# =============================================================================


def chat(message: str, history: Messages) -> str:
    """Función principal del chatbot CV Ángel Nácar.

    Pipeline (3 llamadas LLM mínimas):
      1. InputGuard   → Ollama — evaluación combinada de tópico y toxicidad
      2. Agente       → Ollama — respuesta con tool calling opcional
         └ tool loop  → record_user_details, record_unknown_question
      3. Calidad      → Ollama — evaluación de la respuesta
      4. Rerun        → Ollama — opcional si quality_score < 0.6

    Args:
        message: turno actual del usuario.
        history: historial [{role, content}, ...].

    Returns:
        Respuesta final sanitizada como string.
    """
    return _orchestrator.chat(message, history)
