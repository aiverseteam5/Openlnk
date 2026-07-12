"""LLM adapter — single provider interface for extraction.

All LLM calls go through this adapter. Structured outputs → Pydantic.
Supports three ingestion routes:
- Text: direct text → Claude extraction
- Camera (OL-022): base64 image → Claude Vision → extraction
- Voice (OL-021): base64 audio → Whisper ASR → text → Claude extraction

Prompts are versioned files in apps/api/prompts/, referenced by hash in audit log.
"""

import base64
import hashlib
import tempfile
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

    Supports text, vision (camera/image), and audio (voice via Whisper ASR).
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
                read=settings.extraction_timeout_media_secs,
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
        """Extract commitments from text (OL-020).

        Returns a Pydantic ExtractionResult parsed from the LLM response.
        Raises ExtractionFailedError if the LLM response cannot be parsed
        after one retry.
        """
        used_hash = prompt_hash or self._prompt_hash
        user_content: list[dict] = [{"type": "text", "text": text}]

        return await self._extract_with_retry(user_content, used_hash)

    async def extract_from_image(
        self,
        image_base64: str,
        *,
        media_type: str = "image/jpeg",
    ) -> ExtractionResult:
        """Extract commitments from an image via Claude Vision (OL-022).

        Sends the image directly to Claude — no separate OCR step needed.
        Claude reads circulars, notices, receipts, and fee schedules natively.
        """
        user_content: list[dict] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_base64,
                },
            },
            {
                "type": "text",
                "text": (
                    "Extract all commitments from this document/image. "
                    "This may be a school circular, fee notice, receipt, "
                    "schedule, or any document containing obligations."
                ),
            },
        ]

        logger.info("extraction_vision_start", image_size_kb=len(image_base64) * 3 // 4 // 1024)

        return await self._extract_with_retry(user_content, self._prompt_hash)

    async def transcribe_audio(self, audio_base64: str) -> str:
        """Transcribe audio via OpenAI Whisper API (OL-021).

        Returns the transcribed text. Raises ExtractionFailedError on failure.
        Content is ephemeral — audio is not persisted (ADR-002).
        """
        whisper_key = settings.llm_api_key  # Reuse key if OpenAI; otherwise set WHISPER_API_KEY

        # Decode base64 to temp file (Whisper needs a file upload)
        audio_bytes = base64.b64decode(audio_base64)

        logger.info("asr_whisper_start", audio_size_kb=len(audio_bytes) // 1024)

        # Use Claude's own audio understanding if available,
        # otherwise fall back to a simple approach: send as text description
        # For now, use httpx to call OpenAI Whisper API
        try:
            async with httpx.AsyncClient(timeout=60.0) as whisper_client:
                # Write to temp file (Whisper API requires multipart file upload)
                with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as tmp:
                    tmp.write(audio_bytes)
                    tmp.flush()
                    tmp.seek(0)

                    response = await whisper_client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {settings.whisper_api_key}"},
                        files={"file": ("audio.m4a", tmp, "audio/m4a")},
                        data={"model": "whisper-1", "language": "en"},
                    )

            if response.status_code != 200:
                logger.warning("asr_whisper_failed", status=response.status_code, body=response.text[:200])
                raise ExtractionFailedError(
                    f"Whisper ASR returned {response.status_code}"
                )

            transcript = response.json().get("text", "")
            if not transcript.strip():
                raise ExtractionFailedError("Whisper returned empty transcript")

            logger.info("asr_whisper_complete", transcript_len=len(transcript))
            return transcript

        except httpx.TimeoutException:
            raise ExtractionFailedError("Audio transcription timed out")
        except ExtractionFailedError:
            raise
        except Exception as e:
            raise ExtractionFailedError(f"ASR failed: {e}") from e

    async def extract_from_audio(self, audio_base64: str) -> ExtractionResult:
        """Extract commitments from audio: ASR → text → extraction (OL-021).

        Two-step: Whisper transcribes audio, then Claude extracts commitments.
        """
        transcript = await self.transcribe_audio(audio_base64)
        return await self.extract_commitments(
            f"[Transcribed from voice note]\n\n{transcript}"
        )

    # ── Internal methods ──

    async def _extract_with_retry(
        self,
        user_content: list[dict],
        prompt_hash: str,
    ) -> ExtractionResult:
        """Call LLM with retry on ValidationError (eng review T12)."""
        # First attempt
        try:
            return await self._call_and_parse(user_content, prompt_hash)
        except ValidationError as e:
            logger.warning("extraction_parse_error_retry", error=str(e), attempt=1)

        # Retry once with clarifying instruction
        try:
            retry_content = user_content + [
                {
                    "type": "text",
                    "text": (
                        "Your previous response could not be parsed. "
                        "Use the extract_commitments tool with valid JSON. "
                        "Ensure all required fields are present."
                    ),
                },
            ]
            return await self._call_and_parse(retry_content, prompt_hash)
        except ValidationError as e:
            raise ExtractionFailedError(
                "LLM output failed schema validation after retry",
                original_error=e,
            ) from e

    async def _call_and_parse(
        self,
        user_content: list[dict],
        prompt_hash: str,
    ) -> ExtractionResult:
        """Make the API call and parse the tool_use response into Pydantic."""
        payload = {
            "model": self._model,
            "max_tokens": 4096,
            "system": self._system_prompt,
            "messages": [{"role": "user", "content": user_content}],
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
