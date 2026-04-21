# =============================================================================
# tests/test_mebot.py — Tests for Mebot after refactor
# =============================================================================
"""
Unit and integration tests for Mebot CV chatbot.
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import mebot
from mebot.pipelines import (
    AgentPipeline,
    AgentResponse,
    PipelineOrchestrator,
    QualityEvaluator,
    TopicGuardrail,
    ToxicityPipeline,
    _orchestrator,
)
from mebot.llm_gateway import LLMResponse
from mebot.tools import (
    ToolRegistry,
    record_unknown_question,
    record_user_details,
    _tool_registry,
)
from mebot.sanitizer import OutputSanitizer
from mebot.llm_gateway import RateLimitTracker
from mebot.prompt_loader import PromptLoader
from mebot.config import _SAFETY_FACTOR

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sanitizer():
    return OutputSanitizer()


@pytest.fixture
def tool_registry():
    return ToolRegistry()


@pytest.fixture
def rate_tracker():
    return RateLimitTracker()


# =============================================================================
# OUTPUT SANITIZER TESTS
# =============================================================================


class TestOutputSanitizer:
    def test_sanitize_removes_uuid(self, sanitizer):
        text = "User ID: 12345678-1234-1234-1234-123456789012"
        result = sanitizer.sanitize(text)
        assert "[ID OMITIDO]" in result
        assert "12345678-1234-1234-1234-123456789012" not in result

    def test_sanitize_removes_tool_names(self, sanitizer):
        text = "Called record_user_details"
        result = sanitizer.sanitize(text)
        assert "[HERRAMIENTA INTERNA]" in result
        assert "record_user_details" not in result

    def test_sanitize_removes_groq_provider(self, sanitizer):
        text = "Using Groq API"
        result = sanitizer.sanitize(text)
        assert "Groq" not in result
        assert "[SISTEMA]" in result

    def test_sanitize_removes_ollama_provider(self, sanitizer):
        text = "Using Ollama"
        result = sanitizer.sanitize(text)
        assert "Ollama" not in result
        assert "[SISTEMA]" in result

    def test_sanitize_preserves_normal_text(self, sanitizer):
        text = "Hola, me gustaría saber sobre Java"
        result = sanitizer.sanitize(text)
        assert "Hola" in result
        assert "Java" in result

    def test_sanitize_handles_empty_string(self, sanitizer):
        assert sanitizer.sanitize("") == ""

    def test_sanitize_handles_none(self, sanitizer):
        assert sanitizer.sanitize(None) == ""


# =============================================================================
# TOOL REGISTRY TESTS
# =============================================================================


class TestToolRegistry:
    def test_call_allows_registered_tool(self, tool_registry):
        mock_fn = MagicMock(return_value={"recorded": "ok"})
        tool_registry.register("record_user_details", mock_fn)
        result = tool_registry.call("record_user_details", email="test@example.com")
        mock_fn.assert_called_once()
        assert result == {"recorded": "ok"}

    def test_call_rejects_not_allowed_tool(self, tool_registry):
        result = tool_registry.call("some_random_tool", arg="value")
        assert "error" in result
        assert "not allowed" in result["error"]

    def test_allowed_tools_contains_expected(self):
        expected = {"record_user_details", "record_unknown_question"}
        assert expected.issubset(ToolRegistry._ALLOWED_TOOLS)


# =============================================================================
# RATE LIMIT TRACKER TESTS
# =============================================================================


class TestRateLimitTracker:
    def test_can_use_within_limit(self, rate_tracker):
        for _ in range(23):
            rate_tracker.record("openai/gpt-oss-20b")
        assert rate_tracker.can_use("openai/gpt-oss-20b") is True

    def test_can_use_above_limit(self, rate_tracker):
        for _ in range(25):
            rate_tracker.record("openai/gpt-oss-20b")
        assert rate_tracker.can_use("openai/gpt-oss-20b") is False

    def test_can_use_unknown_model(self, rate_tracker):
        assert rate_tracker.can_use("unknown/model") is True

    def test_safety_factor_is_80_percent(self):
        assert _SAFETY_FACTOR == 0.80


# =============================================================================
# PROMPT LOADER TESTS
# =============================================================================


class TestPromptLoader:
    def test_render_me_best_prompt(self):
        path = Path(__file__).parent.parent / "prompts" / "meBest.md"
        result = PromptLoader.render(path)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_user_toxicity_prompt(self):
        path = Path(__file__).parent.parent / "prompts" / "user_toxicity.md"
        result = PromptLoader.render(path, message="test", history=[])
        assert "test" in result


# =============================================================================
# TOOL FUNCTIONS TESTS
# =============================================================================


class TestToolFunctions:
    @patch("mebot.tools._pushover")
    def test_record_user_details_calls_pushover(self, mock_pushover):
        record_user_details(email="test@example.com", name="Test User")
        mock_pushover.assert_called_once()
        assert "test@example.com" in mock_pushover.call_args[0][0]

    @patch("mebot.tools._pushover")
    def test_record_unknown_question_calls_pushover(self, mock_pushover):
        record_unknown_question(question="How to contact?")
        mock_pushover.assert_called_once()

    def test_record_user_details_returns_success(self):
        result = record_user_details(email="test@example.com")
        assert result == {"recorded": "ok"}


# =============================================================================
# UI TESTS
# =============================================================================


class TestUIFunctions:
    def test_build_ui_returns_gr_blocks(self):
        from ui import build_ui
        import gradio as gr
        app = build_ui(lambda msg, hist: "response")
        assert isinstance(app, gr.Blocks)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestPipelineIntegration:
    @patch("mebot.pipelines._llm_gateway")
    def test_orchestrator_completes_conversation(self, mock_gateway):
        def complete_side(role, messages, **kwargs):
            if kwargs.get("raw"):
                return LLMResponse(content="Soy desarrollador senior.", tool_calls=None, finish_reason="stop")
            return json.dumps({"classification": "GOOD", "quality_score": 0.8, "issues": [], "suggestion": ""})

        mock_gateway.complete = MagicMock(side_effect=[
            json.dumps({"classification": "ACCEPTABLE", "toxicity_score": 0.1, "reason": "clean"}),
            LLMResponse(content="Soy desarrollador senior.", tool_calls=None, finish_reason="stop"),
            json.dumps({"classification": "GOOD", "quality_score": 0.8, "issues": [], "suggestion": ""}),
        ])
        orchestrator = PipelineOrchestrator()
        result = orchestrator.chat("Who are you?", [])
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("mebot.pipelines._llm_gateway")
    def test_orchestrator_blocks_toxic_message(self, mock_gateway):
        mock_gateway.complete = MagicMock(return_value=json.dumps({
            "classification": "NOT_ACCEPTABLE", "toxicity_score": 0.9, "reason": "offensive",
        }))
        orchestrator = PipelineOrchestrator()
        result = orchestrator.chat("Bad words", [])
        assert "Lo siento" in result or "no puedo continuar" in result

    @patch("mebot.pipelines._llm_gateway")
    def test_toxicity_pipeline_fail_closed(self, mock_gateway):
        mock_gateway.complete = MagicMock(side_effect=Exception("API Error"))
        pipeline = ToxicityPipeline()
        result = pipeline.evaluate("any message", [])
        assert result["classification"] == "NOT_ACCEPTABLE"
        assert result["toxicity_score"] == 1.0

    @patch("mebot.pipelines._llm_gateway")
    def test_quality_evaluator_fail_safe(self, mock_gateway):
        mock_gateway.complete = MagicMock(side_effect=Exception("API Error"))
        evaluator = QualityEvaluator()
        result = evaluator.evaluate("reply", "message", [])
        assert result["classification"] == "GOOD"

    @patch("mebot.pipelines._llm_gateway")
    def test_pipeline_sanitizes_output(self, mock_gateway):
        def complete_side(role, messages, **kwargs):
            if kwargs.get("raw"):
                return LLMResponse(
                    content="Using Groq with gpt-oss-120b. UUID: 12345678-1234-1234-1234-123456789012",
                    tool_calls=None,
                    finish_reason="stop",
                )
            return json.dumps({"classification": "GOOD", "quality_score": 0.8, "issues": [], "suggestion": ""})

        mock_gateway.complete = MagicMock(side_effect=[
            json.dumps({"classification": "ACCEPTABLE", "toxicity_score": 0.1, "reason": "clean"}),
            LLMResponse(
                content="Using Groq with gpt-oss-120b. UUID: 12345678-1234-1234-1234-123456789012",
                tool_calls=None,
                finish_reason="stop",
            ),
            json.dumps({"classification": "GOOD", "quality_score": 0.8, "issues": [], "suggestion": ""}),
        ])
        orchestrator = PipelineOrchestrator()
        result = orchestrator.chat("What do you use?", [])
        assert "12345678-1234-1234-1234-123456789012" not in result


# =============================================================================
# SECURITY TESTS
# =============================================================================


class TestSecurity:
    def test_sanitizer_removes_infrastructure_keywords(self, sanitizer):
        for kw in ["Groq", "Ollama", "gpt-oss-20b", "nemotron"]:
            result = sanitizer.sanitize(f"Using {kw}")
            assert "[SISTEMA]" in result or kw not in result

    def test_sanitizer_removes_tool_names(self, sanitizer):
        for tool in ["record_user_details", "record_unknown_question"]:
            result = sanitizer.sanitize(f"Called {tool}")
            assert "[HERRAMIENTA INTERNA]" in result or tool not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
