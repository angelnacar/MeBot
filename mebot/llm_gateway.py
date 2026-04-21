# =============================================================================
# llm_gateway.py — LLM clients and gateway for Mebot
# =============================================================================
"""LLM clients with automatic provider selection and fallback."""

from __future__ import annotations

import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Any, NotRequired

from openai import OpenAI

from .config import (
    _GROQ_LIMITS,
    _MODEL_CONFIG,
    _SAFETY_FACTOR,
    ModelConfig,
    Role,
)
from .types import RateLimitConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limit Tracker
# =============================================================================


class RateLimitTracker:
    """Contabiliza llamadas Groq por modelo con ventana deslizante (monotonic).

    Thread-safe.
    """

    __slots__ = ("_lock", "_rpm_ts", "_rpd_ts")

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._rpm_ts: dict[str, deque[float]] = {}
        self._rpd_ts: dict[str, deque[float]] = {}

    def _ensure(self, model: str) -> None:
        if model not in self._rpm_ts:
            self._rpm_ts[model] = deque()
            self._rpd_ts[model] = deque()

    @staticmethod
    def _purge(dq: deque[float], window: float) -> None:
        cutoff = time.monotonic() - window
        while dq and dq[0] < cutoff:
            dq.popleft()

    def is_within_limits(self, model: str) -> bool:
        """True si el modelo tiene margen dentro del 80% del límite."""
        limits = _GROQ_LIMITS.get(model)
        if not limits:
            return True
        with self._lock:
            self._ensure(model)
            self._purge(self._rpm_ts[model], 60.0)
            self._purge(self._rpd_ts[model], 86_400.0)
            rpm_ok = len(self._rpm_ts[model]) < limits["rpm"] * _SAFETY_FACTOR
            rpd_ok = len(self._rpd_ts[model]) < limits["rpd"] * _SAFETY_FACTOR
            return rpm_ok and rpd_ok

    def can_use(self, model: str) -> bool:
        """Alias para is_within_limits (compatibilidad con tests)."""
        return self.is_within_limits(model)

    def record(self, model: str) -> None:
        """Registra una llamada completada."""
        if model not in _GROQ_LIMITS:
            return
        with self._lock:
            self._ensure(model)
            ts = time.monotonic()
            self._rpm_ts[model].append(ts)
            self._rpd_ts[model].append(ts)

    def status(self) -> dict[str, dict[str, int]]:
        """Estado actual de uso para logging/debug."""
        out: dict[str, dict[str, int]] = {}
        with self._lock:
            for model, limits in _GROQ_LIMITS.items():
                self._purge(self._rpm_ts.get(model, deque()), 60.0)
                self._purge(self._rpd_ts.get(model, deque()), 86_400.0)
                out[model] = {
                    "rpm_used": len(self._rpm_ts.get(model, deque())),
                    "rpm_limit": limits["rpm"],
                    "rpd_used": len(self._rpd_ts.get(model, deque())),
                    "rpd_limit": limits["rpd"],
                }
        return out


_rate_tracker = RateLimitTracker()


# =============================================================================
# LLM Client Interface
# =============================================================================


class LLMClient(ABC):
    """Interfaz abstracta para clientes LLM.

    Define el contrato que deben implementar todos los clientes
    de modelos de lenguaje utilizados en el pipeline.

    Attributes:
        provider: Nombre del proveedor ('groq', 'ollama').

    Methods:
        complete: Genera una completación de texto.
        get_usage: Devuelve el uso de tokens de la última llamada.
    """

    @property
    @abstractmethod
    def provider(self) -> str:
        """Nombre del proveedor LLM."""
        ...

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        tools: NotRequired[list[dict[str, Any]]],
        max_tokens: NotRequired[int],
        temperature: NotRequired[float],
    ) -> str:
        """Genera una completación y devuelve el contenido textual.

        Args:
            messages: Lista de mensajes en formato {role, content}.
            model: Nombre del modelo a utilizar.
            tools: Lista opcional de definiciones de herramientas.
            max_tokens: Máximo de tokens a generar.
            temperature: Temperatura para el sampling.

        Returns:
            Contenido textual de la completación.
        """
        ...

    @abstractmethod
    def get_usage(self) -> dict[str, int] | None:
        """Devuelve estadísticas de uso de la última llamada.

        Returns:
            Diccionario con 'prompt_tokens', 'completion_tokens',
            'total_tokens' o None si no hay datos disponibles.
        """
        ...


@dataclass
class LLMResponse:
    """Respuesta completa del LLM con contenido y tool_calls."""

    content: str
    tool_calls: list[Any] | None
    finish_reason: str | None


