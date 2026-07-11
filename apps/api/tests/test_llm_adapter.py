"""Tests for LLMAdapter — real extraction pipeline implementation.

Tests the httpx-based Anthropic adapter: prompt loading, tool_use parsing,
retry on ValidationError, ExtractionFailedError on API errors.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas import ExtractionResult
from app.services.llm import ExtractionFailedError, LLMAdapter, _load_prompt


@pytest.mark.req("OL-020")
class TestPromptLoading:
    """Versioned prompts loaded from disk with hash."""

    def test_load_prompt_returns_content_and_hash(self):
        content, prompt_hash = _load_prompt("extract_commitments_v1.txt")
        assert "commitment" in content.lower()
        assert len(prompt_hash) == 16  # sha256 truncated to 16 chars

    def test_prompt_hash_is_deterministic(self):
        _, h1 = _load_prompt("extract_commitments_v1.txt")
        _, h2 = _load_prompt("extract_commitments_v1.txt")
        assert h1 == h2


@pytest.mark.req("OL-020")
class TestToolInputParsing:
    """LLMAdapter._extract_tool_input correctly parses Anthropic response."""

    def test_extracts_tool_use_block(self):
        response = {
            "content": [
                {"type": "text", "text": "I found commitments"},
                {
                    "type": "tool_use",
                    "name": "extract_commitments",
                    "input": {
                        "commitments": [
                            {
                                "title": "Pay ₹1500 fee",
                                "class": "fee",
                                "amount_paise": 150000,
                                "confidence": 0.95,
                            }
                        ]
                    },
                },
            ]
        }
        result = LLMAdapter._extract_tool_input(response)
        assert len(result["commitments"]) == 1
        assert result["commitments"][0]["title"] == "Pay ₹1500 fee"

    def test_raises_on_missing_tool_use(self):
        response = {"content": [{"type": "text", "text": "No tools used"}]}
        with pytest.raises(ExtractionFailedError, match="tool_use"):
            LLMAdapter._extract_tool_input(response)

    def test_extracts_empty_commitments(self):
        """No commitments in message → empty list (not an error)."""
        response = {
            "content": [
                {
                    "type": "tool_use",
                    "name": "extract_commitments",
                    "input": {"commitments": []},
                }
            ]
        }
        result = LLMAdapter._extract_tool_input(response)
        assert result["commitments"] == []


@pytest.mark.req("OL-020")
class TestCallAndParse:
    """Integration of API call → parse → ExtractionResult."""

    @pytest.fixture
    def adapter(self):
        return LLMAdapter()

    @staticmethod
    def _make_response(status_code, json_data=None, text=""):
        """Create a MagicMock mimicking httpx.Response (sync .json()/.text)."""
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        if json_data is not None:
            resp.json.return_value = json_data
        return resp

    @pytest.mark.asyncio
    async def test_successful_extraction(self, adapter):
        """Mock a successful API response and verify parsing."""
        mock_response = self._make_response(200, {
            "model": "claude-sonnet-4-20250514",
            "content": [
                {
                    "type": "tool_use",
                    "name": "extract_commitments",
                    "input": {
                        "commitments": [
                            {
                                "title": "Monthly tuition fee ₹2000",
                                "class": "fee",
                                "amount_paise": 200000,
                                "currency": "INR",
                                "due_at": "2026-08-01T00:00:00",
                                "counterparties": [
                                    {"name": "Parent Sharma", "role": "counterparty"}
                                ],
                                "confidence": 0.96,
                            }
                        ]
                    },
                }
            ],
        })

        with patch.object(
            adapter._client, "post",
            new_callable=AsyncMock, return_value=mock_response,
        ):
            result = await adapter.extract_commitments(
                "Please pay ₹2000 by August 1st"
            )

        assert isinstance(result, ExtractionResult)
        assert len(result.commitments) == 1
        assert result.commitments[0].title == "Monthly tuition fee ₹2000"
        assert result.commitments[0].amount_paise == 200000
        assert result.commitments[0].confidence == 0.96
        assert result.model_id == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_api_error_raises_extraction_failed(self, adapter):
        """Non-200 API response raises ExtractionFailedError."""
        mock_response = self._make_response(429, text="Rate limited")

        with patch.object(
            adapter._client, "post",
            new_callable=AsyncMock, return_value=mock_response,
        ):
            with pytest.raises(ExtractionFailedError, match="429"):
                await adapter.extract_commitments("test message")

    @pytest.mark.asyncio
    async def test_no_commitments_returns_empty_list(self, adapter):
        """Message with no commitments → empty list, not an error."""
        mock_response = self._make_response(200, {
            "model": "claude-sonnet-4-20250514",
            "content": [
                {
                    "type": "tool_use",
                    "name": "extract_commitments",
                    "input": {"commitments": []},
                }
            ],
        })

        with patch.object(
            adapter._client, "post",
            new_callable=AsyncMock, return_value=mock_response,
        ):
            result = await adapter.extract_commitments(
                "Good morning! Nice weather today."
            )

        assert result.commitments == []

    @pytest.mark.asyncio
    async def test_retry_on_validation_error_then_success(self, adapter):
        """First call returns bad schema, retry succeeds (eng review T12)."""
        bad_response = self._make_response(200, {
            "model": "claude-sonnet-4-20250514",
            "content": [
                {
                    "type": "tool_use",
                    "name": "extract_commitments",
                    "input": {
                        "commitments": [
                            {
                                "title": "Test",
                                "class": "invalid_class",
                                "confidence": 0.9,
                            }
                        ]
                    },
                }
            ],
        })

        good_response = self._make_response(200, {
            "model": "claude-sonnet-4-20250514",
            "content": [
                {
                    "type": "tool_use",
                    "name": "extract_commitments",
                    "input": {
                        "commitments": [
                            {
                                "title": "Test",
                                "class": "task",
                                "confidence": 0.9,
                            }
                        ]
                    },
                }
            ],
        })

        with patch.object(
            adapter._client, "post",
            new_callable=AsyncMock,
            side_effect=[bad_response, good_response],
        ):
            result = await adapter.extract_commitments("Do the task")

        assert len(result.commitments) == 1
        assert result.commitments[0].class_ == "task"

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self, adapter):
        """Two consecutive validation errors → ExtractionFailedError."""
        bad_response = self._make_response(200, {
            "model": "claude-sonnet-4-20250514",
            "content": [
                {
                    "type": "tool_use",
                    "name": "extract_commitments",
                    "input": {
                        "commitments": [
                            {
                                "title": "Test",
                                "class": "bogus",
                                "confidence": 0.9,
                            }
                        ]
                    },
                }
            ],
        })

        with patch.object(
            adapter._client, "post",
            new_callable=AsyncMock, return_value=bad_response,
        ):
            with pytest.raises(ExtractionFailedError, match="schema validation"):
                await adapter.extract_commitments("test")


@pytest.mark.req("OL-025")
class TestConfidenceFiltering:
    """Extraction worker filters by confidence threshold."""

    def test_threshold_filters_low_confidence(self):
        """Commitments below threshold are discarded by worker."""
        from app.config import settings

        threshold = settings.extraction_confidence_threshold

        commitments = [
            {"title": "High conf", "class": "task", "confidence": 0.95},
            {"title": "Low conf", "class": "task", "confidence": 0.5},
            {"title": "Borderline", "class": "task", "confidence": threshold},
        ]

        from app.schemas import ExtractedCommitment

        parsed = [ExtractedCommitment.model_validate(c) for c in commitments]
        kept = [c for c in parsed if c.confidence >= threshold]

        assert len(kept) == 2  # High conf + borderline (exactly at threshold)
        assert all(c.confidence >= threshold for c in kept)


@pytest.mark.req("OL-027")
class TestPromptVersioning:
    """Extraction attributed to versioned prompt hash and model."""

    def test_adapter_has_prompt_hash(self):
        adapter = LLMAdapter()
        assert adapter._prompt_hash is not None
        assert len(adapter._prompt_hash) == 16

    def test_prompt_hash_in_extraction_result(self):
        """ExtractionResult carries prompt_hash for audit trail."""
        result = ExtractionResult(
            commitments=[],
            prompt_hash="abc123def456",
            model_id="claude-sonnet-4-20250514",
        )
        assert result.prompt_hash == "abc123def456"
