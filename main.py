#!/usr/bin/env python3
# =============================================================================
# main.py — Entry point for Mebot (project root)
# =============================================================================
"""Main entry point for Mebot CV chatbot."""

if __name__ == "__main__":
    from ui import build_ui
    from mebot import chat

    app = build_ui(chat)
    app.launch(server_name="0.0.0.0", server_port=7860)