class OpenAIClient(LLMClient):
    """Cliente genérico que usa el SDK oficial de OpenAI con base_url configurable.

    Soporta Groq, Ollama y cualquier API compatible con OpenAI.

    Attributes:
        base_url: URL base de la API del proveedor.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
    ) -> None:
        self._base_url = base_url
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._last_usage: dict[str, int] | None = None

    @property
    def provider(self) -> str:
        """Nombre del proveedor extraído de la base URL."""
        if "groq" in self._base_url:
            return "groq"
        if "ollama" in self._base_url:
            return "ollama"
        return "openai"

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        tools: NotRequired[list[dict[str, Any]]] | None = None,
        max_tokens: NotRequired[int] = 1024,
        temperature: NotRequired[float] = 0.0,
    ) -> str:
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if response.usage:
            self._last_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise RuntimeError(f"Response truncated (rate limit): {model}")
        return choice.message.content or ""

    def complete_raw(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        tools: NotRequired[list[dict[str, Any]]] | None = None,
        max_tokens: NotRequired[int] = 1024,
        temperature: NotRequired[float] = 0.0,
    ) -> LLMResponse:
        """Versión raw que devuelve contenido + tool_calls + finish_reason."""
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if response.usage:
            self._last_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            tool_calls=choice.message.tool_calls,
            finish_reason=choice.finish_reason,
        )

    def get_usage(self) -> dict[str, int] | None:
        """Devuelve estadísticas de uso de la última llamada."""
        return self._last_usage


# =============================================================================
# Lazy client initialization
# =============================================================================


def _get_groq_client() -> OpenAIClient:
    """Obtiene el cliente Groq (inicialización lazy)."""
    return OpenAIClient(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY"),
    )


def _get_ollama_client() -> OpenAIClient:
    """Obtiene el cliente Ollama (inicialización lazy)."""
    return OpenAIClient(
        base_url=os.environ.get("OLLAMA_BASE_URL", "https://ollama.com/v1"),
        api_key=os.environ.get("OLLAMA_API_KEY"),
    )


# =============================================================================
# LLM Gateway — proveedor automático + fallback
# =============================================================================


class LLMGateway:
    """Puerta de entrada unificada a los LLMs.

    Selecciona primario o fallback según rate limits y disponibilidad.
    """

    def __init__(self) -> None:
        self._groq: OpenAIClient | None = None
        self._ollama: OpenAIClient | None = None

    @property
    def _groq_client(self) -> OpenAIClient:
        if self._groq is None:
            self._groq = _get_groq_client()
        return self._groq

    @property
    def _ollama_client(self) -> OpenAIClient:
        if self._ollama is None:
            self._ollama = _get_ollama_client()
        return self._ollama

    def complete(
        self,
        role: Role,
        messages: list[dict[str, str]],
        *,
        tools: NotRequired[list[dict[str, Any]]] | None = None,
        max_tokens: NotRequired[int] = 1024,
        temperature: NotRequired[float] = 0.0,
        raw: bool = False,
    ) -> str | LLMResponse:
        """Genera una completación con fallback automático.

        Args:
            role: Rol del modelo en el pipeline.
            messages: Historial de mensajes.
            tools: Definición de herramientas (solo para AGENT).
            max_tokens: Máximo de tokens a generar.
            temperature: Temperatura para sampling.
            raw: Si True, devuelve LLMResponse; si False, solo str.

        Returns:
            str si raw=False, LLMResponse si raw=True.
        """
        primary_cfg, fallback_cfg = _MODEL_CONFIG[role]

        use_primary = (
            primary_cfg.provider != "groq"
            or _rate_tracker.is_within_limits(primary_cfg.name)
        )

        if use_primary:
            try:
                client = self._groq_client if primary_cfg.provider == "groq" else self._ollama_client
                result = self._invoke(
                    client, primary_cfg.name, messages, tools, max_tokens, temperature, raw
                )
                if primary_cfg.provider == "groq":
                    _rate_tracker.record(primary_cfg.name)
                logger.debug("✓ [%s] %s/%s", role.value, primary_cfg.provider, primary_cfg.name)
                return result
            except Exception as exc:
                logger.warning(
                    "✗ [%s] %s/%s falló (%s) → fallback",
                    role.value,
                    primary_cfg.provider,
                    primary_cfg.name,
                    exc,
                )
        else:
            logger.info("⚡ Rate limit Groq (%s) → fallback directo", primary_cfg.name)

        # Fallback
        client = self._ollama_client if fallback_cfg.provider == "ollama" else self._groq_client
        result = self._invoke(
            client, fallback_cfg.name, messages, tools, max_tokens, temperature, raw
        )
        logger.debug("✓ fallback [%s] %s/%s", role.value, fallback_cfg.provider, fallback_cfg.name)
        return result

    def _invoke(
        self,
        client: OpenAIClient,
        model: str,
        messages: list[dict[str, str]],
        tools: NotRequired[list[dict[str, Any]]] | None,
        max_tokens: int,
        temperature: float,
        raw: bool,
    ) -> str | LLMResponse:
        """Invoca el cliente y devuelve resultado."""
        if raw:
            result = client.complete_raw(
                model=model,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            # Fail-fast si no hay contenido ni tool calls
            if not result.content and not result.tool_calls:
                raise RuntimeError(f"Empty response without tool_calls: {model}")
            return result
        return client.complete(
            messages,
            model=model,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )


_llm_gateway = LLMGateway()
