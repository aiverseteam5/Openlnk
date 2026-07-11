"""Tests for eval scorer — matching, precision, recall, trust score."""

import pytest

from eval_harness.models import (
    CaseResult,
    EvalCase,
    EvalDataset,
    ExtractedCommitment,
    ExtractionOutput,
    GoldCommitment,
    GoldCounterparty,
    RouteMetrics,
)
from eval_harness.scorer import (
    _due_dates_match,
    _titles_match,
    build_report,
    compute_metrics,
    score_case,
)


# ─── Title matching ───


class TestTitleMatching:
    def test_exact_match(self):
        assert _titles_match("Pay tuition fee", "Pay tuition fee")

    def test_case_insensitive(self):
        assert _titles_match("Pay Tuition Fee", "pay tuition fee")

    def test_whitespace_normalized(self):
        assert _titles_match("  Pay   fee  ", "Pay fee")

    def test_partial_overlap(self):
        assert _titles_match("Pay fee", "Pay tuition fee by Friday")

    def test_no_match(self):
        assert not _titles_match("Pay fee", "Pick up kids from school")

    def test_empty_gold(self):
        assert not _titles_match("", "Something")

    def test_abbreviation_expansion(self):
        assert _titles_match(
            "Parent-teacher meeting Thursday 5pm",
            "PTM proposed for Thursday at 5:00 PM",
        )

    def test_currency_normalization(self):
        assert _titles_match("Pay fee ₹500", "Pay fee Rs 500")

    def test_time_format_normalization(self):
        assert _titles_match("Class at 5pm", "Class at 5:00 PM")

    def test_plural_stemming(self):
        assert _titles_match(
            "Call parents with unpaid fees by Friday",
            "Personally call each parent whose fee payment is pending by Friday",
        )


# ─── Due date matching ───


class TestDueDateMatching:
    def test_both_none(self):
        assert _due_dates_match(None, None)

    def test_one_none(self):
        assert not _due_dates_match("2026-07-15T00:00:00", None)
        assert not _due_dates_match(None, "2026-07-15T00:00:00")

    def test_exact_match(self):
        assert _due_dates_match("2026-07-15T17:00:00", "2026-07-15T17:00:00")

    def test_within_tolerance(self):
        assert _due_dates_match("2026-07-15T17:00:00", "2026-07-15T17:25:00")

    def test_outside_tolerance(self):
        assert not _due_dates_match("2026-07-15T17:00:00", "2026-07-15T18:00:00")

    def test_invalid_dates(self):
        assert not _due_dates_match("not-a-date", "2026-07-15T17:00:00")


# ─── Case scoring ───


class TestScoreCase:
    def test_perfect_match(self):
        case = EvalCase(
            id="test-1",
            message="Pay fee Rs 1000",
            gold_commitments=[
                GoldCommitment(title="Pay fee Rs 1000", **{"class": "fee"}, amount_paise=100000),
            ],
        )
        output = ExtractionOutput(
            case_id="test-1",
            commitments=[
                ExtractedCommitment(
                    title="Pay fee Rs 1000",
                    confidence=0.95,
                    amount_paise=100000,
                    **{"class": "fee"},
                ),
            ],
            prompt_hash="test",
            model_id="test",
            latency_ms=100,
        )
        result = score_case(case, output)
        assert len(result.true_positives) == 1
        assert len(result.false_positives) == 0
        assert len(result.false_negatives) == 0

    def test_false_positive(self):
        """Extraction invents a commitment that doesn't exist."""
        case = EvalCase(
            id="test-2",
            message="Good morning!",
            gold_commitments=[],
        )
        output = ExtractionOutput(
            case_id="test-2",
            commitments=[
                ExtractedCommitment(
                    title="Morning greeting commitment",
                    confidence=0.5,
                    **{"class": "custom"},
                ),
            ],
            prompt_hash="test",
            model_id="test",
            latency_ms=100,
        )
        result = score_case(case, output)
        assert len(result.true_positives) == 0
        assert len(result.false_positives) == 1
        assert len(result.false_negatives) == 0

    def test_false_negative(self):
        """Extraction misses a real commitment."""
        case = EvalCase(
            id="test-3",
            message="Pay Rs 500 by Friday",
            gold_commitments=[
                GoldCommitment(title="Pay Rs 500", **{"class": "fee"}, amount_paise=50000),
            ],
        )
        output = ExtractionOutput(
            case_id="test-3",
            commitments=[],
            prompt_hash="test",
            model_id="test",
            latency_ms=100,
        )
        result = score_case(case, output)
        assert len(result.true_positives) == 0
        assert len(result.false_positives) == 0
        assert len(result.false_negatives) == 1

    def test_multiple_commitments(self):
        """Message with two commitments, both extracted correctly."""
        case = EvalCase(
            id="test-4",
            message="Pay fee Rs 2000 and class at 5pm",
            gold_commitments=[
                GoldCommitment(title="Pay fee Rs 2000", **{"class": "fee"}, amount_paise=200000),
                GoldCommitment(title="Class at 5pm", **{"class": "schedule"}),
            ],
        )
        output = ExtractionOutput(
            case_id="test-4",
            commitments=[
                ExtractedCommitment(
                    title="Pay fee Rs 2000", confidence=0.95,
                    amount_paise=200000, **{"class": "fee"},
                ),
                ExtractedCommitment(
                    title="Class scheduled at 5pm", confidence=0.9,
                    **{"class": "schedule"},
                ),
            ],
            prompt_hash="test",
            model_id="test",
            latency_ms=100,
        )
        result = score_case(case, output)
        assert len(result.true_positives) == 2
        assert len(result.false_positives) == 0
        assert len(result.false_negatives) == 0

    def test_adversarial_correct_empty(self):
        """Adversarial case: no commitments, extraction returns nothing."""
        case = EvalCase(
            id="test-5",
            message="We should meet sometime",
            gold_commitments=[],
            tags=["adversarial"],
        )
        output = ExtractionOutput(
            case_id="test-5",
            commitments=[],
            prompt_hash="test",
            model_id="test",
            latency_ms=100,
        )
        result = score_case(case, output)
        assert len(result.true_positives) == 0
        assert len(result.false_positives) == 0
        assert len(result.false_negatives) == 0


