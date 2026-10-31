"""Deterministic, reproducible profiling harness for Code Lore.

Measures all 8 critical dimensions:
1. API latency (cold, warm, p95 across primary endpoints)
2. AST analysis time (Python and JavaScript parsing & static analysis)
3. Execution tracing time (isolated sandbox subprocess & step collection)
4. Embedding generation time (single, batch, repeated text)
5. Retrieval time (dense semantic search, BM25 scoring, chunk ranking)
6. LLM response time & pipeline stage overhead (prompt building, mock/completion, grounding validation)
7. Database queries (total SQL queries executed, cumulative SQL execution time)
8. Memory consumption (peak heap memory and RSS usage via tracemalloc and resource)
"""

import asyncio
import json
import os
import resource
import statistics
import sys
import time
import tracemalloc
from typing import Any, Callable

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.core.database import SessionLocal, engine
from backend.main import app
from backend.schemas.explanation import ExplainCodeRequest
from backend.schemas.trace import TraceRequest
from backend.services.analysis.code_analyzer import CodeAnalyzer
from backend.services.explanation_pipeline import ExplanationPipeline
from backend.services.rag.embeddings import get_embedding_service
from backend.services.rag.retriever import RAGRetriever
from backend.services.tracer_service import TracerService
from evaluation.dataset import BENCHMARK_DATASET


