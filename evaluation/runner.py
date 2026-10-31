"""CLI entry point to execute the Code Lore Evaluation Benchmark Suite.

Produces machine-readable JSON metrics and a formatted terminal summary report.
Can be rerun after any codebase modifications using:
    python -m evaluation.runner
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from evaluation.evaluator import BenchmarkEvaluator


def print_summary_table(summary: dict) -> None:
    """Print an ASCII metrics summary table to the console."""
    metrics = summary["summary_metrics"]
    latency = summary["latency_breakdown_ms"]
    total_cases = summary["total_benchmark_cases"]

    print("\n" + "=" * 70)
    print("           CODE LORE SYSTEM EVALUATION BENCHMARK REPORT           ")
    print("=" * 70)
    print(f"Total Benchmark Cases Evaluated: {total_cases}")
    print("-" * 70)
    print("KEY PERFORMANCE & GROUNDING METRICS:")
    print(f"  • Static Analysis Accuracy      : {metrics['analysis_accuracy']}%")
    print(f"  • Execution Trace Accuracy      : {metrics['trace_accuracy']}%")
    print(f"  • RAG Retrieval Precision@k     : {metrics['retrieval_precision_at_k']}")
    print(f"  • Explanation Grounding Coverage: {metrics['explanation_coverage']}")
    print(f"  • Invalid Line-Reference Rate   : {metrics['invalid_line_reference_rate']}%")
    print(f"  • Quiz Generation & Grading Acc : {metrics['quiz_accuracy']}%")
    print(f"  • End-to-End Average Latency    : {metrics['average_latency_ms']} ms")
    print("-" * 70)
    print("LATENCY BREAKDOWN (Mean wall-clock):")
    print(f"  • Static Analysis Engine        : {latency['average_analysis']} ms")
    print(f"  • Execution Sandbox Trace       : {latency['average_trace']} ms")
    print(f"  • Hybrid RAG Retrieval          : {latency['average_rag']} ms")
    print(f"  • LLM Explanation & Grounding   : {latency['average_explanation']} ms")
    print(f"  • Interactive Quiz & Progress   : {latency['average_quiz']} ms")
    print(f"  • End-to-End P50 (Median)       : {latency['e2e_median']} ms")
    print(f"  • End-to-End P95                : {latency['e2e_p95']} ms")
    print("=" * 70)


async def main_async() -> int:
    parser = argparse.ArgumentParser(
        description="Run the automated evaluation benchmark for Code Lore."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="evaluation/results/benchmark_report.json",
        help="Path where machine-readable JSON evaluation report will be saved.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Top-K parameter for RAG retrieval evaluation.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed results per individual benchmark case.",
    )

    args = parser.parse_args()

    print("[*] Initializing Code Lore Benchmark Evaluator...")
    evaluator = BenchmarkEvaluator(top_k_rag=args.top_k)

    print(f"[*] Running {len(evaluator.dataset)} benchmark cases across Python and JavaScript...")
    results = await evaluator.run_full_evaluation()

    # Ensure output directory exists
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"[*] Machine-readable report saved to: {out_path.resolve()}")

    if args.verbose:
        print("\nDETAILED BENCHMARK CASE MEASUREMENTS:")
        for idx, case in enumerate(results["cases"], 1):
            m = case["measurements"]
            print(f"\n[{idx}/{len(results['cases'])}] {case['case_id']} ({case['name']}) - {case['language'].upper()}:")
            print(f"    - Static Analysis: complexity={m['static_analysis']['detected_complexity']} (correct={m['static_analysis']['complexity_correct']}), constructs={m['static_analysis']['detected_constructs']}")
            if m["execution_trace"]["executed"]:
                print(f"    - Trace: success={m['execution_trace']['success']}, output_matched={m['execution_trace']['output_matched']}, steps={m['execution_trace']['steps_count']}")
            print(f"    - RAG Precision: {m['rag_retrieval']['mean_precision']}")
            print(f"    - Grounding: valid={m['explanation_grounding']['valid']}, coverage={m['explanation_grounding']['coverage_score']}, invalid_refs={m['explanation_grounding']['invalid_references']}")
            print(f"    - Quiz: valid={m['quiz']['options_valid']}, score_accurate={m['quiz']['scoring_accurate']}")
            print(f"    - Total Case Latency: {m['total_latency_ms']} ms")

    print_summary_table(results)
    return 0


def main() -> None:
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
