"""Eval harness data models.

Gold = human-labeled ground truth.
Extracted = pipeline output.
MatchResult = per-case comparison.
EvalReport = aggregate precision/recall/trust.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ─── Gold labels (human-annotated ground truth) ───


class GoldCounterparty(BaseModel):
    """A counterparty in the gold label."""

    name: str
    role: str = "counterparty"


class GoldCommitment(BaseModel):
    """A single gold-labeled commitment.

    This is what a correct extraction SHOULD produce for a given message.
    """

    title: str
    class_: str = Field(alias="class")
    amount_paise: int | None = None
    currency: str = "INR"
    due_at: str | None = None  # ISO 8601
    counterparties: list[GoldCounterparty] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class EvalCase(BaseModel):
    """One labeled eval case: a message + its gold commitments.

    If gold_commitments is empty, the message contains NO commitments
    (adversarial case — extraction should return nothing).
    """

    id: str
    message: str
    provenance_kind: str = Field(
        default="message",
        pattern="^(message|voice|camera)$",
    )
    gold_commitments: list[GoldCommitment] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)  # e.g. ["adversarial", "multi-cp"]

    model_config = {"populate_by_name": True}


class EvalDataset(BaseModel):
    """A frozen eval dataset (versioned, immutable per milestone)."""

    version: str  # e.g. "v0"
    frozen_at: str  # ISO 8601
    cases: list[EvalCase]

    @property
    def total_gold(self) -> int:
        return sum(len(c.gold_commitments) for c in self.cases)

    @property
    def adversarial_count(self) -> int:
        return sum(1 for c in self.cases if not c.gold_commitments)

    @property
    def adversarial_pct(self) -> float:
        if not self.cases:
            return 0.0
        return self.adversarial_count / len(self.cases)

    @property
    def multi_cp_count(self) -> int:
        return sum(
            1 for c in self.cases
            if any(len(g.counterparties) > 1 for g in c.gold_commitments)
        )


# ─── Extraction output (mirrors app schemas) ───


class ExtractedCounterparty(BaseModel):
    name: str
    phone_e164: str | None = None
    role: str = "counterparty"


class ExtractedCommitment(BaseModel):
    title: str
    class_: str = Field(alias="class")
    amount_paise: int | None = None
    currency: str = "INR"
    due_at: str | None = None
    counterparties: list[ExtractedCounterparty] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = {"populate_by_name": True}


class ExtractionOutput(BaseModel):
    """Pipeline output for one eval case."""

    case_id: str
    commitments: list[ExtractedCommitment]
    prompt_hash: str
    model_id: str
    latency_ms: float


# ─── Match results ───


class CommitmentMatch(BaseModel):
    """A matched pair: gold ↔ extracted."""

    gold: GoldCommitment
    extracted: ExtractedCommitment
    title_match: bool  # Semantic match (adjudicated)
    due_match: bool  # Within ±30 min or both absent
    class_match: bool
    amount_match: bool


class CaseResult(BaseModel):
    """Per-case eval result."""

    case_id: str
    provenance_kind: str
    true_positives: list[CommitmentMatch] = Field(default_factory=list)
    false_positives: list[ExtractedCommitment] = Field(default_factory=list)
    false_negatives: list[GoldCommitment] = Field(default_factory=list)
    latency_ms: float = 0.0


# ─── Aggregate report ───


class RouteMetrics(BaseModel):
    """Precision/recall for one ingestion route."""

    route: str  # "message", "voice", "camera"
    precision: float
    recall: float
    trust_score: float  # FP weighted 3x
    tp_count: int
    fp_count: int
    fn_count: int
    case_count: int


class EvalReport(BaseModel):
    """Full eval run report — archived per run."""

    dataset_version: str
    run_at: str
    model_id: str
    prompt_hash: str
    overall_precision: float
    overall_recall: float
    overall_trust_score: float
    per_route: list[RouteMetrics]
    total_cases: int
    total_tp: int
    total_fp: int
    total_fn: int
    latency_p50_ms: float
    latency_p95_ms: float
    cost_per_1k_msgs: float | None = None
    confusion_samples: list[CaseResult] = Field(default_factory=list)
    gate_passed: bool  # precision ≥ 0.97 AND recall ≥ 0.85

    @staticmethod
    def precision_bar() -> float:
        return 0.97

    @staticmethod
    def recall_bar() -> float:
        return 0.85
