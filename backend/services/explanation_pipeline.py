"""Core Explanation Pipeline linking deterministic analysis, execution tracing, RAG, and LLM synthesis."""

import json
from typing import Any
from sqlalchemy.orm import Session

from backend.core.logging import logger
from backend.repositories.submission_repo import SubmissionRepository
from backend.schemas.explanation import (
    AlgorithmComplexity,
    BlockExplanation,
    CodeAnalysisResponse,
    ConceptItem,
    ConceptTag,
    ExplainCodeRequest,
    ExplainCodeResponse,
    LearnerProfile,
    LineExplanationItem,
    StructuredExplanationOutput,
)


from backend.schemas.rag import RAGSourceCitation
from backend.schemas.trace import TraceResponse
from backend.services.analysis.analysis_service import AnalysisService
from backend.services.detector.language_detector import LanguageDetector
from backend.services.explanation_validator import ExplanationValidator
from backend.services.llm import get_llm_service
from backend.services.llm.base import BaseLLMService, LLMExplanationResult
from backend.services.prompt_builder import PromptBuilder
from backend.services.rag.retrieval_service import RetrievalService
from backend.services.tracer_service import TraceService


class ExplanationPipeline:
    """Service orchestrating the complete 10-stage deterministic-to-LLM explanation pipeline."""

    def __init__(
        self,
        db: Session | None = None,
        language_detector: LanguageDetector | None = None,
        analysis_service: AnalysisService | None = None,
        trace_service: TraceService | None = None,
        retrieval_service: RetrievalService | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_service: BaseLLMService | None = None,
        validator: ExplanationValidator | None = None,
        repo: SubmissionRepository | None = None,
    ):
        self.db = db
        self.language_detector = language_detector or LanguageDetector()
        self.analysis_service = analysis_service or AnalysisService()
        self.trace_service = trace_service or TraceService()
        self.retrieval_service = retrieval_service or RetrievalService(db=db)
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm_service = llm_service or get_llm_service()
        self.validator = validator or ExplanationValidator()
        self.repo = repo or (SubmissionRepository(db) if db is not None else None)

    async def execute(self, request: ExplainCodeRequest) -> ExplainCodeResponse:
        """Run the end-to-end explanation pipeline."""
        code = request.code
        filename = request.filename
        logger.info(f"ExplanationPipeline starting for snippet ({len(code)} chars, {len(code.splitlines())} lines).")

        # ── 1. Language Detection ─────────────────────────────────────
        detection = self.language_detector.detect(
            code=code,
            filename=filename,
            explicit_language=request.language if request.language != "auto" else None,
        )
        resolved_lang = detection.language if detection.language != "unknown" else "python"
        logger.info(f"Language detected: {resolved_lang} via {detection.method} (confidence {detection.confidence})")

        # ── 2. AST / Static Analysis ──────────────────────────────────
        ast_result: CodeAnalysisResponse | None = None
        if request.include_ast_analysis:
            ast_result = self.analysis_service.analyze(
                code=code,
                language=resolved_lang,
                filename=filename,
            )
            # Re-resolve language if AST determined otherwise
            if ast_result and ast_result.language:
                resolved_lang = ast_result.language

        # ── 3. Execution Trace when applicable ────────────────────────
        trace_result: TraceResponse | None = None
        is_syntax_valid = ast_result.is_valid_syntax if ast_result else True
        if request.enable_trace and resolved_lang == "python" and is_syntax_valid:
            try:
                trace_result = await self.trace_service.trace_if_applicable(code, resolved_lang)
                if trace_result and trace_result.success:
                    logger.info(f"Execution trace completed: {len(trace_result.steps or [])} steps.")
                elif trace_result and trace_result.error:
                    logger.warning(f"Execution trace encountered issue: {trace_result.error}")
            except Exception as e:
                logger.warning(f"Execution trace failed non-fatally: {e}")

        # ── 4. RAG Retrieval ──────────────────────────────────────────
        rag_sources: list[RAGSourceCitation] = []
        rag_formatted_context: str | None = None
        rag_context_used = False

        if request.enable_rag and self.retrieval_service:
            try:
                rag_res = self.retrieval_service.retrieve(
                    code=code,
                    language=resolved_lang,
                    ast_result=ast_result,
                    top_k=3,
                    min_relevance_threshold=0.32,
                )
                if rag_res.results:
                    rag_sources = rag_res.results
                    rag_formatted_context = rag_res.formatted_context
                    rag_context_used = True
                    logger.info(f"RAG retrieved {len(rag_sources)} knowledge chunks.")
            except Exception as e:
                logger.warning(f"RAG retrieval encountered non-fatal error: {e}")

        # ── 5. Learner Profile & Mode Normalization ───────────────────
        learner_profile = request.learner_profile or LearnerProfile(
            level=request.level,
            mode=request.mode or request.level,
        )
        norm_mode = self.prompt_builder.normalize_mode(
            request.mode or learner_profile.mode,
            request.level or learner_profile.level,
        )

        # ── 6. Prompt Builder ─────────────────────────────────────────
        sys_prompt, user_prompt = self.prompt_builder.build_prompts(
            code=code,
            language=resolved_lang,
            mode=norm_mode,
            ast_result=ast_result,
            trace_result=trace_result,
            rag_citations=rag_sources,
            rag_formatted_context=rag_formatted_context,
            learner_profile=learner_profile,
        )

        # ── 7. LLM Invocation ─────────────────────────────────────────
        raw_llm_output: str | None = None
        legacy_llm_result: LLMExplanationResult | None = None
        legacy_validated_blocks: list[BlockExplanation] | None = None

        ast_summary_context = None
        if ast_result and ast_result.constructs:
            ast_summary_context = (
                f"Functions: {[f.name for f in ast_result.constructs.functions]}, "
                f"Classes: {[c.name for c in ast_result.constructs.classes]}, "
                f"Loops: {len(ast_result.constructs.loops)}, "
                f"Conditions: {len(ast_result.constructs.conditions)}, "
                f"Complexity Score: {ast_result.complexity_score}"
            )

        try:
            raw_llm_output = await self.llm_service.generate_chat_completion(
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                json_mode=True,
            )
        except NotImplementedError:
            # Service only implements generate_explanation (legacy or test mock)
            try:
                import inspect
                sig = inspect.signature(self.llm_service.generate_explanation)
                params = sig.parameters
                call_kwargs: dict[str, Any] = {
                    "code": code,
                    "language": resolved_lang,
                    "level": norm_mode,
                }
                if "ast_context" in params:
                    call_kwargs["ast_context"] = ast_summary_context
                if "required_blocks" in params:
                    call_kwargs["required_blocks"] = ast_result.blocks if ast_result and ast_result.blocks else []
                if "rag_context" in params:
                    call_kwargs["rag_context"] = rag_formatted_context
                if "rag_citations" in params:
                    call_kwargs["rag_citations"] = rag_sources

                legacy_llm_result = await self.llm_service.generate_explanation(**call_kwargs)
            except ValueError:
                raise
            except Exception as e:
                logger.error(f"Legacy LLM invocation error: {e}")

        except Exception as e:
            logger.error(f"LLM invocation error: {e}")

        # ── 8. Output Validator & Retry / Fallback Strategy ───────────
        structured_output: StructuredExplanationOutput | None = None
        validation_error: str | None = None

        if legacy_llm_result:
            max_lines = len(code.splitlines())
            validated_blocks = []
            for b in legacy_llm_result.blocks:
                b.line_start = max(1, min(b.line_start, max_lines))
                b.line_end = max(b.line_start, min(b.line_end, max_lines))
                validated_blocks.append(b)

            required_blocks = ast_result.blocks if ast_result and ast_result.blocks else []
            if required_blocks:
                covered = {b.title for b in validated_blocks}
                missing = [rb for rb in required_blocks if rb.title not in covered]
                retry_count = 0
                while missing and retry_count < 2:
                    call_kwargs["required_blocks"] = missing
                    retry_res = await self.llm_service.generate_explanation(**call_kwargs)
                    for nb in retry_res.blocks:
                        nb.line_start = max(1, min(nb.line_start, max_lines))
                        nb.line_end = max(nb.line_start, min(nb.line_end, max_lines))
                        validated_blocks.append(nb)
                    covered = {b.title for b in validated_blocks}
                    missing = [rb for rb in required_blocks if rb.title not in covered]
                    retry_count += 1
                validated_blocks.sort(key=lambda b: (b.line_start, b.line_end))

            legacy_validated_blocks = validated_blocks
            source_lines = code.splitlines()
            line_expls = [
                LineExplanationItem(
                    line_number=b.line_start,
                    code=source_lines[b.line_start - 1] if 1 <= b.line_start <= len(source_lines) else "",
                    explanation=b.explanation,
                )
                for b in validated_blocks
            ]
            structured_output = StructuredExplanationOutput(
                summary=legacy_llm_result.summary,
                line_explanations=line_expls,
                concepts=[ConceptItem(name=c.concept, explanation=c.definition) for c in legacy_llm_result.concepts],
                issues=[],
                execution_walkthrough=legacy_llm_result.algorithm_steps,
                key_takeaways=[],
                suggested_improvements=legacy_llm_result.hints,
                uncertainty_notes=[],
            )
        elif raw_llm_output:
            structured_output, validation_error = self.validator.validate_and_sanitize(
                raw_llm_output, code
            )

        # Safe Retry Strategy
        if validation_error and not structured_output and not legacy_llm_result:
            logger.warning(f"Initial LLM output invalid ({validation_error}). Attempting safe retry...")
            retry_sys = sys_prompt + f"\n\nPREVIOUS OUTPUT FAILED VALIDATION: {validation_error}. You MUST return strictly valid JSON matching the schema."
            try:
                retry_raw = await self.llm_service.generate_chat_completion(
                    system_prompt=retry_sys,
                    user_prompt=user_prompt,
                    temperature=0.1,
                    json_mode=True,
                )
                structured_output, validation_error = self.validator.validate_and_sanitize(
                    retry_raw, code
                )
            except Exception as e:
                logger.error(f"Retry attempt failed: {e}")
                validation_error = str(e)


        # Safe Fallback Strategy if still invalid or failed
        if not structured_output:
            logger.warning(f"Employing deterministic fallback synthesizer due to: {validation_error}")
            structured_output = self.validator.synthesize_fallback(
                code=code,
                language=resolved_lang,
                mode=norm_mode,
                ast_result=ast_result,
                trace_result=trace_result,
                rag_citations=rag_sources,
                failure_reason=validation_error or "LLM generation unavailable",
            )

        # ── 8.5 Deterministic Explanation Validation & Grounding ──────
        val_result = self.validator.validate_grounding(
            structured=structured_output,
            code=code,
            ast_result=ast_result,
        )

        # If invalid claims or references detected, attempt 1 regeneration with feedback
        if not val_result.valid and raw_llm_output:
            logger.warning(f"Grounding validation detected issues ({len(val_result.unsupported_claims)} unsupported claims, {len(val_result.invalid_references)} invalid lines). Requesting regeneration...")
            feedback_items = []
            if val_result.invalid_references:
                feedback_items.append(f"Invalid non-existent line references: {val_result.invalid_references}")
            if val_result.unsupported_claims:
                feedback_items.append(f"Unsupported AST claims: {'; '.join(val_result.unsupported_claims)}")

            regen_sys = (
                sys_prompt
                + "\n\nCRITICAL VALIDATION FEEDBACK:\n"
                + "\n".join(feedback_items)
                + "\nPlease regenerate the explanation strictly adhering to verified source lines and AST constructs."
            )
            try:
                regen_raw = await self.llm_service.generate_chat_completion(
                    system_prompt=regen_sys,
                    user_prompt=user_prompt,
                    temperature=0.1,
                    json_mode=True,
                )
                regen_struct, regen_err = self.validator.validate_and_sanitize(regen_raw, code)
                if regen_struct:
                    regen_val = self.validator.validate_grounding(regen_struct, code, ast_result)
                    if regen_val.valid:
                        structured_output = regen_struct
                        val_result = regen_val
            except Exception as e:
                logger.warning(f"Regeneration attempt failed: {e}")

        # If still invalid, deterministically repair using verified AST structures
        if not val_result.valid:
            logger.info("Applying deterministic grounding repair to resolve unsupported claims and missing lines.")
            structured_output = self.validator.repair_explanation(
                structured=structured_output,
                validation=val_result,
                code=code,
                ast_result=ast_result,
            )
            val_result = self.validator.validate_grounding(
                structured=structured_output,
                code=code,
                ast_result=ast_result,
            )
            val_result.repaired = True

        # ── 9. Final Explanation Assembly & Backward Compatibility ────
        blocks: list[BlockExplanation] = []
        if legacy_validated_blocks is not None:
            blocks = legacy_validated_blocks
        elif structured_output.line_explanations:

            # Group or map line explanations to blocks
            blocks = [
                BlockExplanation(
                    title=f"Line {item.line_number}",
                    explanation=item.explanation,
                    line_start=item.line_number,
                    line_end=item.line_number,
                )
                for item in structured_output.line_explanations
            ]

        elif ast_result and ast_result.blocks:
            blocks = [
                BlockExplanation(
                    title=b.title,
                    explanation=f"Block '{b.title}' covering lines {b.line_start} to {b.line_end}.",
                    line_start=b.line_start,
                    line_end=b.line_end,
                )
                for b in ast_result.blocks
            ]

        concept_tags = [
            ConceptTag(concept=c.name, definition=c.explanation)
            for c in structured_output.concepts
        ]

        time_comp = "O(n)"
        space_comp = "O(1)"
        if ast_result:
            if ast_result.complexity_score > 8:
                time_comp = "O(n^2) / High Branching"
            elif ast_result.complexity_score > 3:
                time_comp = "O(n) / Multi-Branch"
            else:
                time_comp = "O(1) / Linear"

        complexity = AlgorithmComplexity(
            time_complexity=time_comp,
            space_complexity=space_comp,
            explanation=f"Based on cyclomatic complexity score {ast_result.complexity_score if ast_result else 1} and nesting depth {ast_result.max_nesting_depth if ast_result else 0}.",
        )

        hints = list(structured_output.suggested_improvements)
        for issue in structured_output.issues[:2]:
            if issue.suggested_fix:
                hints.append(f"[{issue.severity.upper()}] {issue.description} -> Fix: {issue.suggested_fix}")

        # ── 10. Persistence (Optional) ────────────────────────────────
        record_id = None
        created_at = None
        if request.save_history and self.repo is not None:
            try:
                sub = self.repo.save_full_submission(
                    code=code,
                    language=resolved_lang,
                    level=norm_mode,
                    ast_summary=json.dumps(ast_result.model_dump()) if ast_result else None,
                    llm_result=LLMExplanationResult(
                        summary=structured_output.summary,
                        blocks=blocks,
                        concepts=concept_tags,
                        algorithm_steps=structured_output.execution_walkthrough,
                        complexity=complexity,
                        hints=hints,
                    ),
                    quiz_response=None,
                    user_id=request.user_id,
                )
                record_id = sub.id
                created_at = sub.created_at
            except Exception as e:
                logger.error(f"Failed to persist submission to database: {e}")

        return ExplainCodeResponse(
            id=record_id,
            language=resolved_lang,
            level=request.level,
            summary=structured_output.summary,
            blocks=blocks,
            concepts=concept_tags,
            algorithm_steps=structured_output.execution_walkthrough,
            complexity=complexity,
            hints=hints,
            ast_analysis=ast_result,
            rag_sources=rag_sources,
            rag_context_used=rag_context_used,
            structured_output=structured_output,
            line_explanations=structured_output.line_explanations,
            issues=structured_output.issues,
            execution_walkthrough=structured_output.execution_walkthrough,
            key_takeaways=structured_output.key_takeaways,
            suggested_improvements=structured_output.suggested_improvements,
            uncertainty_notes=structured_output.uncertainty_notes,
            execution_trace=trace_result,
            explanation_mode=norm_mode,
            validation_result=val_result,
            created_at=created_at,
        )
