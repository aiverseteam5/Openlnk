"""Pydantic v2 schemas — request/response models + extraction output.

All LLM outputs are parsed into these Pydantic models before touching services.
Zod validation at runtime boundaries for TS clients (packages/schema).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ─── Commitment schemas ───


class CommitmentCreate(BaseModel):
    """Create a new commitment."""

    context_id: UUID
    owner_id: UUID
    counterparty_id: UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    class_: str = Field(alias="class", pattern="^(fee|schedule|task|payment|custom)$")
    amount_paise: int | None = None
    currency: str = "INR"
    due_at: datetime | None = None
    provenance_kind: str | None = Field(default=None, pattern="^(message|voice|camera|manual)$")
    provenance_ref: str | None = None

    model_config = {"populate_by_name": True}


class CommitmentResponse(BaseModel):
    """Commitment as returned by the API."""

    id: UUID
    context_id: UUID
    owner_id: UUID
    counterparty_id: UUID | None
    title: str
    class_: str = Field(alias="class")
    amount_paise: int | None
    currency: str
    due_at: datetime | None
    state: str
    version: int
    at_risk: bool  # Computed at query time, never stored
    provenance_kind: str | None
    extraction_confidence: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True, "from_attributes": True}


class CursorPage(BaseModel):
    """Cursor-paginated response wrapper (CLAUDE.md: cursor pagination only)."""

    items: list[CommitmentResponse]
    next_cursor: str | None = None
    has_more: bool = False


class CommitmentAmend(BaseModel):
    """Amend a commitment's title, due date, or amount (OL-002a).

    All fields optional (partial update). Version is required for
    optimistic concurrency.
    """

    title: str | None = Field(default=None, min_length=1, max_length=500)
    due_at: datetime | None = None
    amount_paise: int | None = None
    version: int = Field(description="Expected current version for optimistic concurrency")


class CommitmentStateTransition(BaseModel):
    """Request to transition commitment state."""

    new_state: str = Field(pattern="^(accepted|in_progress|done|broken|cancelled)$")
    version: int = Field(description="Expected current version for optimistic concurrency")


# ─── Extraction schemas ───


class ExtractedPrincipal(BaseModel):
    """A principal identified by the extraction pipeline."""

    name: str
    phone_e164: str | None = None
    role: str = Field(pattern="^(owner|counterparty)$")


class ExtractedCommitment(BaseModel):
    """A commitment extracted from a message by the LLM.

    This is the Pydantic model that LLM structured outputs are parsed into.
    Parsed BEFORE touching services (CLAUDE.md).
    """

    title: str
    class_: str = Field(alias="class", pattern="^(fee|schedule|task|payment|custom)$")
    amount_paise: int | None = None
    currency: str = "INR"
    due_at: str | None = None  # ISO 8601 string, parsed to datetime in service
    counterparties: list[ExtractedPrincipal] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = {"populate_by_name": True}


class ExtractionResult(BaseModel):
    """Full extraction result from one message."""

    commitments: list[ExtractedCommitment]
    prompt_hash: str
    model_id: str


# ─── Sync / delta schemas (OL-003) ───


class DeltaEvent(BaseModel):
    """A sync delta event broadcast over WebSocket (OL-003)."""

    event: str
    context_id: str
    subject_id: str
    seq: int
    data: dict


class CorrectionAction(BaseModel):
    """User correction/rejection of an extracted commitment (OL-026).

    Users can reject or edit any extraction in <= 2 taps.
    Corrections feed into the eval-candidate queue (OL-090).
    """

    action: str = Field(pattern="^(reject|edit)$")
    edits: dict | None = None


class AuditEntryResponse(BaseModel):
    """Single audit log entry for commitment history (OL-004)."""

    id: int
    at: datetime
    actor_kind: str
    event: str
    detail: dict

    model_config = {"from_attributes": True}


class ExtractionRequest(BaseModel):
    """Request to extract commitments from text, voice, or camera input.

    Supports three ingestion routes (OL-020, OL-021, OL-022):
    - text: direct text content (paste from WhatsApp, etc.)
    - voice: base64-encoded audio for ASR → extraction
    - camera: base64-encoded image for vision → extraction

    message_id/thread_id are optional — used when extracting from
    an existing message in the DB. For direct input, use text/audio/image.
    """

    message_id: UUID | None = None
    thread_id: UUID | None = None
    text: str | None = None
    audio_base64: str | None = None
    image_base64: str | None = None
    provenance_kind: str = Field(default="message", pattern="^(message|voice|camera)$")


class ExtractionResponse(BaseModel):
    """Accepted response for async extraction."""

    job_id: str
    status: str = "queued"
