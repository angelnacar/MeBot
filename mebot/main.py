# =============================================================================
# main.py — Entry point for Mebot
# =============================================================================
"""Main entry point for Mebot CV chatbot."""

from __future__ import annotations

if __name__ == "__main__":
    import logging

    from ui import build_ui
    from mebot import chat

    app = build_ui(chat)
    app.launch(server_name="0.0.0.0", server_port=7860)
