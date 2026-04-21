# =============================================================================
# sanitizer.py — Output sanitization for Mebot
# =============================================================================
"""Filter sensitive information from LLM responses."""

from __future__ import annotations

import re


class OutputSanitizer:
    """Filtro de seguridad final para evitar fugas de información técnica.

    Elimina UUIDs, nombres de herramientas y menciones a proveedores.
    """

    UUID_PATTERN = re.compile(
        r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"
    )
    _TOOLS_TO_MASK = ["record_user_details", "record_unknown_question"]
    _INFRA_KEYWORDS = [
        "Groq",
        "Ollama",
        "gpt-oss",
        "gpt-oss-20b",
        "gpt-oss-120b",
        "gpt-oss:20b-cloud",
        "gpt-oss:120b-cloud",
        "nemotron",
        "gemma4:31b-cloud",
        "fallback",
        "tool_calls",
        "api.groq.com",
        "ollama.com",
    ]

    def sanitize(self, text: str) -> str:
        if not text:
            return ""

        # 1. Eliminar UUIDs
        text = self.UUID_PATTERN.sub("[ID OMITIDO]", text)

        # 2. Eliminar nombres de herramientas
        for tool in self._TOOLS_TO_MASK:
            text = text.replace(tool, "[HERRAMIENTA INTERNA]")

        # 3. Eliminar menciones a infraestructura
        for kw in self._INFRA_KEYWORDS:
            text = re.compile(re.escape(kw), re.IGNORECASE).sub("[SISTEMA]", text)

        return text
