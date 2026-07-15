"""Tests for the daily brief summary — AI-generated commitment insights.

Tests the LLMAdapter.generate_brief_summary fallback logic and
the brief prompt loading.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm import LLMAdapter, _load_prompt


@pytest.mark.req("OL-064")
class TestDailyBriefPrompt:
    """daily_brief_v1.txt loads correctly."""

    def test_load_brief_prompt(self):
        content, prompt_hash = _load_prompt("daily_brief_v1.txt")
        assert "daily brief" in content.lower()
        assert len(prompt_hash) == 16

    def test_brief_prompt_hash_deterministic(self):
        _, h1 = _load_prompt("daily_brief_v1.txt")
        _, h2 = _load_prompt("daily_brief_v1.txt")
        assert h1 == h2


@pytest.mark.req("OL-064")
class TestFallbackBrief:
    """Static fallback when LLM is unavailable."""

    def test_fallback_no_commitments(self):
        result = LLMAdapter._fallback_brief(at_risk=0, due_today=0, total_active=0)
        assert "clear day" in result.lower()

    def test_fallback_at_risk(self):
        result = LLMAdapter._fallback_brief(at_risk=3, due_today=1, total_active=5)
        assert "3" in result
        assert "at risk" in result.lower()

    def test_fallback_due_today_only(self):
        result = LLMAdapter._fallback_brief(at_risk=0, due_today=2, total_active=4)
        assert "2" in result
        assert "due today" in result.lower()

    def test_fallback_nothing_urgent(self):
        result = LLMAdapter._fallback_brief(at_risk=0, due_today=0, total_active=7)
        assert "7" in result
        assert "nothing urgent" in result.lower()


@pytest.mark.req("OL-064")
class TestGenerateBriefSummary:
    """LLMAdapter.generate_brief_summary handles success and failure."""

    @pytest.mark.asyncio
    async def test_returns_summary_on_success(self):
        adapter = LLMAdapter.__new__(LLMAdapter)
        adapter._model = "test-model"
        adapter._client = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {"type": "text", "text": "2 commitments at risk today. 1 due by end of day."}
            ],
            "model": "test-model",
        }
        adapter._client.post = AsyncMock(return_value=mock_response)

        result = await adapter.generate_brief_summary(
            at_risk=2, due_today=1, proposed=0, done_today=0, total_active=5,
        )
        assert "at risk" in result.lower()
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_falls_back_on_api_error(self):
        adapter = LLMAdapter.__new__(LLMAdapter)
        adapter._model = "test-model"
        adapter._client = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        adapter._client.post = AsyncMock(return_value=mock_response)

        result = await adapter.generate_brief_summary(
            at_risk=1, due_today=0, proposed=0, done_today=0, total_active=3,
        )
        # Falls back to static summary
        assert "1" in result
        assert "at risk" in result.lower()

    @pytest.mark.asyncio
    async def test_falls_back_on_exception(self):
        adapter = LLMAdapter.__new__(LLMAdapter)
        adapter._model = "test-model"
        adapter._client = MagicMock()
        adapter._client.post = AsyncMock(side_effect=Exception("timeout"))

        result = await adapter.generate_brief_summary(
            at_risk=0, due_today=0, proposed=0, done_today=0, total_active=0,
        )
        assert "clear day" in result.lower()

    @pytest.mark.asyncio
    async def test_falls_back_on_empty_response(self):
        adapter = LLMAdapter.__new__(LLMAdapter)
        adapter._model = "test-model"
        adapter._client = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": []}
        adapter._client.post = AsyncMock(return_value=mock_response)

        result = await adapter.generate_brief_summary(
            at_risk=0, due_today=3, proposed=0, done_today=0, total_active=5,
        )
        # Falls back to static
        assert "3" in result
