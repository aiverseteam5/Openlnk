"""LLM adapter — single provider interface for extraction.

All LLM calls go through this adapter. Structured outputs → Pydantic.
Provider access through one adapter in services/llm/ (CLAUDE.md).
Provider to be selected after DPDP compliance review (TODOS T-001).
"""

import structlog

from app.schemas import ExtractionResult

logger = structlog.get_logger()


class LLMAdapter:
    """Single LLM provider adapter.

    Pydantic ValidationError handling (eng review T12):
    - On ValidationError: retry once with a clarifying prompt
    - On second failure: raise ExtractionFailedError (visible to user)
    - Never silently swallow a parse error
    """

    async def extract_commitments(
        self,
        text: str,
        *,
        prompt_hash: str,
    ) -> ExtractionResult:
        """Send text to LLM for commitment extraction.

        Returns a Pydantic ExtractionResult parsed from the LLM response.
        Raises ExtractionFailedError if the LLM response cannot be parsed
        after one retry.
        """
        # TODO: implement with httpx call to LLM provider
        # structured output → parse into ExtractionResult
        raise NotImplementedError("LLMAdapter.extract_commitments not yet implemented")


class ExtractionFailedError(Exception):
    """Raised when extraction fails after retries.

    The user sees: 'Extraction failed — create commitment manually.'
    """

    def __init__(self, reason: str, *, original_error: Exception | None = None):
        self.reason = reason
        self.original_error = original_error
        super().__init__(reason)
