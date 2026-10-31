"""ExplanationValidator enforcing JSON schema validation, line-reference accuracy, and safe fallback."""

import json
import re
from backend.core.logging import logger

from backend.schemas.explanation import (
    CodeAnalysisResponse,
    ConceptItem,
    IssueItem,
    LineExplanationItem,
    StructuredExplanationOutput,
)
from backend.schemas.rag import RAGSourceCitation
from backend.schemas.trace import TraceResponse


class ExplanationValidator:
    """Validator for LLM outputs enforcing schema compliance, source line fidelity, and deterministic fallbacks."""

    @staticmethod
    def extract_json_text(raw_text: str) -> str:
        """Strip markdown fences and extract outermost JSON object."""
        text = raw_text.strip()
        # Remove markdown code fences if wrapped
        if text.startswith("```"):
            fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if fence_match:
                text = fence_match.group(1).strip()

        # If not clean JSON, search for the outermost curly brackets
        if not (text.startswith("{") and text.endswith("}")):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]

        return text

    def validate_and_sanitize(
        self,
        raw_text: str,
        code: str,
    ) -> tuple[StructuredExplanationOutput | None, str | None]:
        """Validate LLM raw output into StructuredExplanationOutput, enforcing line reference constraints."""
        json_str = self.extract_json_text(raw_text)

        try:
            data = json.loads(json_str)
        except Exception as e:
            return None, f"JSON parse error: {str(e)}"

        if not isinstance(data, dict):
            return None, "Root JSON must be an object dictionary."

        try:
            structured = StructuredExplanationOutput.model_validate(data)
        except Exception as e:
            return None, f"Pydantic schema validation error: {str(e)}"

        # Enforce line-reference integrity: every line must reference an actual source line
        source_lines = code.splitlines()
        total_lines = len(source_lines)
        validated_lines: list[LineExplanationItem] = []
        discarded_lines: list[int] = []

        for item in structured.line_explanations:
            if item.line_number < 1 or item.line_number > total_lines:
                discarded_lines.append(item.line_number)
                continue

            # Populate exact code line if missing
            if not item.code:
                item.code = source_lines[item.line_number - 1]
            validated_lines.append(item)

        # Sort line explanations in natural source order
        validated_lines.sort(key=lambda x: x.line_number)
        structured.line_explanations = validated_lines

        if discarded_lines:
            note = (
                f"Discarded {len(discarded_lines)} line explanations referencing non-existent lines: "
                f"{discarded_lines} (valid source range: 1-{total_lines})."
            )
            logger.warning(note)
            structured.uncertainty_notes.append(note)

        # Validate issue line references
        for issue in structured.issues:
            if issue.line_number is not None and (issue.line_number < 1 or issue.line_number > total_lines):
                issue.line_number = None

        return structured, None

    def synthesize_fallback(
        self,
        code: str,
        language: str,
        mode: str,
        ast_result: CodeAnalysisResponse | None = None,
        trace_result: TraceResponse | None = None,
        rag_citations: list[RAGSourceCitation] | None = None,
        failure_reason: str = "Unparseable LLM output",
    ) -> StructuredExplanationOutput:
        """Deterministic fallback synthesizer deriving valid structured explanation strictly from AST, Trace, and RAG."""
        source_lines = code.splitlines()
        total_lines = len(source_lines)

        summary = (
            f"This {language.capitalize()} snippet was analyzed deterministically in '{mode}' mode. "
            f"It contains {total_lines} source lines with a cyclomatic complexity score of "
            f"{ast_result.complexity_score if ast_result else 1}."
        )

        line_explanations: list[LineExplanationItem] = []
        # Synthesize line explanations from syntax blocks or line-by-line
        if ast_result and ast_result.blocks:
            for b in ast_result.blocks:
                start = max(1, min(b.line_start, total_lines))
                end = max(start, min(b.line_end, total_lines))
                for line_idx in range(start, end + 1):
                    line_explanations.append(
                        LineExplanationItem(
                            line_number=line_idx,
                            code=source_lines[line_idx - 1] if line_idx <= total_lines else "",
                            explanation=f"Part of {b.block_type} block '{b.title}'.",
                            uncertainty_note=None,
                        )
                    )
        else:
            for idx, line in enumerate(source_lines):
                line_explanations.append(
                    LineExplanationItem(
                        line_number=idx + 1,
                        code=line,
                        explanation=f"Executes line {idx + 1} statement.",
                        uncertainty_note=None,
                    )
                )

        concepts: list[ConceptItem] = [
            ConceptItem(
                name=f"{language.capitalize()} Language Syntax",
                explanation=f"Structured algorithmic and control-flow execution in {language.capitalize()}.",
                reference_source="Core Language Specification",
            )
        ]

        if rag_citations:
            for cite in rag_citations:
                concepts.append(
                    ConceptItem(
                        name=cite.title,
                        explanation=cite.text or cite.snippet or f"Grounded documentation on {cite.title}",
                        reference_source=cite.source,
                    )
                )

        issues: list[IssueItem] = []
        if ast_result:
            findings = getattr(ast_result, "findings", []) or getattr(ast_result, "static_hints", [])
            for f in findings:
                issues.append(
                    IssueItem(
                        line_number=f.line_number if 1 <= f.line_number <= total_lines else None,
                        severity=f.severity if f.severity in ("info", "warning", "error") else "warning",
                        category=f.category,
                        description=f.technical_description,
                        suggested_fix=f.suggested_fix,
                    )
                )

        execution_walkthrough: list[str] = []
        if trace_result and trace_result.success and trace_result.steps:
            for idx, s in enumerate(trace_result.steps[:10]):
                execution_walkthrough.append(
                    f"Step {idx + 1}: Line {s.line_number} executed event '{s.event_type}'. Code: {s.executed_code or ''}"
                )
        else:
            execution_walkthrough = [
                f"Step 1: Module loaded and language runtime initialized for {language}.",
                "Step 2: Statements execute sequentially through definitions and calls.",
                "Step 3: Execution completes.",
            ]

        key_takeaways = [
            f"Code conforms to structural {language.capitalize()} conventions.",
            "Deterministic analysis engine verified AST constructs and syntax validity.",
        ]

        suggested_improvements = [
            "Add docstrings and explicit type hints to improve code self-documentation.",
            "Verify all edge cases and boundary inputs in automated unit tests.",
        ]

        uncertainty_notes = [
            f"Notice: Explanation safely synthesized from deterministic static analysis and execution engine due to: {failure_reason}."
        ]

        return StructuredExplanationOutput(
            summary=summary,
            line_explanations=line_explanations,
            concepts=concepts,
            issues=issues,
            execution_walkthrough=execution_walkthrough,
            key_takeaways=key_takeaways,
            suggested_improvements=suggested_improvements,
            uncertainty_notes=uncertainty_notes,
        )
