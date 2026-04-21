# =============================================================================
# pushover.py — Pushover notifications for Mebot
# =============================================================================
"""Send notifications via Pushover."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _pushover(message: str) -> None:
    """Envía una notificación via Pushover."""
    user = os.getenv("PUSHOVER_USER")
    token = os.getenv("PUSHOVER_TOKEN")
    url = "https://api.pushover.net/1/messages.json"

    logger.info("Pushover → %s", message)
    try:
        import requests as _requests

        r = _requests.post(
            url,
            data={"user": user, "token": token, "message": message},
            timeout=5,
        )
        r.raise_for_status()
    except Exception as exc:
        logger.warning("Pushover error: %s", exc)
