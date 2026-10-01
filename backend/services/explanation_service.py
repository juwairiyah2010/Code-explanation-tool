"""Orchestration service coordinating language detection, AST parsing, LLM prompt synthesis, and repository storage."""

from sqlalchemy.orm import Session
from backend.core.logging import logger
from backend.repositories.submission_repo import SubmissionRepository
from backend.schemas.explanation import (
    CodeAnalysisResponse,
    ExplainCodeRequest,
    ExplainCodeResponse,
)
from backend.services.detector import detect_language
from backend.services.llm import get_llm_service
from backend.services.parsers import get_parser


class ExplanationService:
    """Service that processes code analysis and explanations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = SubmissionRepository(db)
        self.llm = get_llm_service()

    def analyze_code_ast(
        self,
        code: str,
        language: str = "auto",
        filename: str | None = None,
    ) -> CodeAnalysisResponse:
        """Detect language if needed and run language-specific parser to extract constructs, rules, and blocks."""
        # 1. Resolve language
        if language.lower() in ("auto", "unknown", ""):
            detection = detect_language(code, filename=filename)
            resolved_lang = detection.language if detection.language != "unknown" else "python"
            method = detection.method
        else:
            detection = detect_language(code, filename=filename, explicit_language=language)
            resolved_lang = detection.language
            method = detection.method

        parser = get_parser(resolved_lang)
        return parser.parse(code, detection_method=method)

    async def explain_code(self, request: ExplainCodeRequest) -> ExplainCodeResponse:
        """Analyze code, generate AI explanation, optionally save to database, and return response."""
        logger.info(f"Processing explanation for language: {request.language}, style: {request.level}")

        # 1. AST analysis & language detection
        ast_result: CodeAnalysisResponse | None = None
        ast_summary_context: str | None = None

        if request.include_ast_analysis:
            ast_result = self.analyze_code_ast(request.code, request.language, request.filename)
            resolved_lang = ast_result.language
            ast_summary_context = (
                f"Functions: {[f.name for f in ast_result.constructs.functions]}, "
                f"Classes: {[c.name for c in ast_result.constructs.classes]}, "
                f"Loops: {len(ast_result.constructs.loops)}, "
                f"Conditions: {len(ast_result.constructs.conditions)}, "
                f"Assignments: {len(ast_result.constructs.assignments)}, "
                f"Complexity Score: {ast_result.complexity_score}, "
                f"Max Nesting: {ast_result.max_nesting_depth}"
            )
        else:
            detection = detect_language(request.code, filename=request.filename, explicit_language=request.language)
            resolved_lang = detection.language if detection.language != "unknown" else "python"

                # 2. Hybrid LLM explanation generation
        required_blocks = ast_result.blocks if ast_result and ast_result.blocks else []
        
        llm_output = await self.llm.generate_explanation(
            code=request.code,
            language=resolved_lang,
            level=request.level,
            ast_context=ast_summary_context,
            required_blocks=required_blocks,
        )

        # 2.5 Coverage Validator & Retry Logic
        max_lines = len(request.code.splitlines())
        
        def validate_blocks(blocks):
            validated = []
            for b in blocks:
                if b.line_start < 1: b.line_start = 1
                if b.line_end > max_lines: b.line_end = max_lines
                validated.append(b)
            return validated
        
        validated_blocks = validate_blocks(llm_output.blocks)
        
        if required_blocks:
            covered_titles = {b.title for b in validated_blocks}
            missing_blocks = [rb for rb in required_blocks if rb.title not in covered_titles]
            
            retry_count = 0
            max_retries = 2
            
            while missing_blocks and retry_count < max_retries:
                logger.warning(f"Missing explanations for {len(missing_blocks)} blocks. Retrying...")
                retry_output = await self.llm.generate_explanation(
                    code=request.code,
                    language=resolved_lang,
                    level=request.level,
                    ast_context=ast_summary_context,
                    required_blocks=missing_blocks,
                )
                
                new_blocks = validate_blocks(retry_output.blocks)
                validated_blocks.extend(new_blocks)
                
                covered_titles = {b.title for b in validated_blocks}
                missing_blocks = [rb for rb in required_blocks if rb.title not in covered_titles]
                retry_count += 1
                
            if missing_blocks:
                llm_output.hints.append(f"Warning: Could not generate explanations for some blocks: {', '.join(b.title for b in missing_blocks)}")

            # Merge validated results in source order
            validated_blocks.sort(key=lambda b: (b.line_start, b.line_end))
        else:
            # If no AST blocks, just use what LLM gave
            validated_blocks.sort(key=lambda b: (b.line_start, b.line_end))

        from backend.services.llm.base import LLMExplanationResult
        llm_output = LLMExplanationResult(
            summary=llm_output.summary,
            blocks=validated_blocks,
            concepts=llm_output.concepts,
            algorithm_steps=llm_output.algorithm_steps,
            complexity=llm_output.complexity,
            hints=llm_output.hints
        )


        # 3. Optional DB persistence
        record_id = None
        created_at = None
        if request.save_history:
            import json
            
            sub = self.repo.save_full_submission(
                code=request.code,
                language=resolved_lang,
                level=request.level,
                ast_summary=json.dumps(ast_result.model_dump()) if ast_result else None,
                llm_result=llm_output,
                quiz_response=None # Could attach quiz later if integrated
            )
            record_id = sub.id
            created_at = sub.created_at

        return ExplainCodeResponse(
            id=record_id,
            language=resolved_lang,
            level=request.level,
            summary=llm_output.summary,
            blocks=llm_output.blocks,
            concepts=llm_output.concepts,
            algorithm_steps=llm_output.algorithm_steps,
            complexity=llm_output.complexity,
            hints=llm_output.hints,
            ast_analysis=ast_result,
            created_at=created_at,
        )
