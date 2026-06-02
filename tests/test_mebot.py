# =============================================================================
# tests/test_mebot.py — Tests for Mebot
# =============================================================================
"""Unit and integration tests for Mebot CV chatbot."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import mebot
from mebot.pipelines import (
    AgentPipeline,
    AgentResponse,
    InputGuardPipeline,
    PipelineOrchestrator,
    QualityEvaluator,
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
from mebot.prompt_loader import PromptLoader
from mebot.types import InputGuardResult


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sanitizer():
    return OutputSanitizer()


@pytest.fixture
def tool_registry():
    return ToolRegistry()


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
# PROMPT LOADER TESTS
# =============================================================================


class TestPromptLoader:
    def test_render_me_best_prompt(self):
        path = Path(__file__).parent.parent / "prompts" / "meBest.md"
        result = PromptLoader.render(path)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_input_guard_prompt(self):
        path = Path(__file__).parent.parent / "prompts" / "input_guard.md"
        result = PromptLoader.render(path, message="test", history=[])
        assert "test" in result


# =============================================================================
# TOOL FUNCTIONS TESTS
# =============================================================================


class TestToolFunctions:
    def test_record_user_details_returns_success(self):
        result = record_user_details(email="test@example.com", name="Test User")
        assert result == {"recorded": "ok"}

    def test_record_unknown_question_returns_success(self):
        result = record_unknown_question(question="How to contact?")
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
# INPUT GUARD TESTS
# =============================================================================


class TestInputGuardPipeline:
    @patch("mebot.pipelines._llm_gateway")
    def test_allows_on_topic_message(self, mock_gateway):
        mock_gateway.complete = MagicMock(return_value=json.dumps({
            "topic": "ACCEPTABLE",
            "topic_confidence": 0.9,
            "toxicity": "ACCEPTABLE",
            "toxicity_score": 0.1,
            "reason": "ok",
            "suggested_redirect": "",
        }))
        pipeline = InputGuardPipeline()
        allowed, msg, result = pipeline.evaluate("¿Cuántos años de experiencia tiene Ángel?", [])
        assert allowed is True
        assert msg == ""

    @patch("mebot.pipelines._llm_gateway")
    def test_blocks_off_topic_with_high_confidence(self, mock_gateway):
        mock_gateway.complete = MagicMock(return_value=json.dumps({
            "topic": "OFF_TOPIC",
            "topic_confidence": 0.8,
            "toxicity": "ACCEPTABLE",
            "toxicity_score": 0.1,
            "reason": "pregunta de matemáticas",
            "suggested_redirect": "Solo respondo sobre el perfil de Ángel.",
        }))
        pipeline = InputGuardPipeline()
        allowed, msg, result = pipeline.evaluate("¿Cuánto es 2+2?", [])
        assert allowed is False
        assert msg != ""

    @patch("mebot.pipelines._llm_gateway")
    def test_allows_off_topic_with_low_confidence(self, mock_gateway):
        mock_gateway.complete = MagicMock(return_value=json.dumps({
            "topic": "OFF_TOPIC",
            "topic_confidence": 0.3,
            "toxicity": "ACCEPTABLE",
            "toxicity_score": 0.1,
            "reason": "dudoso",
            "suggested_redirect": "",
        }))
        pipeline = InputGuardPipeline()
        allowed, _, _ = pipeline.evaluate("¿Algo sobre IA?", [])
        assert allowed is True

    @patch("mebot.pipelines._llm_gateway")
    def test_blocks_toxic_message(self, mock_gateway):
        mock_gateway.complete = MagicMock(return_value=json.dumps({
            "topic": "ACCEPTABLE",
            "topic_confidence": 0.9,
            "toxicity": "NOT_ACCEPTABLE",
            "toxicity_score": 0.9,
            "reason": "lenguaje ofensivo",
            "suggested_redirect": "",
        }))
        pipeline = InputGuardPipeline()
        allowed, msg, _ = pipeline.evaluate("mensaje ofensivo", [])
        assert allowed is False
        assert "Lo siento" in msg

    @patch("mebot.pipelines._llm_gateway")
    def test_fail_closed_on_exception(self, mock_gateway):
        mock_gateway.complete = MagicMock(side_effect=Exception("Network error"))
        pipeline = InputGuardPipeline()
        allowed, _, result = pipeline.evaluate("any message", [])
        assert allowed is False
        assert result["toxicity_score"] == 1.0

    @patch("mebot.pipelines._llm_gateway")
    def test_fail_open_on_invalid_json(self, mock_gateway):
        mock_gateway.complete = MagicMock(return_value="not valid json at all <<<")
        pipeline = InputGuardPipeline()
        allowed, _, _ = pipeline.evaluate("any message", [])
        assert allowed is True


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestPipelineIntegration:
    @patch("mebot.pipelines._llm_gateway")
    def test_orchestrator_completes_conversation(self, mock_gateway):
        mock_gateway.complete = MagicMock(side_effect=[
            json.dumps({
                "topic": "ACCEPTABLE", "topic_confidence": 0.9,
                "toxicity": "ACCEPTABLE", "toxicity_score": 0.1,
                "reason": "clean", "suggested_redirect": "",
            }),
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
            "topic": "ACCEPTABLE", "topic_confidence": 0.9,
            "toxicity": "NOT_ACCEPTABLE", "toxicity_score": 0.9,
            "reason": "offensive", "suggested_redirect": "",
        }))
        orchestrator = PipelineOrchestrator()
        result = orchestrator.chat("Bad words", [])
        assert "Lo siento" in result or "no puedo continuar" in result

    @patch("mebot.pipelines._llm_gateway")
    def test_input_guard_fail_closed(self, mock_gateway):
        mock_gateway.complete = MagicMock(side_effect=Exception("API Error"))
        pipeline = InputGuardPipeline()
        allowed, _, result = pipeline.evaluate("any message", [])
        assert allowed is False
        assert result["toxicity_score"] == 1.0

    @patch("mebot.pipelines._llm_gateway")
    def test_quality_evaluator_fail_safe(self, mock_gateway):
        mock_gateway.complete = MagicMock(side_effect=Exception("API Error"))
        evaluator = QualityEvaluator()
        result = evaluator.evaluate("reply", "message", [])
        assert result["classification"] == "GOOD"

    @patch("mebot.pipelines._llm_gateway")
    def test_pipeline_sanitizes_output(self, mock_gateway):
        mock_gateway.complete = MagicMock(side_effect=[
            json.dumps({
                "topic": "ACCEPTABLE", "topic_confidence": 0.9,
                "toxicity": "ACCEPTABLE", "toxicity_score": 0.1,
                "reason": "clean", "suggested_redirect": "",
            }),
            LLMResponse(
                content="UUID: 12345678-1234-1234-1234-123456789012",
                tool_calls=None,
                finish_reason="stop",
            ),
            json.dumps({"classification": "GOOD", "quality_score": 0.8, "issues": [], "suggestion": ""}),
        ])
        orchestrator = PipelineOrchestrator()
        result = orchestrator.chat("What do you use?", [])
        assert "12345678-1234-1234-1234-123456789012" not in result

    @patch("mebot.pipelines._llm_gateway")
    def test_orchestrator_blocks_off_topic(self, mock_gateway):
        mock_gateway.complete = MagicMock(return_value=json.dumps({
            "topic": "OFF_TOPIC", "topic_confidence": 0.9,
            "toxicity": "ACCEPTABLE", "toxicity_score": 0.1,
            "reason": "matemáticas", "suggested_redirect": "Solo respondo sobre Ángel.",
        }))
        orchestrator = PipelineOrchestrator()
        result = orchestrator.chat("¿Cuánto es 2+2?", [])
        assert "Ángel" in result or "Solo" in result


# =============================================================================
# SECURITY TESTS
# =============================================================================


class TestSecurity:
    def test_sanitizer_removes_infrastructure_keywords(self, sanitizer):
        for kw in ["Ollama", "gpt-oss-20b", "nemotron"]:
            result = sanitizer.sanitize(f"Using {kw}")
            assert "[SISTEMA]" in result or kw not in result

    def test_sanitizer_removes_tool_names(self, sanitizer):
        for tool in ["record_user_details", "record_unknown_question"]:
            result = sanitizer.sanitize(f"Called {tool}")
            assert "[HERRAMIENTA INTERNA]" in result or tool not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
