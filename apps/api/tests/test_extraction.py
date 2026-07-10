"""Tests for extraction engine requirements OL-020..OL-029.

Unit tests: schema validation, extraction pipeline structure.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    ExtractedCommitment,
    ExtractedPrincipal,
    ExtractionRequest,
    ExtractionResponse,
    ExtractionResult,
)
from app.services.llm import ExtractionFailedError, LLMAdapter


@pytest.mark.req("OL-005")
class TestProvenance:
    """Every extracted commitment links to provenance source."""

    def test_extraction_request_has_message_id(self):
        req = ExtractionRequest(message_id=uuid4(), thread_id=uuid4())
        assert req.message_id is not None
        assert req.thread_id is not None


@pytest.mark.req("OL-027")
class TestPromptHashTracking:
    """Extraction attributed to versioned prompt hash and model identifier."""

    def test_extraction_result_has_prompt_hash(self):
        result = ExtractionResult(
            commitments=[],
            prompt_hash="sha256:abc123",
            model_id="claude-sonnet-4-20250514",
        )
        assert result.prompt_hash == "sha256:abc123"
        assert result.model_id == "claude-sonnet-4-20250514"


@pytest.mark.req("OL-029")
class TestStructuredOutputs:
    """Extraction uses Pydantic-validated structured outputs."""

    def test_extracted_commitment_schema(self):
        ec = ExtractedCommitment(
            title="Monthly fee ₹1500",
            confidence=0.95,
            amount_paise=150000,
            counterparties=[ExtractedPrincipal(name="Parent A", role="counterparty")],
            **{"class": "fee"},
        )
        assert ec.title == "Monthly fee ₹1500"
        assert ec.confidence == 0.95
        assert ec.amount_paise == 150000

    def test_extracted_commitment_rejects_invalid_class(self):
        with pytest.raises(ValidationError):
            ExtractedCommitment(
                title="Test",
                confidence=0.9,
                **{"class": "invalid"},
            )

    def test_extracted_commitment_rejects_out_of_range_confidence(self):
        with pytest.raises(ValidationError):
            ExtractedCommitment(
                title="Test",
                confidence=1.5,
                **{"class": "task"},
            )

    def test_extracted_commitment_rejects_negative_confidence(self):
        with pytest.raises(ValidationError):
            ExtractedCommitment(
                title="Test",
                confidence=-0.1,
                **{"class": "task"},
            )

    def test_extraction_result_contains_commitments_list(self):
        result = ExtractionResult(
            commitments=[
                ExtractedCommitment(
                    title="Fee",
                    confidence=0.98,
                    amount_paise=100000,
                    **{"class": "fee"},
                )
            ],
            prompt_hash="sha256:test",
            model_id="test-model",
        )
        assert len(result.commitments) == 1

    def test_extraction_response_is_async(self):
        """Extraction returns 202 with job_id (async processing)."""
        resp = ExtractionResponse(job_id="job-123", status="queued")
        assert resp.status == "queued"
        assert resp.job_id == "job-123"

    def test_llm_adapter_exists(self):
        """LLMAdapter class exists with extract_commitments method."""
        adapter = LLMAdapter()
        assert hasattr(adapter, "extract_commitments")

    def test_extraction_failed_error(self):
        """ExtractionFailedError carries reason."""
        err = ExtractionFailedError("parse_error", original_error=ValueError("bad json"))
        assert err.reason == "parse_error"
        assert isinstance(err.original_error, ValueError)


@pytest.mark.req("OL-029b")
class TestGroupExtraction:
    """Extraction output includes counterparties list."""

    def test_extracted_commitment_has_counterparties(self):
        ec = ExtractedCommitment(
            title="Group task",
            confidence=0.92,
            counterparties=[
                ExtractedPrincipal(name="Alice", role="counterparty"),
                ExtractedPrincipal(name="Bob", role="counterparty"),
            ],
            **{"class": "task"},
        )
        assert len(ec.counterparties) == 2
        assert ec.counterparties[0].name == "Alice"
        assert ec.counterparties[1].role == "counterparty"

    def test_extracted_principal_roles(self):
        """ExtractedPrincipal accepts owner and counterparty roles."""
        p1 = ExtractedPrincipal(name="Owner", role="owner")
        p2 = ExtractedPrincipal(name="CP", role="counterparty")
        assert p1.role == "owner"
        assert p2.role == "counterparty"

    def test_extracted_principal_rejects_invalid_role(self):
        with pytest.raises(ValidationError):
            ExtractedPrincipal(name="Bad", role="invalid")
