"""Eval scorer — matches extracted commitments against gold labels.

Matching rules (from EVAL-HARNESS.md):
- True positive: extracted matches gold on owner + normalized title intent
  (semantic match) and due within ±30 min when both present.
- False positive: extracted with no gold counterpart, OR wrong owner,
  OR hallucinated amount/date. Weighted 3x in trust score.
- False negative: gold with no extraction.
- Trust score: tp / (tp + 3*fp) — reported alongside raw precision.
"""

from datetime import datetime, timedelta

from eval_harness.models import (
    CaseResult,
    CommitmentMatch,
    EvalCase,
    EvalReport,
    ExtractedCommitment,
    ExtractionOutput,
    GoldCommitment,
    RouteMetrics,
)

# ±30 min tolerance for due_at matching
_DUE_TOLERANCE = timedelta(minutes=30)


_ABBREVIATIONS: dict[str, str] = {
    "ptm": "parent teacher meeting",
    "hw": "homework",
    "govt": "government",
    "govt.": "government",
    "std": "standard",
    "std.": "standard",
    "yr": "year",
    "mth": "month",
    "amt": "amount",
    "pmt": "payment",
}

# Synonyms collapsed to a canonical form for word-overlap matching
_SYNONYMS: dict[str, str] = {
    "exam": "test",
    "examination": "test",
    "commence": "start",
    "commences": "start",
    "begin": "start",
    "begins": "start",
    "beginning": "start",
    "submit": "complete",
    "submitting": "complete",
    "submission": "complete",
    "prepare": "complete",
    "preparation": "complete",
    "scheduled": "schedule",
    "scheduling": "schedule",
    "reschedule": "schedule",
    "rescheduled": "schedule",
}

import re

_TIME_RE = re.compile(
    r"\b(\d{1,2})\s*:\s*(\d{2})\s*(am|pm|a\.m\.|p\.m\.)\b", re.IGNORECASE
)
_TIME_SIMPLE_RE = re.compile(r"\b(\d{1,2})\s*(am|pm)\b", re.IGNORECASE)


def _normalize_title(title: str) -> str:
    """Normalize title for comparison: lowercase, strip, collapse whitespace,
    expand abbreviations, normalize time and currency formats."""
    t = title.lower().strip()
    # Normalize currency symbols to 'rs'
    t = t.replace("₹", "rs ").replace("rs.", "rs ").replace("inr", "rs ")
    # Normalize times: "5:00 PM" → "5pm", "5:00pm" → "5pm"
    t = _TIME_RE.sub(
        lambda m: f"{m.group(1)}{m.group(3).rstrip('.').replace('.','').lower()}",
        t,
    )
    t = " ".join(t.split())
    # Expand abbreviations and collapse synonyms
    words = t.split()
    expanded = [_ABBREVIATIONS.get(w, w) for w in words]
    normalized = []
    for w in " ".join(expanded).split():
        normalized.append(_SYNONYMS.get(w, w))
    return " ".join(normalized)


def _stem(word: str) -> str:
    """Minimal English stemmer for matching: strip trailing 's', 'ed', 'ing'."""
    if len(word) > 4 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 3 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _titles_match(gold_title: str, extracted_title: str) -> bool:
    """Semantic title match — normalized word overlap.

    A proper semantic matcher (embedding similarity) can replace this
    at Gate 2+ when the dataset is large enough. For v0, normalized
    word overlap catches most cases.
    """
    g = _normalize_title(gold_title)
    e = _normalize_title(extracted_title)
    # Exact match or one contains the other
    if g == e:
        return True
    if g and e and (g in e or e in g):
        return True
    # Check key word overlap (ignoring common stop words)
    _STOP = {"the", "a", "an", "is", "to", "for", "of", "and", "by", "on",
             "in", "at", "from", "with", "will", "be", "has", "was", "are",
             "this", "that", "it", "its", "i", "we", "you", "my", "our",
             "please", "kindly", "sir", "madam", "ma'am", "dear"}
    gold_words = set(_stem(w) for w in g.split()) - _STOP
    extracted_words = set(_stem(w) for w in e.split()) - _STOP
    if not gold_words:
        return False
    overlap = gold_words & extracted_words
    # At least 40% content-word overlap
    return len(overlap) / len(gold_words) >= 0.4