# ─── Metrics computation ───


class TestComputeMetrics:
    def _make_result(self, tp=0, fp=0, fn=0):
        result = CaseResult(case_id="m", provenance_kind="message")
        for _ in range(tp):
            result.true_positives.append(
                pytest.importorskip("eval_harness.models").CommitmentMatch(
                    gold=GoldCommitment(title="g", **{"class": "task"}),
                    extracted=ExtractedCommitment(
                        title="e", confidence=0.9, **{"class": "task"},
                    ),
                    title_match=True,
                    due_match=True,
                    class_match=True,
                    amount_match=True,
                )
            )
        for _ in range(fp):
            result.false_positives.append(
                ExtractedCommitment(title="fp", confidence=0.5, **{"class": "task"})
            )
        for _ in range(fn):
            result.false_negatives.append(
                GoldCommitment(title="fn", **{"class": "task"})
            )
        return result

    def test_perfect_precision_recall(self):
        results = [self._make_result(tp=5, fp=0, fn=0)]
        m = compute_metrics(results)
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.trust_score == 1.0

    def test_precision_with_false_positives(self):
        results = [self._make_result(tp=9, fp=1, fn=0)]
        m = compute_metrics(results)
        assert m.precision == pytest.approx(0.9)
        assert m.recall == 1.0
        # Trust score: 9 / (9 + 3*1) = 9/12 = 0.75
        assert m.trust_score == pytest.approx(0.75)

    def test_recall_with_false_negatives(self):
        results = [self._make_result(tp=8, fp=0, fn=2)]
        m = compute_metrics(results)
        assert m.precision == 1.0
        assert m.recall == pytest.approx(0.8)
        assert m.trust_score == 1.0

    def test_empty_results(self):
        m = compute_metrics([])
        assert m.precision == 1.0
        assert m.recall == 1.0

    def test_all_false_positives(self):
        results = [self._make_result(tp=0, fp=5, fn=0)]
        m = compute_metrics(results)
        assert m.precision == 0.0
        assert m.trust_score == 0.0

    def test_trust_score_penalizes_fp_heavily(self):
        """Trust score with 3x FP weighting is lower than raw precision."""
        results = [self._make_result(tp=10, fp=2, fn=0)]
        m = compute_metrics(results)
        assert m.precision == pytest.approx(10 / 12)
        # Trust: 10 / (10 + 6) = 10/16 = 0.625
        assert m.trust_score == pytest.approx(10 / 16)
        assert m.trust_score < m.precision


# ─── Report building ───


class TestBuildReport:
    def test_gate_passes_above_bars(self):
        results = [
            CaseResult(case_id="r1", provenance_kind="message", latency_ms=100)
        ]
        # All zeroes = 1.0 precision, 1.0 recall = PASS
        report = build_report("v0", "test-model", "test-hash", results)
        assert report.gate_passed is True
        assert report.overall_precision == 1.0

    def test_gate_fails_below_precision(self):
        result = CaseResult(case_id="r1", provenance_kind="message")
        # Add 1 TP and 1 FP = 50% precision
        from eval_harness.models import CommitmentMatch

        result.true_positives.append(CommitmentMatch(
            gold=GoldCommitment(title="g", **{"class": "task"}),
            extracted=ExtractedCommitment(title="e", confidence=0.9, **{"class": "task"}),
            title_match=True, due_match=True, class_match=True, amount_match=True,
        ))
        result.false_positives.append(
            ExtractedCommitment(title="bad", confidence=0.5, **{"class": "task"})
        )
        report = build_report("v0", "test", "test", [result])
        assert report.gate_passed is False
        assert report.overall_precision == pytest.approx(0.5)

    def test_latency_percentiles(self):
        results = [
            CaseResult(case_id=f"r{i}", provenance_kind="message", latency_ms=i * 100)
            for i in range(1, 21)
        ]
        report = build_report("v0", "test", "test", results)
        assert report.latency_p50_ms > 0
        assert report.latency_p95_ms >= report.latency_p50_ms


# ─── Dataset model ───


class TestDatasetModel:
    def test_loads_seed_dataset(self):
        import json
        from pathlib import Path

        path = Path(__file__).parent.parent / "data" / "v0" / "dataset.json"
        raw = json.loads(path.read_text())
        ds = EvalDataset.model_validate(raw)
        assert len(ds.cases) >= 500  # Gate 1 entry: ≥500 cases
        assert ds.total_gold >= 60  # Gate 1 entry: ≥60 gold commitments
        assert ds.adversarial_pct >= 0.15  # ≥15% adversarial (EVAL-HARNESS.md)

    def test_multi_counterparty_cases_exist(self):
        import json
        from pathlib import Path

        path = Path(__file__).parent.parent / "data" / "v0" / "dataset.json"
        raw = json.loads(path.read_text())
        ds = EvalDataset.model_validate(raw)
        assert ds.multi_cp_count >= 1
