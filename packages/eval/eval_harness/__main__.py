"""CLI entry point for `just eval` / `python -m eval_harness`.

Runs the extraction pipeline against the frozen eval dataset,
scores results, and outputs a rich report to the console + JSON archive.
"""

import argparse
import asyncio
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from eval_harness.models import EvalReport
from eval_harness.runner import load_dataset, run_eval

console = Console()


def _render_report(report: EvalReport) -> None:
    """Render the eval report with rich formatting."""
    # Gate verdict
    if report.gate_passed:
        verdict = "[bold green]PASS[/bold green]"
    else:
        verdict = "[bold red]FAIL[/bold red]"

    console.print()
    console.print(
        Panel(
            f"[bold]Eval Report[/bold] — {report.dataset_version}\n"
            f"Model: {report.model_id}\n"
            f"Prompt: {report.prompt_hash}\n"
            f"Run: {report.run_at[:19]}",
            title="OpenLnk Extraction Eval",
            border_style="blue",
        )
    )

    # Overall metrics
    metrics = Table(title="Overall Metrics", show_header=True)
    metrics.add_column("Metric", style="bold")
    metrics.add_column("Value", justify="right")
    metrics.add_column("Gate", justify="right")
    metrics.add_column("Status", justify="center")

    p_color = "green" if report.overall_precision >= 0.97 else "red"
    r_color = "green" if report.overall_recall >= 0.85 else "red"

    metrics.add_row(
        "Precision",
        f"[{p_color}]{report.overall_precision:.1%}[/{p_color}]",
        "≥ 97%",
        "[green]PASS[/green]" if report.overall_precision >= 0.97 else "[red]FAIL[/red]",
    )
    metrics.add_row(
        "Recall",
        f"[{r_color}]{report.overall_recall:.1%}[/{r_color}]",
        "≥ 85%",
        "[green]PASS[/green]" if report.overall_recall >= 0.85 else "[red]FAIL[/red]",
    )
    metrics.add_row(
        "Trust Score",
        f"{report.overall_trust_score:.1%}",
        "(info)",
        "",
    )
    metrics.add_row(
        "TP / FP / FN",
        f"{report.total_tp} / {report.total_fp} / {report.total_fn}",
        "",
        "",
    )
    console.print(metrics)

    # Per-route breakdown
    if len(report.per_route) > 1:
        routes = Table(title="Per-Route Breakdown", show_header=True)
        routes.add_column("Route")
        routes.add_column("Cases", justify="right")
        routes.add_column("Precision", justify="right")
        routes.add_column("Recall", justify="right")
        routes.add_column("Trust", justify="right")
        routes.add_column("TP/FP/FN", justify="right")

        for rm in report.per_route:
            routes.add_row(
                rm.route,
                str(rm.case_count),
                f"{rm.precision:.1%}",
                f"{rm.recall:.1%}",
                f"{rm.trust_score:.1%}",
                f"{rm.tp_count}/{rm.fp_count}/{rm.fn_count}",
            )
        console.print(routes)

    # Latency
    console.print(
        f"\n  Latency  p50={report.latency_p50_ms:.0f}ms  "
        f"p95={report.latency_p95_ms:.0f}ms"
    )
    if report.cost_per_1k_msgs is not None:
        console.print(f"  Cost     ${report.cost_per_1k_msgs:.2f} / 1k msgs")

    # Confusion samples
    if report.confusion_samples:
        console.print(
            f"\n  [yellow]{len(report.confusion_samples)} case(s) "
            f"with errors[/yellow] (see JSON report for details)"
        )
        for cs in report.confusion_samples[:5]:
            fps = ", ".join(f'"{e.title}"' for e in cs.false_positives)
            fns = ", ".join(f'"{g.title}"' for g in cs.false_negatives)
            parts = []
            if fps:
                parts.append(f"FP=[{fps}]")
            if fns:
                parts.append(f"FN=[{fns}]")
            console.print(f"    {cs.case_id}: {' '.join(parts)}")

    # Verdict
    console.print(f"\n  Gate verdict: {verdict}")
    console.print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenLnk extraction eval harness"
    )
    parser.add_argument(
        "--version",
        default="v0",
        help="Dataset version to evaluate (default: v0)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Confidence threshold for filtering (default: 0.0 = use all)",
    )
    args = parser.parse_args()

    console.print("[bold blue]OpenLnk Eval Harness[/bold blue]")
    console.print(f"  Dataset: {args.version}")
    console.print(f"  Threshold: {args.threshold}")
    console.print()

    dataset = load_dataset(args.version)
    console.print(
        f"  Loaded {len(dataset.cases)} cases, "
        f"{dataset.total_gold} gold commitments, "
        f"{dataset.adversarial_pct:.0%} adversarial"
    )
    console.print()

    report = asyncio.run(
        run_eval(dataset, confidence_threshold=args.threshold)
    )

    _render_report(report)

    # Exit with non-zero if gate failed (CI gate)
    if not report.gate_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
