# =============================================================================
# mebot — Multi-agent CV chatbot for Ángel Nácar Jiménez
# =============================================================================
"""Mebot: Interactive CV chatbot using a multi-agent LLM pipeline."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

# ── Carga de variables de entorno ─────────────────────────────────────────────

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

from .pipelines import chat  # noqa: E402

__all__ = ["chat"]
