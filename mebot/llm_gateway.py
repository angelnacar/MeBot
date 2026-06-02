# =============================================================================
# llm_gateway.py — LLM clients and gateway for Mebot
# =============================================================================
"""LLM clients with Ollama backend."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, NotRequired

from openai import OpenAI

from .config import _MODEL_CONFIG, ModelConfig, Role

logger = logging.getLogger(__name__)


# =============================================================================
# LLM Client Interface
# =============================================================================


class LLMClient(ABC):
    """Interfaz abstracta para clientes LLM."""

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
        """Genera una completación y devuelve el contenido textual."""
        ...

    @abstractmethod
    def get_usage(self) -> dict[str, int] | None:
        """Devuelve estadísticas de uso de la última llamada."""
        ...


@dataclass
class LLMResponse:
    """Respuesta completa del LLM con contenido y tool_calls."""

    content: str
    tool_calls: list[Any] | None
    finish_reason: str | None


class OpenAIClient(LLMClient):
    """Cliente genérico que usa el SDK oficial de OpenAI con base_url configurable.

    Soporta Ollama y cualquier API compatible con OpenAI.

    Attributes:
        base_url: URL base de la API del proveedor.
    """

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self._base_url = base_url
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._last_usage: dict[str, int] | None = None

    @property
    def provider(self) -> str:
        """Nombre del proveedor extraído de la base URL."""
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
            raise RuntimeError(f"Response truncated (max_tokens): {model}")
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


def _get_ollama_client() -> OpenAIClient:
    """Obtiene el cliente Ollama (inicialización lazy)."""
    return OpenAIClient(
        base_url=os.environ.get("OLLAMA_BASE_URL", "https://ollama.com/v1"),
        api_key=os.environ.get("OLLAMA_API_KEY"),
    )


# =============================================================================
# LLM Gateway
# =============================================================================


class LLMGateway:
    """Puerta de entrada unificada a los LLMs (Ollama)."""

    def __init__(self) -> None:
        self._ollama: OpenAIClient | None = None

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
        """Genera una completación con el modelo configurado para el rol.

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
        cfg: ModelConfig = _MODEL_CONFIG[role]
        result = self._invoke(
            self._ollama_client, cfg.name, messages, tools, max_tokens, temperature, raw
        )
        logger.debug("✓ [%s] %s/%s", role.value, cfg.provider, cfg.name)
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
