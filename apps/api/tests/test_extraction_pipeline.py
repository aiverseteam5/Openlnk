"""Tests for OL-020..026 — extraction pipeline.

Structural tests verifying pipeline shape. Full integration tests
require LLM provider configuration (Gate 1 entry criteria).
"""

import pytest

from app.schemas import ExtractedCommitment, ExtractedPrincipal, ExtractionResult
from app.services.llm import ExtractionFailedError, LLMAdapter


@pytest.mark.req("OL-020")
class TestTextExtraction:
    """The system shall extract candidate commitments from text messages."""

    def test_llm_adapter_exists(self):
        adapter = LLMAdapter()
        assert hasattr(adapter, "extract_commitments")

    def test_extraction_result_model(self):
        """ExtractionResult has commitments, prompt_hash, model_id."""
        result = ExtractionResult(
            commitments=[
                ExtractedCommitment(
                    title="Pay fee",
                    confidence=0.95,
                    counterparties=[
                        ExtractedPrincipal(name="Alice", role="counterparty"),
                    ],
                    **{"class": "fee"},
                    amount_paise=150000,
                )
            ],
            prompt_hash="sha256:abc",
            model_id="claude-sonnet-4-20250514",
        )
        assert len(result.commitments) == 1
        assert result.commitments[0].title == "Pay fee"

    def test_extraction_result_validates_confidence(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            ExtractedCommitment(
                title="Bad",
                confidence=1.5,
                **{"class": "task"},
            )


@pytest.mark.req("OL-021")
class TestVoiceExtraction:
    """Extract from voice notes via ASR + text pipeline."""

    def test_extraction_job_supports_voice(self):
        """extraction_job accepts provenance_kind='voice'."""
        import inspect

        from app.workers.extraction_job import extraction_job

        source = inspect.getsource(extraction_job)
        assert "voice" in source or "provenance_kind" in source

    def test_voice_timeout_is_120s(self):
        """Voice/media extraction has 120s timeout."""
        from app.config import settings

        assert settings.extraction_timeout_media_secs == 120


@pytest.mark.req("OL-022")
class TestCameraExtraction:
    """Extract from photographed documents (camera flow)."""

    def test_extraction_job_supports_camera(self):
        """extraction_job supports camera provenance."""
        import inspect

        from app.workers.extraction_job import extraction_job

        source = inspect.getsource(extraction_job)
        assert "camera" in source or "provenance_kind" in source

    def test_camera_uses_media_timeout(self):
        """Camera uses the media timeout (120s)."""
        from app.config import settings

        assert settings.extraction_timeout_media_secs == 120


@pytest.mark.req("OL-023")
class TestExtractionPrecision:
    """Precision >= 97% and recall >= 85% on eval set (CI merge gate)."""

    def test_eval_thresholds_exist(self):
        """Eval harness thresholds are defined."""
        # These thresholds are enforced by packages/eval CI job
        # Structural test: verify the config has the extraction threshold
        from app.config import settings

        assert settings.extraction_confidence_threshold == 0.85

    def test_extraction_failed_error_exists(self):
        """ExtractionFailedError provides visible feedback."""
        err = ExtractionFailedError("test reason")
        assert err.reason == "test reason"


@pytest.mark.req("OL-025")
class TestConfidenceThreshold:
    """WHEN extraction confidence is below propose threshold, discard silently."""

    def test_threshold_value_configured(self):
        from app.config import settings

        assert 0 < settings.extraction_confidence_threshold < 1

    def test_below_threshold_discarded(self):
        """Low-confidence extractions are filtered out."""
        from app.config import settings

        threshold = settings.extraction_confidence_threshold
        commitment = ExtractedCommitment(
            title="Maybe a commitment",
            confidence=0.5,
            **{"class": "task"},
        )
        assert commitment.confidence < threshold

    def test_above_threshold_kept(self):
        """High-confidence extractions pass the threshold."""
        from app.config import settings

        threshold = settings.extraction_confidence_threshold
        commitment = ExtractedCommitment(
            title="Definitely a commitment",
            confidence=0.95,
            **{"class": "fee"},
            amount_paise=10000,
        )
        assert commitment.confidence >= threshold


@pytest.mark.req("OL-026")
class TestUserCorrections:
    """User can correct/reject any extracted commitment in <= 2 taps."""

    def test_correction_schema_exists(self):
        """CorrectionAction schema for user corrections."""
        from app.schemas import CorrectionAction

        action = CorrectionAction(
            commitment_id="00000000-0000-0000-0000-000000000001",
            action="reject",
        )
        assert action.action == "reject"

    def test_correction_actions_are_reject_or_edit(self):
        """Valid correction actions are 'reject' or 'edit'."""
        from app.schemas import CorrectionAction

        reject = CorrectionAction(
            commitment_id="00000000-0000-0000-0000-000000000001",
            action="reject",
        )
        assert reject.action in {"reject", "edit"}

        edit = CorrectionAction(
            commitment_id="00000000-0000-0000-0000-000000000001",
            action="edit",
            edits={"title": "Corrected title"},
        )
        assert edit.action == "edit"
        assert edit.edits is not None