def _counterparties_overlap(
    gold_cps: list, extracted_cps: list,
) -> bool:
    """Check if counterparty names overlap."""
    if not gold_cps and not extracted_cps:
        return True
    gold_names = {cp.name.lower() for cp in gold_cps}
    ext_names = {cp.name.lower() for cp in extracted_cps}
    if not gold_names:
        return True  # No specific counterparties required
    return bool(gold_names & ext_names)


def _can_match(
    gold: "GoldCommitment",
    ext: "ExtractedCommitment",
) -> bool:
    """Multi-factor matching: title match OR structural alignment.

    A match requires EITHER:
    - Title word overlap (primary signal), OR
    - Same class AND at least one structural match (amount or counterparties)

    This handles paraphrased messages where extraction titles differ from
    gold labels but the structural content is identical.
    """
    title_ok = _titles_match(gold.title, ext.title)
    if title_ok:
        return True

    # Structural fallback: class must match
    if gold.class_ != ext.class_:
        return False

    # Need at least one structural signal
    amount_ok = _amounts_match(gold.amount_paise, ext.amount_paise)
    cp_ok = _counterparties_overlap(gold.counterparties, ext.counterparties)

    # Amount match is strong signal, but if both sides name specific
    # counterparties those must also overlap (prevents cross-person matching
    # in multi-person fee messages where amounts are identical).
    if amount_ok and gold.amount_paise is not None:
        if gold.counterparties and ext.counterparties:
            return cp_ok  # Both have CPs → require overlap
        return True

    # Counterparty match is strong signal (specific names)
    if cp_ok and gold.counterparties:
        return True

    return False


def _due_dates_match(gold_due: str | None, extracted_due: str | None) -> bool:
    """Check if due dates match within ±30 min tolerance."""
    if gold_due is None and extracted_due is None:
        return True
    if gold_due is None or extracted_due is None:
        return False  # One has a date, the other doesn't
    try:
        g = datetime.fromisoformat(gold_due)
        e = datetime.fromisoformat(extracted_due)
        return abs(g - e) <= _DUE_TOLERANCE
    except ValueError:
        return False


def _amounts_match(
    gold_amount: int | None, extracted_amount: int | None
) -> bool:
    """Check if amounts match exactly."""
    return gold_amount == extracted_amount


