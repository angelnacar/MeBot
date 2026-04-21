# =============================================================================
# pipelines.py — Multi-agent pipelines for Mebot
# =============================================================================
"""Pipeline classes for toxicity, quality, agent, rerun, and orchestration."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, TypedDict

from .config import (
    _AGENT_MAX_TOKENS,
    _QUALITY_MAX_TOKENS,
    _TOXICITY_MAX_TOKENS,
    QUALITY_THRESHOLD,
    TOXICITY_BLOCK_MSG,
    TOXICITY_THRESHOLD,
    Role,
)
from .llm_gateway import LLMResponse, _llm_gateway
from .prompt_loader import quality_prompt, system_prompt, topic_guardrail_prompt, toxicity_prompt
from .sanitizer import OutputSanitizer
from .tools import TOOLS_SCHEMA, _get_tool_schema, _tool_registry
from .types import QualityResult, ToolCallResult, ToxicityResult

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
# ToxicityPipeline
# =============================================================================


class ToxicityPipeline:
    """Evalúa la toxicidad de un mensaje de usuario.

    Fallback: si falla, retorna ACCEPTABLE con score 0.0 (fail-open).
    """

    def evaluate(self, message: str, history: Messages) -> ToxicityResult:
        """Evalúa el mensaje y devuelve el resultado.

        Fail-open: si falla, no bloqueamos al usuario.
        """
        try:
            content = _llm_gateway.complete(
                Role.TOXICITY,
                [
                    {
                        "role": "system",
                        "content": "Eres un evaluador de seguridad. Responde SOLO con JSON válido, sin texto adicional.",
                    },
                    {"role": "user", "content": toxicity_prompt(message, history)},
                ],
                max_tokens=_TOXICITY_MAX_TOKENS,
                temperature=0.0,
            )
            parsed = _parse_json(content, "toxicity")
            if parsed is not None:
                return ToxicityResult(
                    classification=parsed.get("classification", "ACCEPTABLE"),
                    toxicity_score=float(parsed.get("toxicity_score", 0.0)),
                    reason=parsed.get("reason", ""),
                )
            # Contenido vacío del evaluador → no tóxico (fail-open)
            logger.warning("ToxicityPipeline: contenido vacío, tratando como seguro")
            return ToxicityResult(
                classification="ACCEPTABLE",
                toxicity_score=0.0,
                reason="evaluador sin respuesta",
            )
        except Exception as exc:
            logger.error("ToxicityPipeline falló: %s", exc)
            # Solo fail-closed ante error real de red/servicio
            return ToxicityResult(
                classification="NOT_ACCEPTABLE",
                toxicity_score=1.0,
                reason="evaluador no disponible — bloqueado por seguridad",
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
            # Contenido vacío o JSON truncado → fail-safe
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
# TopicGuardrail
# =============================================================================


class TopicGuardrailResult(TypedDict):
    """Resultado de la evaluación del guardrail de tópicos.

    Attributes:
        classification: 'ACCEPTABLE' o 'OFF_TOPIC'.
        confidence: Puntuación de confianza entre 0.0 y 1.0.
        reason: Explicación de la clasificación.
        suggested_redirect: Mensaje sugerido para reconducir (si es OFF_TOPIC).
    """

    classification: str
    confidence: float
    reason: str
    suggested_redirect: str


class TopicGuardrail:
    """Guardrail de tópicos para evitar preguntas off-topic.

    Permite saludos y preguntas genéricas, pero bloquea temas ajenos al perfil.
    """

    OFF_TOPIC_MSG = (
        "Solo puedo responder preguntas sobre el perfil profesional de Ángel Nácar, "
        "su experiencia, habilidades, proyectos o cómo contactar con él. "
        "¿Tienes alguna duda sobre alguno de estos temas?"
    )

    def evaluate(self, message: str, history: Messages) -> tuple[bool, str]:
        """Evalúa si el mensaje está dentro del ámbito permitido.

        Returns:
            (is_allowed, redirect_message) tuple.
            Si is_allowed=True, redirect_message está vacío.
            Si is_allowed=False, redirect_message contiene el mensaje de reconducción.
        """
        try:
            content = _llm_gateway.complete(
                Role.TOXICITY,
                [
                    {
                        "role": "system",
                        "content": "Eres un clasificador de tópicos. Responde SOLO con JSON válido.",
                    },
                    {"role": "user", "content": topic_guardrail_prompt(message, history)},
                ],
                max_tokens=_TOXICITY_MAX_TOKENS,
                temperature=0.0,
            )
            parsed = _parse_json(content, "topic_guardrail")
            if parsed is not None:
                classification = parsed.get("classification", "OFF_TOPIC")
                confidence = float(parsed.get("confidence", 0.0))

                # Fail-open con confianza baja → permitir pero monitorizar
                if classification == "OFF_TOPIC" and confidence >= 0.5:
                    logger.warning(
                        "TopicGuardrail → OFF_TOPIC (confidence=%.2f) | %s",
                        confidence,
                        parsed.get("reason", ""),
                    )
                    return False, self.OFF_TOPIC_MSG

                logger.debug(
                    "TopicGuardrail → %s (confidence=%.2f) | %s",
                    classification,
                    confidence,
                    parsed.get("reason", ""),
                )

            # Contenido vacío o JSON inválido → permitir (fail-open)
            return True, ""

        except Exception as exc:
            logger.error("TopicGuardrail falló: %s", exc)
            # Fail-open: no bloqueamos si el guardrail falla
            return True, ""


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

            # Si content tiene JSON con tool_calls (formato anterior/alternativo)
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
            # Pydantic ChatCompletionMessageFunctionToolCall
            name = tc.function.name
            args_str = tc.function.arguments
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
            tool_id = tc.id
        else:
            # Dict (de JSON parseado)
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

            # Validar argumentos contra el schema del tool
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

            # Eliminar 'name' de args si existe (ya se pasa como primer argumento)
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
    """Regenera la respuesta incorporando feedback del evaluador.

    Usa Ollama exclusivamente para conservar cuota Groq.
    """

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

    Coordina: TopicGuardrail → Toxicity → Agent → Quality → Rerun opcional.
    """

    def __init__(self) -> None:
        self._topic = TopicGuardrail()
        self._toxicity = ToxicityPipeline()
        self._agent = AgentPipeline()
        self._quality = QualityEvaluator()
        self._rerun = RerunPipeline()

    def chat(self, message: str, history: Messages) -> str:
        """Ejecuta el pipeline completo y devuelve la respuesta sanitizada."""
        # ── Paso 1: Topic Guardrail ──────────────────────────────────────────────
        is_allowed, redirect_msg = self._topic.evaluate(message, history)
        if not is_allowed:
            logger.warning("Mensaje BLOQUEADO por TopicGuardrail: %s", message[:100])
            return redirect_msg

        # ── Paso 2: Toxicidad ───────────────────────────────────────────────────
        toxicity_result = self._toxicity.evaluate(message, history)
        logger.info(
            "Toxicidad → %s | score=%.2f | %s",
            toxicity_result["classification"],
            toxicity_result["toxicity_score"],
            toxicity_result["reason"],
        )

        if toxicity_result["toxicity_score"] > TOXICITY_THRESHOLD:
            logger.warning("Mensaje BLOQUEADO (toxicity=%.2f)", toxicity_result["toxicity_score"])
            return TOXICITY_BLOCK_MSG

        # ── Paso 3: Agente principal ───────────────────────────────────────────
        agent_response = self._agent.run(message, history)
        reply = agent_response.content

        # ── Paso 4: Calidad ──────────────────────────────────────────────────────
        quality_result = self._quality.evaluate(reply, message, history)
        logger.info(
            "Calidad → %s | score=%.2f | issues=%s",
            quality_result["classification"],
            quality_result["quality_score"],
            quality_result["issues"],
        )

        # ── Paso 5: Rerun si es necesario ──────────────────────────────────────
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

    Pipeline:
      1. TopicGuardrail → Groq llama-3.1-8b-instant (fallback Ollama) - BLOQUEA off-topic
      2. Toxicidad      → Groq llama-3.1-8b-instant (fallback Ollama)
      3. Agente         → Groq llama-3.1-8b-instant (fallback Ollama)
         └ tool loop    → record_user_details, record_unknown_question
      4. Calidad        → Groq llama-3.1-8b-instant (fallback Ollama)
      5. Rerun opcional → Ollama (si quality_score < 0.6)

    Args:
        message: turno actual del usuario.
        history: historial [{role, content}, ...].

    Returns:
        Respuesta final sanitizada como string.
    """
    return _orchestrator.chat(message, history)
