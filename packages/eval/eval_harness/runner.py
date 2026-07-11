"""Eval runner — executes the extraction pipeline against the frozen dataset.

Loads the frozen dataset, sends each message through LLMAdapter,
collects ExtractionOutput, scores, and builds the report.
"""

import json
import sys
import time
from pathlib import Path

from eval_harness.models import (
    EvalCase,
    EvalDataset,
    EvalReport,
    ExtractedCommitment,
    ExtractionOutput,
)
from eval_harness.scorer import build_report, score_case

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def load_dataset(version: str = "v0") -> EvalDataset:
    """Load a frozen eval dataset from disk."""
    dataset_path = _DATA_DIR / version / "dataset.json"
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}", file=sys.stderr)
        print(
            "Create the dataset file with labeled eval cases. "
            "See EVAL-HARNESS.md for the format.",
            file=sys.stderr,
        )
        sys.exit(1)

    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    return EvalDataset.model_validate(raw)


async def run_eval(
    dataset: EvalDataset,
    *,
    confidence_threshold: float = 0.0,
) -> EvalReport:
    """Run the full eval pipeline.

    Imports LLMAdapter at call time so the eval harness can be tested
    without the full API dependency tree installed.
    """
    # Import here to avoid hard dependency on apps/api at import time.
    # The eval harness adds apps/api to sys.path when invoked via `just eval`.
    import os
    api_dir = Path(__file__).resolve().parent.parent.parent.parent / "apps" / "api"
    sys.path.insert(0, str(api_dir))
    # Temporarily change cwd so pydantic_settings finds apps/api/.env
    prev_cwd = os.getcwd()
    os.chdir(str(api_dir))
    from app.services.llm import LLMAdapter  # type: ignore[import-untyped]
    os.chdir(prev_cwd)

    adapter = LLMAdapter()
    case_results = []
    outputs: list[ExtractionOutput] = []

    prompt_hash = adapter._prompt_hash
    model_id = adapter._model

    for i, case in enumerate(dataset.cases):
        t0 = time.monotonic()

        try:
            result = await adapter.extract_commitments(case.message)
            latency_ms = (time.monotonic() - t0) * 1000

            extracted = [
                ExtractedCommitment.model_validate(
                    c.model_dump(by_alias=True)
                )
                for c in result.commitments
                if c.confidence >= confidence_threshold
            ]

            output = ExtractionOutput(
                case_id=case.id,
                commitments=extracted,
                prompt_hash=result.prompt_hash,
                model_id=result.model_id,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.monotonic() - t0) * 1000
            print(
                f"  [{i + 1}/{len(dataset.cases)}] "
                f"CASE {case.id} ERROR: {e}",
                file=sys.stderr,
            )
            output = ExtractionOutput(
                case_id=case.id,
                commitments=[],
                prompt_hash=prompt_hash,
                model_id=model_id,
                latency_ms=latency_ms,
            )

        outputs.append(output)

        scored = score_case(case, output)
        case_results.append(scored)

        tp = len(scored.true_positives)
        fp = len(scored.false_positives)
        fn = len(scored.false_negatives)
        status = "OK" if fp == 0 and fn == 0 else "MISS"
        print(
            f"  [{i + 1}/{len(dataset.cases)}] "
            f"{case.id}: TP={tp} FP={fp} FN={fn} "
            f"({latency_ms:.0f}ms) [{status}]"
        )

    report = build_report(
        dataset_version=dataset.version,
        model_id=model_id,
        prompt_hash=prompt_hash,
        case_results=case_results,
    )

    # Archive the report
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = _REPORTS_DIR / f"report_{dataset.version}_{report.run_at[:19].replace(':', '-')}.json"
    report_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    await adapter.close()
    return report


async def run_eval_offline(
    dataset: EvalDataset,
    extraction_outputs: list[ExtractionOutput],
) -> EvalReport:
    """Score pre-collected outputs (no LLM calls). For testing."""
    outputs_by_id = {o.case_id: o for o in extraction_outputs}
    case_results = []

    for case in dataset.cases:
        output = outputs_by_id.get(case.id)
        if output is None:
            output = ExtractionOutput(
                case_id=case.id,
                commitments=[],
                prompt_hash="offline",
                model_id="offline",
                latency_ms=0.0,
            )
        scored = score_case(case, output)
        case_results.append(scored)

    prompt_hash = extraction_outputs[0].prompt_hash if extraction_outputs else "offline"
    model_id = extraction_outputs[0].model_id if extraction_outputs else "offline"

    return build_report(
        dataset_version=dataset.version,
        model_id=model_id,
        prompt_hash=prompt_hash,
        case_results=case_results,
    )