class SQLQueryCounter:
    """SQLAlchemy cursor listener to record query counts and execution durations."""

    def __init__(self, target_engine):
        self.engine = target_engine
        self.queries: list[dict[str, Any]] = []
        self._listening = False

    def start(self):
        self.queries.clear()
        if not self._listening:
            event.listen(self.engine, "before_cursor_execute", self._before_execute)
            event.listen(self.engine, "after_cursor_execute", self._after_execute)
            self._listening = True

    def stop(self):
        if self._listening:
            event.remove(self.engine, "before_cursor_execute", self._before_execute)
            event.remove(self.engine, "after_cursor_execute", self._after_execute)
            self._listening = False

    def _before_execute(self, conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.perf_counter()

    def _after_execute(self, conn, cursor, statement, parameters, context, executemany):
        elapsed_ms = (time.perf_counter() - getattr(context, "_query_start_time", time.perf_counter())) * 1000.0
        self.queries.append({
            "statement": statement,
            "duration_ms": elapsed_ms,
        })

    @property
    def count(self) -> int:
        return len(self.queries)

    @property
    def total_duration_ms(self) -> float:
        return sum(q["duration_ms"] for q in self.queries)


def run_benchmark_timing(fn: Callable[[], Any], iterations: int = 5) -> dict[str, float]:
    """Measure cold and repeated warm durations in milliseconds."""
    # Cold run
    t0 = time.perf_counter()
    fn()
    cold_ms = (time.perf_counter() - t0) * 1000.0

    warm_times = []
    for _ in range(iterations):
        t1 = time.perf_counter()
        fn()
        warm_times.append((time.perf_counter() - t1) * 1000.0)

    warm_times.sort()
    p95_idx = max(0, int(len(warm_times) * 0.95) - 1)

    return {
        "cold_ms": round(cold_ms, 2),
        "mean_ms": round(statistics.mean(warm_times), 2),
        "min_ms": round(min(warm_times), 2),
        "p95_ms": round(warm_times[p95_idx], 2),
        "max_ms": round(max(warm_times), 2),
    }


async def run_async_benchmark_timing(fn_coro: Callable[[], Any], iterations: int = 5) -> dict[str, float]:
    """Measure cold and repeated warm durations for async coroutines."""
    t0 = time.perf_counter()
    await fn_coro()
    cold_ms = (time.perf_counter() - t0) * 1000.0

    warm_times = []
    for _ in range(iterations):
        t1 = time.perf_counter()
        await fn_coro()
        warm_times.append((time.perf_counter() - t1) * 1000.0)

    warm_times.sort()
    p95_idx = max(0, int(len(warm_times) * 0.95) - 1)

    return {
        "cold_ms": round(cold_ms, 2),
        "mean_ms": round(statistics.mean(warm_times), 2),
        "min_ms": round(min(warm_times), 2),
        "p95_ms": round(warm_times[p95_idx], 2),
        "max_ms": round(max(warm_times), 2),
    }


def profile_all(output_file: str | None = None) -> dict[str, Any]:
    """Execute complete profiling suite across all 8 dimensions."""
    print("=" * 70)
    print("🚀 Starting Code Lore Performance Profiling")
    print("=" * 70)

    results: dict[str, Any] = {}
    sql_counter = SQLQueryCounter(engine)

    # ─────────────────────────────────────────────────────────────────
    # 1. AST Analysis Profiling
    # ─────────────────────────────────────────────────────────────────
    print("\n[1/8] Profiling AST Analysis...")
    analyzer = CodeAnalyzer()

    # Pick sample cases from dataset
    py_simple = next(c.code for c in BENCHMARK_DATASET if c.case_id == "py_basic_variables")
    py_complex = next(c.code for c in BENCHMARK_DATASET if c.case_id == "py_recursion")
    js_simple = next(c.code for c in BENCHMARK_DATASET if c.case_id == "js_basic_variables_and_functions")
    js_complex = next(c.code for c in BENCHMARK_DATASET if c.case_id == "js_classes_and_inheritance")

    tracemalloc.start()
    ast_py_simple_metrics = run_benchmark_timing(lambda: analyzer.analyze(py_simple, "python"), iterations=10)
    ast_py_complex_metrics = run_benchmark_timing(lambda: analyzer.analyze(py_complex, "python"), iterations=10)
    ast_js_simple_metrics = run_benchmark_timing(lambda: analyzer.analyze(js_simple, "javascript"), iterations=10)
    ast_js_complex_metrics = run_benchmark_timing(lambda: analyzer.analyze(js_complex, "javascript"), iterations=10)
    _, ast_peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    results["ast_analysis"] = {
        "py_simple": ast_py_simple_metrics,
        "py_complex": ast_py_complex_metrics,
        "js_simple": ast_js_simple_metrics,
        "js_complex": ast_js_complex_metrics,
        "peak_memory_kb": round(ast_peak_mem / 1024.0, 2),
    }

    # ─────────────────────────────────────────────────────────────────
    # 2. Execution Tracing Profiling
    # ─────────────────────────────────────────────────────────────────
    print("[2/8] Profiling Execution Tracing...")
    tracer = TracerService()

    async def run_trace_py_simple():
        req = TraceRequest(code=py_simple, language="python", generate_flowchart=True)
        return await tracer.trace_code(req)

    async def run_trace_py_recursion():
        req = TraceRequest(code=py_complex, language="python", generate_flowchart=True)
        return await tracer.trace_code(req)

    loop = asyncio.get_event_loop()
    tracemalloc.start()
    trace_simple_metrics = loop.run_until_complete(
        run_async_benchmark_timing(run_trace_py_simple, iterations=5)
    )
    trace_recursion_metrics = loop.run_until_complete(
        run_async_benchmark_timing(run_trace_py_recursion, iterations=5)
    )
    _, trace_peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    results["execution_tracing"] = {
        "simple_trace": trace_simple_metrics,
        "recursion_trace": trace_recursion_metrics,
        "peak_memory_kb": round(trace_peak_mem / 1024.0, 2),
    }

    # ─────────────────────────────────────────────────────────────────
    # 3. Embedding Generation Profiling
    # ─────────────────────────────────────────────────────────────────
    print("[3/8] Profiling Embedding Generation...")
    embedding_service = get_embedding_service()
    sample_text = "Python function recursion call stack memory base case"
    batch_texts = [
        f"Concept {i}: algorithmic complexity and data structure representation"
        for i in range(10)
    ]

    tracemalloc.start()
    single_embed_metrics = run_benchmark_timing(
        lambda: embedding_service.embed_text(sample_text), iterations=10
    )
    batch_embed_metrics = run_benchmark_timing(
        lambda: embedding_service.embed_texts(batch_texts), iterations=5
    )
    # Repeated text embedding (tests if caching would benefit)
    repeated_embed_metrics = run_benchmark_timing(
        lambda: [embedding_service.embed_text(sample_text) for _ in range(5)], iterations=5
    )
    _, embed_peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    results["embedding_generation"] = {
        "single_text": single_embed_metrics,
        "batch_10_texts": batch_embed_metrics,
        "repeated_5x_same_text": repeated_embed_metrics,
        "peak_memory_kb": round(embed_peak_mem / 1024.0, 2),
    }

    # ─────────────────────────────────────────────────────────────────
    # 4. RAG Retrieval Profiling & Database Query Measurement
    # ─────────────────────────────────────────────────────────────────
    print("[4/8] Profiling RAG Knowledge Retrieval...")
    db = SessionLocal()
    retriever = RAGRetriever(db=db)

    sql_counter.start()
    tracemalloc.start()

    def retrieve_cold_and_warm(query: str, lang: str):
        return retriever.retrieve(query=query, language=lang, top_k=3)

    rag_py_query = "recursive function call stack"
    rag_timing = run_benchmark_timing(
        lambda: retrieve_cold_and_warm(rag_py_query, "python"), iterations=10
    )

    sql_counter.stop()
    _, rag_peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    results["retrieval"] = {
        "hybrid_search": rag_timing,
        "db_queries_for_11_runs": sql_counter.count,
        "avg_queries_per_retrieval": round(sql_counter.count / 11.0, 2),
        "total_sql_time_ms": round(sql_counter.total_duration_ms, 2),
        "peak_memory_kb": round(rag_peak_mem / 1024.0, 2),
    }

    # ─────────────────────────────────────────────────────────────────
    # 5. LLM Response & End-to-End Explanation Pipeline Profiling
    # ─────────────────────────────────────────────────────────────────
    print("[5/8] Profiling Explanation Pipeline Stages...")
    pipeline = ExplanationPipeline(db=db)
    explain_req = ExplainCodeRequest(
        code=py_complex,
        language="python",
        level="beginner",
        enable_trace=True,
        enable_rag=True,
        save_history=False,
    )

    sql_counter.start()
    tracemalloc.start()

    async def run_pipeline():
        return await pipeline.execute(explain_req)

    pipeline_timing = loop.run_until_complete(
        run_async_benchmark_timing(run_pipeline, iterations=5)
    )

    sql_counter.stop()
    _, pipeline_peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    results["explanation_pipeline"] = {
        "end_to_end": pipeline_timing,
        "db_queries_for_6_runs": sql_counter.count,
        "avg_queries_per_run": round(sql_counter.count / 6.0, 2),
        "total_sql_time_ms": round(sql_counter.total_duration_ms, 2),
        "peak_memory_kb": round(pipeline_peak_mem / 1024.0, 2),
    }

    # ─────────────────────────────────────────────────────────────────
    # 6. Database Queries & Transactions Profiling
    # ─────────────────────────────────────────────────────────────────
    print("[6/8] Profiling Database Operations...")
    from backend.repositories.learning_repo import LearningRepository
    from backend.repositories.rag_repo import RAGRepository
    from backend.repositories.submission_repo import SubmissionRepository

    rag_repo = RAGRepository(db)
    sub_repo = SubmissionRepository(db)
    learning_repo = LearningRepository(db)

    db_metrics: dict[str, Any] = {}

    # Query 1: Candidate chunks lookup
    sql_counter.start()
    for _ in range(10):
        rag_repo.get_candidate_chunks(language="python")
    sql_counter.stop()
    db_metrics["get_candidate_chunks_10x"] = {
        "queries": sql_counter.count,
        "total_duration_ms": round(sql_counter.total_duration_ms, 2),
        "avg_duration_ms": round(sql_counter.total_duration_ms / 10.0, 3),
    }

    # Query 2: Learner progress lookup
    sql_counter.start()
    for _ in range(10):
        learning_repo.get_learner_progress(user_id=1)
    sql_counter.stop()
    db_metrics["get_learner_progress_10x"] = {
        "queries": sql_counter.count,
        "total_duration_ms": round(sql_counter.total_duration_ms, 2),
        "avg_duration_ms": round(sql_counter.total_duration_ms / 10.0, 3),
    }

    # Query 3: Evaluation & progress record attempt
    test_questions = [
        {
            "id": "q1",
            "concept": "Recursion",
            "correct_answer": "B",
            "question": "What is the base case?",
        },
        {
            "id": "q2",
            "concept": "Loops",
            "correct_answer": "A",
            "question": "How many iterations?",
        },
    ]
    test_answers = {"q1": "B", "q2": "C"}
    sql_counter.start()
    for _ in range(5):
        learning_repo.evaluate_and_record_attempt(
            questions=test_questions,
            answers=test_answers,
            language="python",
            user_id=999,
        )
    sql_counter.stop()
    db_metrics["evaluate_and_record_attempt_5x"] = {
        "queries": sql_counter.count,
        "total_duration_ms": round(sql_counter.total_duration_ms, 2),
        "avg_duration_ms": round(sql_counter.total_duration_ms / 5.0, 3),
    }

    results["database_operations"] = db_metrics
    db.close()

    # ─────────────────────────────────────────────────────────────────
    # 7. API Endpoints Latency Profiling
    # ─────────────────────────────────────────────────────────────────
    print("[7/8] Profiling API Endpoints Latency via TestClient...")
    client = TestClient(app)
    api_results: dict[str, Any] = {}

    # /api/v1/ast/analyze
    ast_req_payload = {"code": py_complex, "language": "python"}
    api_results["post_ast_analyze"] = run_benchmark_timing(
        lambda: client.post("/api/v1/ast/analyze", json=ast_req_payload), iterations=10
    )

    # /api/v1/trace
    trace_req_payload = {"code": py_simple, "language": "python", "generate_flowchart": True}
    api_results["post_trace"] = run_benchmark_timing(
        lambda: client.post("/api/v1/trace", json=trace_req_payload), iterations=5
    )

    # /api/v1/rag/retrieve
    rag_req_payload = {"query": "how do loops work in python", "language": "python", "top_k": 3}
    api_results["post_rag_retrieve"] = run_benchmark_timing(
        lambda: client.post("/api/v1/rag/retrieve", json=rag_req_payload), iterations=10
    )

    # /api/v1/learning/material
    material_req_payload = {"code": py_complex, "language": "python", "level": "beginner"}
    api_results["post_learning_material"] = run_benchmark_timing(
        lambda: client.post("/api/v1/learning/material", json=material_req_payload), iterations=5
    )

    # /api/v1/learning/evaluate
    eval_req_payload = {
        "questions": test_questions,
        "answers": test_answers,
        "language": "python",
    }
    api_results["post_learning_evaluate"] = run_benchmark_timing(
        lambda: client.post("/api/v1/learning/evaluate", json=eval_req_payload), iterations=10
    )

    # /api/v1/explain
    explain_req_payload = {
        "code": py_simple,
        "language": "python",
        "level": "beginner",
        "enable_trace": True,
        "enable_rag": True,
    }
    api_results["post_explain"] = run_benchmark_timing(
        lambda: client.post("/api/v1/explain", json=explain_req_payload), iterations=5
    )

    results["api_latencies"] = api_results

    # ─────────────────────────────────────────────────────────────────
    # 8. System Memory Consumption Profiling
    # ─────────────────────────────────────────────────────────────────
    print("[8/8] Measuring Global Memory Usage...")
    ru_maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # On macOS ru_maxrss is in bytes; on Linux in kilobytes
    import sys
    rss_mb = round((ru_maxrss / (1024.0 * 1024.0)) if sys.platform == "darwin" else (ru_maxrss / 1024.0), 2)

    results["memory_consumption"] = {
        "process_max_rss_mb": rss_mb,
        "platform": sys.platform,
        "ast_peak_kb": results["ast_analysis"]["peak_memory_kb"],
        "trace_peak_kb": results["execution_tracing"]["peak_memory_kb"],
        "embed_peak_kb": results["embedding_generation"]["peak_memory_kb"],
        "retrieval_peak_kb": results["retrieval"]["peak_memory_kb"],
        "pipeline_peak_kb": results["explanation_pipeline"]["peak_memory_kb"],
    }

    # Summary
    print("\n" + "=" * 70)
    print("📊 Profiling Complete!")
    print(f"Max RSS: {rss_mb} MB")
    print(f"AST Analysis (Python simple): {results['ast_analysis']['py_simple']['mean_ms']} ms")
    print(f"AST Analysis (Python complex): {results['ast_analysis']['py_complex']['mean_ms']} ms")
    print(f"Execution Tracing (Simple): {results['execution_tracing']['simple_trace']['mean_ms']} ms")
    print(f"RAG Retrieval (Hybrid): {results['retrieval']['hybrid_search']['mean_ms']} ms")
    print(f"Explanation Pipeline (E2E): {results['explanation_pipeline']['end_to_end']['mean_ms']} ms")
    print(f"API /api/v1/ast/analyze: {results['api_latencies']['post_ast_analyze']['mean_ms']} ms")
    print(f"API /api/v1/rag/retrieve: {results['api_latencies']['post_rag_retrieve']['mean_ms']} ms")
    print(f"API /api/v1/explain: {results['api_latencies']['post_explain']['mean_ms']} ms")
    print("=" * 70)

    if output_file:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"📁 Benchmark report saved to: {output_file}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Profile Code Lore Performance")
    parser.add_argument("--out", type=str, default="profiling/baseline_report.json", help="Output JSON path")
    args = parser.parse_args()
    profile_all(args.out)