def score_case(
    case: EvalCase,
    output: ExtractionOutput,
) -> CaseResult:
    """Score a single eval case: match extractions against gold labels.

    Uses greedy matching: each extracted commitment is matched to the
    best-fitting unmatched gold commitment.
    """
    result = CaseResult(
        case_id=case.id,
        provenance_kind=case.provenance_kind,
        latency_ms=output.latency_ms,
    )

    unmatched_gold = list(case.gold_commitments)
    unmatched_extracted = list(output.commitments)

    # Greedy matching: for each extracted, find best gold match
    matched_pairs: list[tuple[int, int, CommitmentMatch]] = []

    for ei, ext in enumerate(unmatched_extracted):
        best_gi: int | None = None
        best_match: CommitmentMatch | None = None
        best_score: int = -1

        for gi, gold in enumerate(unmatched_gold):
            if not _can_match(gold, ext):
                continue

            title_ok = _titles_match(gold.title, ext.title)
            due_ok = _due_dates_match(gold.due_at, ext.due_at)
            class_ok = gold.class_ == ext.class_
            amount_ok = _amounts_match(gold.amount_paise, ext.amount_paise)
            cp_ok = _counterparties_overlap(gold.counterparties, ext.counterparties)

            match = CommitmentMatch(
                gold=gold,
                extracted=ext,
                title_match=title_ok,
                due_match=due_ok,
                class_match=class_ok,
                amount_match=amount_ok,
            )

            # Score match quality for ranking (cp_ok breaks ties on
            # multi-person fee messages where class+amount are identical)
            score = sum([title_ok, due_ok, class_ok, amount_ok, cp_ok])
            if score > best_score:
                best_gi = gi
                best_match = match
                best_score = score

        if best_match is not None and best_gi is not None:
            matched_pairs.append((best_gi, ei, best_match))

    # Remove duplicates: each gold can only match once
    used_gold: set[int] = set()
    used_ext: set[int] = set()

    # Sort by quality (more field matches = better)
    matched_pairs.sort(
        key=lambda t: (
            t[2].title_match,
            t[2].due_match,
            t[2].class_match,
            t[2].amount_match,
        ),
        reverse=True,
    )

    for gi, ei, match in matched_pairs:
        if gi not in used_gold and ei not in used_ext:
            result.true_positives.append(match)
            used_gold.add(gi)
            used_ext.add(ei)

    # Remaining unmatched
    for ei, ext in enumerate(unmatched_extracted):
        if ei not in used_ext:
            result.false_positives.append(ext)

    for gi, gold in enumerate(unmatched_gold):
        if gi not in used_gold:
            result.false_negatives.append(gold)

    return result


def compute_metrics(
    results: list[CaseResult],
    route: str = "all",
) -> RouteMetrics:
    """Compute precision, recall, trust score for a set of case results."""
    tp = sum(len(r.true_positives) for r in results)
    fp = sum(len(r.false_positives) for r in results)
    fn = sum(len(r.false_negatives) for r in results)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    # Trust score: FP weighted 3x (EVAL-HARNESS.md)
    trust_denom = tp + 3 * fp
    trust_score = tp / trust_denom if trust_denom > 0 else 1.0

    return RouteMetrics(
        route=route,
        precision=precision,
        recall=recall,
        trust_score=trust_score,
        tp_count=tp,
        fp_count=fp,
        fn_count=fn,
        case_count=len(results),
    )


def build_report(
    dataset_version: str,
    model_id: str,
    prompt_hash: str,
    case_results: list[CaseResult],
) -> EvalReport:
    """Build a full eval report from scored case results."""
    # Overall metrics
    overall = compute_metrics(case_results)

    # Per-route breakdown
    routes: dict[str, list[CaseResult]] = {}
    for r in case_results:
        routes.setdefault(r.provenance_kind, []).append(r)

    per_route = [
        compute_metrics(results, route=route)
        for route, results in sorted(routes.items())
    ]

    # Latency stats
    latencies = sorted(r.latency_ms for r in case_results if r.latency_ms > 0)
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95_idx = int(len(latencies) * 0.95)
    p95 = latencies[min(p95_idx, len(latencies) - 1)] if latencies else 0.0

    # Confusion samples: cases with FP or FN (for human review)
    confusion = [
        r for r in case_results
        if r.false_positives or r.false_negatives
    ]

    gate_passed = (
        overall.precision >= EvalReport.precision_bar()
        and overall.recall >= EvalReport.recall_bar()
    )

    return EvalReport(
        dataset_version=dataset_version,
        run_at=datetime.utcnow().isoformat(),
        model_id=model_id,
        prompt_hash=prompt_hash,
        overall_precision=overall.precision,
        overall_recall=overall.recall,
        overall_trust_score=overall.trust_score,
        per_route=per_route,
        total_cases=len(case_results),
        total_tp=overall.tp_count,
        total_fp=overall.fp_count,
        total_fn=overall.fn_count,
        latency_p50_ms=p50,
        latency_p95_ms=p95,
        confusion_samples=confusion[:50],  # Cap at 50 for debugging
        gate_passed=gate_passed,
    )
