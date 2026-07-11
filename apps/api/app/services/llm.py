"""LLM adapter — single provider interface for extraction.

All LLM calls go through this adapter. Structured outputs → Pydantic.
Uses httpx to call the Anthropic Messages API with tool_use for structured output.
Prompts are versioned files in apps/api/prompts/, referenced by hash in audit log.
"""

import hashlib
from pathlib import Path

import httpx
import structlog
from pydantic import ValidationError

from app.config import settings
from app.schemas import ExtractedCommitment, ExtractionResult

logger = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

# Tool schema for structured extraction output
_EXTRACTION_TOOL = {
    "name": "extract_commitments",
    "description": (
        "Extract commitments found in the message. "
        "Call this with the list of commitments identified."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "commitments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Clear, concise title of the commitment",
                        },
                        "class": {
                            "type": "string",
                            "enum": ["fee", "schedule", "task", "payment", "custom"],
                            "description": "Commitment class",
                        },
                        "amount_paise": {
                            "type": ["integer", "null"],
                            "description": "Amount in paise. null if not monetary.",
                        },
                        "currency": {
                            "type": "string",
                            "default": "INR",
                        },
                        "due_at": {
                            "type": ["string", "null"],
                            "description": "ISO 8601 datetime string. null if no due date.",
                        },
                        "counterparties": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "phone_e164": {"type": ["string", "null"]},
                                    "role": {
                                        "type": "string",
                                        "enum": ["owner", "counterparty"],
                                    },
                                },
                                "required": ["name", "role"],
                            },
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Extraction confidence. ≥0.85 = unambiguous.",
                        },
                    },
                    "required": ["title", "class", "confidence"],
                },
            },
        },
        "required": ["commitments"],
    },
}


def _load_prompt(name: str) -> tuple[str, str]:
    """Load a prompt file and return (content, sha256 hash).

    Prompt hash is stored in audit_log for provenance (CLAUDE.md).
    """
    path = _PROMPTS_DIR / name
    content = path.read_text(encoding="utf-8")
    prompt_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return content, prompt_hash


class ExtractionFailedError(Exception):
    """Raised when extraction fails after retries.

    The user sees: 'Extraction failed — create commitment manually.'
    """

    def __init__(self, reason: str, *, original_error: Exception | None = None):
        self.reason = reason
        self.original_error = original_error
        super().__init__(reason)


class LLMAdapter:
    """Single LLM provider adapter — Anthropic Messages API via httpx.

    Pydantic ValidationError handling (eng review T12):
    - On ValidationError: retry once with a clarifying prompt
    - On second failure: raise ExtractionFailedError (visible to user)
    - Never silently swallow a parse error
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            headers={
                "x-api-key": settings.llm_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=httpx.Timeout(
                connect=10.0,
                read=settings.extraction_timeout_text_secs,
                write=10.0,
                pool=10.0,
            ),
        )
        self._model = settings.llm_model or "claude-sonnet-4-6"
        self._system_prompt, self._prompt_hash = _load_prompt(
            "extract_commitments_v1.txt"
        )

    async def extract_commitments(
        self,
        text: str,
        *,
        prompt_hash: str | None = None,
    ) -> ExtractionResult:
        """Send text to LLM for commitment extraction.

        Returns a Pydantic ExtractionResult parsed from the LLM response.
        Raises ExtractionFailedError if the LLM response cannot be parsed
        after one retry.
        """
        used_hash = prompt_hash or self._prompt_hash

        # First attempt
        try:
            return await self._call_and_parse(text, used_hash)
        except ValidationError as e:
            logger.warning(
                "extraction_parse_error_retry",
                error=str(e),
                attempt=1,
            )

        # Retry once with clarifying instruction (eng review T12)
        try:
            return await self._call_and_parse(
                text,
                used_hash,
                retry_hint="Your previous response could not be parsed. "
                "Use the extract_commitments tool with valid JSON. "
                "Ensure all required fields are present.",
            )
        except ValidationError as e:
            raise ExtractionFailedError(
                "LLM output failed schema validation after retry",
                original_error=e,
            ) from e

    async def _call_and_parse(
        self,
        text: str,
        prompt_hash: str,
        retry_hint: str | None = None,
    ) -> ExtractionResult:
        """Make the API call and parse the tool_use response into Pydantic."""
        messages = [{"role": "user", "content": text}]
        if retry_hint:
            messages.append({"role": "assistant", "content": retry_hint})
            messages.append({"role": "user", "content": text})

        payload = {
            "model": self._model,
            "max_tokens": 4096,
            "system": self._system_prompt,
            "messages": messages,
            "tools": [_EXTRACTION_TOOL],
            "tool_choice": {"type": "tool", "name": "extract_commitments"},
        }

        response = await self._client.post("/v1/messages", json=payload)

        if response.status_code != 200:
            error_body = response.text
            logger.error(
                "llm_api_error",
                status=response.status_code,
                body=error_body[:500],
            )
            raise ExtractionFailedError(
                f"LLM API returned {response.status_code}",
            )

        data = response.json()
        model_id = data.get("model", self._model)

        # Extract the tool_use block
        tool_input = self._extract_tool_input(data)

        # Parse each commitment through Pydantic
        raw_commitments = tool_input.get("commitments", [])
        commitments = [
            ExtractedCommitment.model_validate(c) for c in raw_commitments
        ]

        logger.info(
            "extraction_complete",
            commitments_count=len(commitments),
            model_id=model_id,
            prompt_hash=prompt_hash,
        )

        return ExtractionResult(
            commitments=commitments,
            prompt_hash=prompt_hash,
            model_id=model_id,
        )

    @staticmethod
    def _extract_tool_input(response_data: dict) -> dict:
        """Pull the tool input from the Anthropic Messages API response."""
        for block in response_data.get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "extract_commitments":
                return block.get("input", {})  # type: ignore[no-any-return]
        raise ExtractionFailedError(
            "LLM response did not contain extract_commitments tool_use block"
        )

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()
