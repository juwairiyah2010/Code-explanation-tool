"""Integration tests verifying the automated evaluation framework and benchmark dataset."""

import pytest
from evaluation.dataset import BENCHMARK_DATASET
from evaluation.evaluator import BenchmarkEvaluator


def test_benchmark_dataset_integrity():
    """Verify benchmark dataset covers all required syntax categories and edge cases."""
    assert len(BENCHMARK_DATASET) >= 10
    categories = {case.category for case in BENCHMARK_DATASET}
    languages = {case.language for case in BENCHMARK_DATASET}

    assert "python" in languages
    assert "javascript" in languages

    expected_categories = {
        "basic_variables",
        "conditionals",
        "loops",
        "functions",
        "recursion",
        "classes",
        "exceptions",
        "common_beginner_mistakes",
        "inefficient_code",
        "security_related",
    }
    assert expected_categories.issubset(categories)


@pytest.mark.asyncio
async def test_run_benchmark_evaluation():
    """Run full benchmark evaluation and verify all measured metrics meet target thresholds."""
    evaluator = BenchmarkEvaluator(top_k_rag=3)
    results = await evaluator.run_full_evaluation()

    assert results["total_benchmark_cases"] == len(BENCHMARK_DATASET)

    metrics = results["summary_metrics"]
    # 1. Static Analysis Accuracy >= 95%
    assert metrics["analysis_accuracy"] >= 95.0

    # 2. Execution Trace Accuracy == 100%
    assert metrics["trace_accuracy"] == 100.0

    # 3. Grounding Explanation Coverage >= 0.8
    assert metrics["explanation_coverage"] >= 0.8

    # 4. Invalid Line Reference Rate == 0.0%
    assert metrics["invalid_line_reference_rate"] == 0.0

    # 5. Quiz Correctness >= 95%
    assert metrics["quiz_accuracy"] >= 95.0

    # 6. Latency is tracked and sub-second
    assert metrics["average_latency_ms"] < 1000.0
