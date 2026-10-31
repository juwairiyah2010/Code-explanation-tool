"""Core Evaluator for Code Lore Benchmark Suite.

Executes deterministic measurements across all 7 evaluation dimensions:
1. Static analysis accuracy
2. Execution trace accuracy
3. RAG retrieval relevance (Precision@k)
4. Explanation grounding
5. Line-reference accuracy
6. Quiz correctness and deterministic grading
7. Response latency profiling
"""

import time
from typing import Any
from backend.core.database import SessionLocal
from backend.schemas.explanation import CodeAnalysisResponse, ExplainCodeRequest
from backend.schemas.trace import TraceRequest
from backend.services.analysis.code_analyzer import CodeAnalyzer
from backend.services.explanation_pipeline import ExplanationPipeline
from backend.services.explanation_validator import ExplanationValidator
from backend.services.learning_service import LearningService
from backend.services.llm.mock_llm import MockLLMService
from backend.services.rag.embeddings import MockEmbeddingService
from backend.services.rag.retriever import RAGRetriever
from backend.services.tracer_service import TracerService
from evaluation.dataset import BENCHMARK_DATASET


class BenchmarkEvaluator:
    """Evaluates Code Lore components against the standardized benchmark dataset."""

    def __init__(self, top_k_rag: int = 3):
        self.dataset = BENCHMARK_DATASET
        self.top_k_rag = top_k_rag

        # Services under evaluation
        self.analyzer = CodeAnalyzer()
        self.tracer = TracerService(timeout_seconds=3.0)
        self.mock_llm = MockLLMService()
        self.validator = ExplanationValidator()
        self.learning_service = LearningService(llm_service=self.mock_llm)
        self.pipeline = ExplanationPipeline(
            llm_service=self.mock_llm,
            validator=self.validator,
        )

    async def run_full_evaluation(self) -> dict[str, Any]:
        """Execute all benchmarks and collect strict measurements."""
        case_results: list[dict[str, Any]] = []

        total_analysis_checks = 0
        passed_analysis_checks = 0

        trace_attempted = 0
        trace_passed = 0

        total_retrieval_queries = 0
        total_retrieval_precision_sum = 0.0

        total_coverage_scores: list[float] = []
        total_line_references = 0
        invalid_line_references = 0

        quiz_checks_total = 0
        quiz_checks_passed = 0

        latencies_ms: dict[str, list[float]] = {
            "analysis": [],
            "trace": [],
            "rag": [],
            "explanation": [],
            "quiz": [],
            "e2e": [],
        }

        db = SessionLocal()
        retriever = RAGRetriever(
            db=db,
            embedding_service=MockEmbeddingService(dimension=384),
        )

        try:
            for case in self.dataset:
                case_metrics: dict[str, Any] = {
                    "case_id": case.case_id,
                    "name": case.name,
                    "language": case.language,
                    "category": case.category,
                    "measurements": {},
                }

                # ── 1. Static Analysis Evaluation ───────────────────────
                t0 = time.perf_counter()
                analysis_res: CodeAnalysisResponse = self.analyzer.analyze(
                    case.code,
                    language=case.language,
                )
                t_analysis_ms = (time.perf_counter() - t0) * 1000.0
                latencies_ms["analysis"].append(t_analysis_ms)

                # Check construct detection
                construct_ok = True
                detected_constructs = set()
                if analysis_res.constructs:
                    if analysis_res.constructs.functions:
                        detected_constructs.add("functions")
                    if analysis_res.constructs.classes:
                        detected_constructs.add("classes")
                    if analysis_res.constructs.loops:
                        detected_constructs.add("loops")
                    if analysis_res.constructs.conditions:
                        detected_constructs.add("conditions")
                    if analysis_res.constructs.assignments:
                        detected_constructs.add("assignments")
                    if analysis_res.constructs.calls:
                        detected_constructs.add("calls")

                for expected_c in case.expected_constructs:
                    total_analysis_checks += 1
                    if expected_c in detected_constructs:
                        passed_analysis_checks += 1
                    else:
                        construct_ok = False

                # Check complexity bounds
                min_c, max_c = case.expected_complexity_range
                total_analysis_checks += 1
                complexity_ok = min_c <= analysis_res.complexity_score <= max_c
                if complexity_ok:
                    passed_analysis_checks += 1

                # Check expected rule findings
                findings_ok = True
                detected_rules = {h.rule_id for h in (analysis_res.hints or [])}
                for exp_rule in case.expected_findings:
                    total_analysis_checks += 1
                    if exp_rule in detected_rules:
                        passed_analysis_checks += 1
                    else:
                        findings_ok = False

                case_metrics["measurements"]["static_analysis"] = {
                    "is_valid_syntax": analysis_res.is_valid_syntax,
                    "detected_complexity": analysis_res.complexity_score,
                    "expected_complexity": list(case.expected_complexity_range),
                    "complexity_correct": complexity_ok,
                    "detected_constructs": list(detected_constructs),
                    "constructs_correct": construct_ok,
                    "expected_findings": case.expected_findings,
                    "detected_findings": list(detected_rules),
                    "findings_correct": findings_ok,
                    "latency_ms": round(t_analysis_ms, 2),
                }

                # ── 2. Execution Trace Accuracy ─────────────────────────
                if case.is_traceable and case.language == "python":
                    trace_attempted += 1
                    t0 = time.perf_counter()
                    trace_res = await self.tracer.trace_code(
                        TraceRequest(code=case.code, language="python")
                    )
                    t_trace_ms = (time.perf_counter() - t0) * 1000.0
                    latencies_ms["trace"].append(t_trace_ms)

                    output_matched = False
                    if case.expected_deterministic_output is not None:
                        output_matched = case.expected_deterministic_output.strip() == (trace_res.output or "").strip()
                    else:
                        output_matched = True

                    steps_valid = len(trace_res.steps) > 0 and trace_res.success
                    trace_ok = output_matched and steps_valid
                    if trace_ok:
                        trace_passed += 1

                    case_metrics["measurements"]["execution_trace"] = {
                        "executed": True,
                        "success": trace_res.success,
                        "steps_count": len(trace_res.steps),
                        "output_matched": output_matched,
                        "actual_output": trace_res.output,
                        "expected_output": case.expected_deterministic_output,
                        "latency_ms": round(t_trace_ms, 2),
                    }
                else:
                    case_metrics["measurements"]["execution_trace"] = {
                        "executed": False,
                        "reason": "Not configured for execution sandbox or non-Python",
                    }

                # ── 3. RAG Retrieval Relevance ──────────────────────────
                rag_precisions: list[float] = []
                for concept in case.expected_concepts[:2]:  # Test primary concepts
                    t0 = time.perf_counter()
                    retrieval_res = retriever.retrieve(
                        query=f"{case.language} {concept}",
                        language=case.language,
                        top_k=self.top_k_rag,
                        similarity_threshold=0.1,
                    )
                    t_rag_ms = (time.perf_counter() - t0) * 1000.0
                    latencies_ms["rag"].append(t_rag_ms)

                    # Compute Precision@k
                    retrieved_chunks = retrieval_res.results
                    relevant_count = 0
                    for c in retrieved_chunks:
                        # Match language relevance and concept keywords
                        lang_match = c.language in (case.language, "general")
                        concept_match = concept.lower() in (c.title + " " + c.section + " " + c.text).lower()
                        if lang_match and concept_match:
                            relevant_count += 1

                    prec_at_k = (relevant_count / len(retrieved_chunks)) if retrieved_chunks else 0.0
                    rag_precisions.append(prec_at_k)
                    total_retrieval_queries += 1
                    total_retrieval_precision_sum += prec_at_k

                case_metrics["measurements"]["rag_retrieval"] = {
                    "evaluated_concepts": case.expected_concepts[:2],
                    "precision_scores": [round(p, 3) for p in rag_precisions],
                    "mean_precision": round(sum(rag_precisions) / len(rag_precisions), 3) if rag_precisions else 1.0,
                }

                # ── 4 & 5. Explanation Grounding & Line Reference Accuracy
                t0 = time.perf_counter()
                pipeline_res = await self.pipeline.execute(
                    ExplainCodeRequest(
                        code=case.code,
                        language=case.language,
                        level="Beginner",
                    )
                )
                t_expl_ms = (time.perf_counter() - t0) * 1000.0
                latencies_ms["explanation"].append(t_expl_ms)

                val_res = pipeline_res.validation_result
                total_coverage_scores.append(val_res.coverage_score)

                total_lines_in_code = len(case.code.splitlines())
                case_refs = val_res.referenced_lines
                total_line_references += len(case_refs)

                case_invalid_refs = [
                    line for line in case_refs
                    if line < 1 or line > total_lines_in_code
                ]
                invalid_line_references += len(case_invalid_refs)

                case_metrics["measurements"]["explanation_grounding"] = {
                    "valid": val_res.valid,
                    "coverage_score": round(val_res.coverage_score, 3),
                    "referenced_lines": case_refs,
                    "invalid_references": case_invalid_refs,
                    "unsupported_claims": val_res.unsupported_claims,
                    "latency_ms": round(t_expl_ms, 2),
                }

                # ── 6. Quiz Correctness ─────────────────────────────────
                t0 = time.perf_counter()
                quiz_mat = await self.learning_service.generate_learning_material(
                    code=case.code,
                    language=case.language,
                )
                t_quiz_ms = (time.perf_counter() - t0) * 1000.0
                latencies_ms["quiz"].append(t_quiz_ms)

                questions = quiz_mat.questions
                q_valid = True
                quiz_checks_total += len(questions)

                for q in questions:
                    # Verify options contain correct answer and options are unique
                    opt_ids = [opt.id for opt in q.options]
                    if q.correct_answer in opt_ids and len(set(opt_ids)) == len(q.options):
                        quiz_checks_passed += 1
                    else:
                        q_valid = False

                # Test deterministic scoring engine with perfect answers
                grading_answers = {q.id: q.correct_answer for q in questions}
                test_user_id = 888000 + len(case_results)
                scoring_eval = self.learning_service.evaluate_answers(
                    answers=grading_answers,
                    questions_payload=[q.model_dump() for q in questions],
                    user_id=test_user_id,
                    db=db,
                )
                scoring_accurate = scoring_eval.score == 100.0 and scoring_eval.correct_count == len(questions)

                case_metrics["measurements"]["quiz"] = {
                    "questions_generated": len(questions),
                    "options_valid": q_valid,
                    "scoring_accurate": scoring_accurate,
                    "latency_ms": round(t_quiz_ms, 2),
                }

                # Total end-to-end latency for this benchmark case
                total_case_ms = t_analysis_ms + (t_trace_ms if case.is_traceable else 0) + t_expl_ms + t_quiz_ms
                latencies_ms["e2e"].append(total_case_ms)
                case_metrics["measurements"]["total_latency_ms"] = round(total_case_ms, 2)

                case_results.append(case_metrics)

        finally:
            db.close()

        # ── Calculate Summary Metrics ───────────────────────────────────
        analysis_accuracy = (passed_analysis_checks / total_analysis_checks * 100.0) if total_analysis_checks > 0 else 0.0
        trace_accuracy = (trace_passed / trace_attempted * 100.0) if trace_attempted > 0 else 0.0
        retrieval_precision_at_k = (total_retrieval_precision_sum / total_retrieval_queries) if total_retrieval_queries > 0 else 0.0
        avg_explanation_coverage = (sum(total_coverage_scores) / len(total_coverage_scores)) if total_coverage_scores else 0.0
        invalid_ref_rate = (invalid_line_references / total_line_references * 100.0) if total_line_references > 0 else 0.0
        quiz_accuracy = (quiz_checks_passed / quiz_checks_total * 100.0) if quiz_checks_total > 0 else 0.0

        all_e2e_latencies = sorted(latencies_ms["e2e"])
        avg_latency = sum(all_e2e_latencies) / len(all_e2e_latencies) if all_e2e_latencies else 0.0
        median_latency = all_e2e_latencies[len(all_e2e_latencies) // 2] if all_e2e_latencies else 0.0
        p95_index = int(len(all_e2e_latencies) * 0.95)
        p95_latency = all_e2e_latencies[min(p95_index, len(all_e2e_latencies) - 1)] if all_e2e_latencies else 0.0

        summary: dict[str, Any] = {
            "total_benchmark_cases": len(self.dataset),
            "summary_metrics": {
                "analysis_accuracy": round(analysis_accuracy, 2),
                "trace_accuracy": round(trace_accuracy, 2),
                "retrieval_precision_at_k": round(retrieval_precision_at_k, 3),
                "explanation_coverage": round(avg_explanation_coverage, 3),
                "invalid_line_reference_rate": round(invalid_ref_rate, 2),
                "quiz_accuracy": round(quiz_accuracy, 2),
                "average_latency_ms": round(avg_latency, 2),
            },
            "latency_breakdown_ms": {
                "average_analysis": round(sum(latencies_ms["analysis"]) / len(latencies_ms["analysis"]), 2),
                "average_trace": round(sum(latencies_ms["trace"]) / len(latencies_ms["trace"]), 2) if latencies_ms["trace"] else 0.0,
                "average_rag": round(sum(latencies_ms["rag"]) / len(latencies_ms["rag"]), 2),
                "average_explanation": round(sum(latencies_ms["explanation"]) / len(latencies_ms["explanation"]), 2),
                "average_quiz": round(sum(latencies_ms["quiz"]) / len(latencies_ms["quiz"]), 2),
                "e2e_median": round(median_latency, 2),
                "e2e_p95": round(p95_latency, 2),
            },
            "cases": case_results,
        }

        return summary
