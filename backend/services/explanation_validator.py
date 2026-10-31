"""Deterministic Explanation Validation Layer.

Enforces code grounding, source-line verification, AST construct validation,
static-finding consistency, and coverage calculation without relying on a secondary LLM.
"""

import json
import re
from backend.core.logging import logger
from backend.schemas.explanation import (
    CodeAnalysisResponse,
    ConceptItem,
    ExplanationValidationResult,
    IssueItem,
    LineExplanationItem,
    StructuredExplanationOutput,
)
from backend.schemas.rag import RAGSourceCitation
from backend.schemas.trace import TraceResponse


class ExplanationValidator:
    """Deterministic validator verifying that generated explanations are faithfully grounded in code."""

    @staticmethod
    def extract_json_text(raw_text: str) -> str:
        """Strip markdown code fences and extract outermost JSON object."""
        text = raw_text.strip()
        if text.startswith("```"):
            fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if fence_match:
                text = fence_match.group(1).strip()

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
        """Validate raw text against Pydantic schema and enforce source line bounds."""
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

        source_lines = code.splitlines()
        total_lines = len(source_lines)
        validated_lines: list[LineExplanationItem] = []
        discarded_lines: list[int] = []

        for item in structured.line_explanations:
            if item.line_number < 1 or item.line_number > total_lines:
                discarded_lines.append(item.line_number)
                continue

            if not item.code:
                item.code = source_lines[item.line_number - 1]
            validated_lines.append(item)

        validated_lines.sort(key=lambda x: x.line_number)
        structured.line_explanations = validated_lines

        if discarded_lines:
            note = (
                f"Discarded {len(discarded_lines)} line explanations referencing non-existent lines: "
                f"{discarded_lines} (valid source range: 1-{total_lines})."
            )
            logger.warning(note)
            structured.uncertainty_notes.append(note)

        for issue in structured.issues:
            if issue.line_number is not None and (issue.line_number < 1 or issue.line_number > total_lines):
                issue.line_number = None

        return structured, None

    def validate_grounding(
        self,
        structured: StructuredExplanationOutput,
        code: str,
        ast_result: CodeAnalysisResponse | None = None,
    ) -> ExplanationValidationResult:
        """Run deterministic grounding checks against source code and AST constructs."""
        source_lines = code.splitlines()
        total_lines = len(source_lines)

        significant_lines = {
            i + 1
            for i, line in enumerate(source_lines)
            if line.strip() and not line.strip().startswith(("#", "//", "/*", "*"))
        }

        referenced_lines_set: set[int] = set()
        invalid_references_set: set[int] = set()
        unsupported_claims: list[str] = []
        warnings: list[str] = []

        # ── 1. Source-line and Referenced-line Validation ─────────────
        for item in structured.line_explanations:
            if item.line_number < 1 or item.line_number > total_lines:
                invalid_references_set.add(item.line_number)
            else:
                referenced_lines_set.add(item.line_number)

        for issue in structured.issues:
            if issue.line_number is not None:
                if issue.line_number < 1 or issue.line_number > total_lines:
                    invalid_references_set.add(issue.line_number)
                else:
                    referenced_lines_set.add(issue.line_number)

        # Extract textual line mentions (e.g., "Line 4", "line 12")
        all_text = " ".join([
            structured.summary,
            " ".join(structured.execution_walkthrough),
            " ".join(structured.key_takeaways),
        ])
        for line_match in re.finditer(r"\b(?:[Ll]ine|[Ll])\s*(\d+)\b", all_text):
            ln = int(line_match.group(1))
            if ln < 1 or ln > total_lines:
                invalid_references_set.add(ln)
            else:
                referenced_lines_set.add(ln)

        # ── 2. AST Construct Map Building ─────────────────────────────
        loop_lines: set[int] = set()
        loop_start_lines: set[int] = set()
        func_lines: set[int] = set()
        func_start_lines: set[int] = set()
        class_lines: set[int] = set()
        class_start_lines: set[int] = set()
        cond_lines: set[int] = set()
        import_lines: set[int] = set()

        known_identifiers: set[str] = set()

        if ast_result and ast_result.constructs:
            c = ast_result.constructs
            for f in c.functions:
                func_start_lines.add(f.line_start)
                known_identifiers.add(f.name)
                for line_idx in range(f.line_start, f.line_end + 1):
                    func_lines.add(line_idx)

            for cl in c.classes:
                class_start_lines.add(cl.line_start)
                known_identifiers.add(cl.name)
                for line_idx in range(cl.line_start, cl.line_end + 1):
                    class_lines.add(line_idx)

            for lp in c.loops:
                loop_start_lines.add(lp.line_start)
                for line_idx in range(lp.line_start, lp.line_end + 1):
                    loop_lines.add(line_idx)

            for cond in c.conditions:
                for line_idx in range(cond.line_start, cond.line_end + 1):
                    cond_lines.add(line_idx)

            for imp in c.imports:
                known_identifiers.add(imp.module)
                for name in imp.names:
                    known_identifiers.add(name)
                for line_idx in range(imp.line_start, imp.line_end + 1):
                    import_lines.add(line_idx)

            for asgn in c.assignments:
                for target in asgn.targets:
                    known_identifiers.add(target)

        # Fallback to syntax blocks if constructs are sparse
        if ast_result and ast_result.blocks:
            for b in ast_result.blocks:
                if b.block_type == "function":
                    func_start_lines.add(b.line_start)
                    for idx in range(b.line_start, b.line_end + 1): func_lines.add(idx)
                elif b.block_type == "loop":
                    loop_start_lines.add(b.line_start)
                    for idx in range(b.line_start, b.line_end + 1): loop_lines.add(idx)
                elif b.block_type == "branch":
                    for idx in range(b.line_start, b.line_end + 1): cond_lines.add(idx)
                elif b.block_type == "imports":
                    for idx in range(b.line_start, b.line_end + 1): import_lines.add(idx)

        # ── 3. AST Construct Validation ───────────────────────────────
        for item in structured.line_explanations:
            ln = item.line_number
            if ln < 1 or ln > total_lines:
                continue

            expl_lower = item.explanation.lower()

            # Loop claim validation
            if re.search(r"\b(loop|for\s+loop|while\s+loop|iterat(?:es?|ion))\b", expl_lower):
                if ln not in loop_lines:
                    unsupported_claims.append(
                        f"Line {ln} is claimed to contain a loop ('{item.explanation}'), but AST analysis confirmed no loop construct exists at line {ln}."
                    )

            # Function definition claim validation
            if re.search(r"\b(defines?\s+(?:a\s+)?function|function\s+definition|function\s+declaration)\b", expl_lower):
                if ln not in func_start_lines:
                    unsupported_claims.append(
                        f"Line {ln} is claimed to define a function, but no function definition starts at line {ln}."
                    )

            # Class definition claim validation
            if re.search(r"\b(defines?\s+(?:a\s+)?class|class\s+definition)\b", expl_lower):
                if ln not in class_start_lines:
                    unsupported_claims.append(
                        f"Line {ln} is claimed to define a class, but no class definition starts at line {ln}."
                    )

            # Import statement claim validation
            if re.search(r"\b(imports?\s+(?:module|package|library)|import\s+statement)\b", expl_lower):
                if ln not in import_lines:
                    unsupported_claims.append(
                        f"Line {ln} is claimed to be an import statement, but line {ln} is not an import."
                    )

            # Conditional claim validation
            if re.search(r"\b(conditional\s+statement|if\s+condition|conditional\s+branch)\b", expl_lower):
                if ln not in cond_lines:
                    unsupported_claims.append(
                        f"Line {ln} is claimed to contain a conditional branch, but no condition exists at line {ln}."
                    )

        # Check explicit text claims of the form: "Line X contains a loop"
        claim_patterns = [
            (r"\b(?:[Ll]ine|[Ll])\s*(\d+)\s*(?:contains|is|has|defines)\s*(?:a|an)?\s*(?:for\s+|while\s+)?loop\b", loop_lines, "loop"),
            (r"\b(?:[Ll]ine|[Ll])\s*(\d+)\s*(?:defines|declares)\s*(?:a|an)?\s*function\b", func_start_lines, "function"),
            (r"\b(?:[Ll]ine|[Ll])\s*(\d+)\s*(?:defines|declares)\s*(?:a|an)?\s*class\b", class_start_lines, "class"),
            (r"\b(?:[Ll]ine|[Ll])\s*(\d+)\s*(?:contains|is|has|defines)\s*(?:a|an)?\s*(?:conditional|if\s+statement)\b", cond_lines, "conditional"),
            (r"\b(?:[Ll]ine|[Ll])\s*(\d+)\s*(?:contains|is|has|defines)\s*(?:a|an)?\s*import\b", import_lines, "import"),
        ]
        for pattern, valid_lines, construct_name in claim_patterns:
            for match in re.finditer(pattern, all_text, re.IGNORECASE):
                claim_line = int(match.group(1))
                if 1 <= claim_line <= total_lines and claim_line not in valid_lines:
                    claim_desc = (
                        f"Text claims Line {claim_line} contains a {construct_name}, "
                        f"but AST analysis verified no {construct_name} on line {claim_line}."
                    )
                    if claim_desc not in unsupported_claims:
                        unsupported_claims.append(claim_desc)

        # ── 4. Static-Finding Consistency Checking ────────────────────
        if ast_result:
            deterministic_finding_lines = {
                f.line_number
                for f in getattr(ast_result, "findings", []) or getattr(ast_result, "static_hints", [])
            }
            for issue in structured.issues:
                if issue.line_number and issue.line_number not in deterministic_finding_lines:
                    warnings.append(
                        f"Issue reported at line {issue.line_number} ('{issue.description}') is an LLM inference not present in deterministic static analysis findings."
                    )

        # ── 5. Explanation Coverage Calculation ───────────────────────
        covered_significant = referenced_lines_set & significant_lines
        coverage_score = (
            round(len(covered_significant) / max(1, len(significant_lines)), 2)
            if significant_lines
            else 1.0
        )

        if coverage_score < 0.5:
            warnings.append(
                f"Low code coverage ({int(coverage_score * 100)}%): only {len(covered_significant)} of {len(significant_lines)} significant lines are referenced."
            )

        # ── 6. Determine Grounding Confidence Level ───────────────────
        is_valid = len(invalid_references_set) == 0 and len(unsupported_claims) == 0

        if is_valid and coverage_score >= 0.7 and len(warnings) == 0:
            grounding_level = "High"
        elif is_valid and coverage_score >= 0.4:
            grounding_level = "Moderate"
        else:
            grounding_level = "Low"

        return ExplanationValidationResult(
            valid=is_valid,
            coverage_score=coverage_score,
            referenced_lines=sorted(referenced_lines_set),
            invalid_references=sorted(invalid_references_set),
            unsupported_claims=unsupported_claims,
            warnings=warnings,
            grounding_level=grounding_level,
            repaired=False,
        )

    def repair_explanation(
        self,
        structured: StructuredExplanationOutput,
        validation: ExplanationValidationResult,
        code: str,
        ast_result: CodeAnalysisResponse | None = None,
    ) -> StructuredExplanationOutput:
        """Deterministically repair validation defects using verified AST constructs and source code."""
        source_lines = code.splitlines()
        total_lines = len(source_lines)
        repaired_lines: list[LineExplanationItem] = []

        # Remove invalid references
        for item in structured.line_explanations:
            if item.line_number < 1 or item.line_number > total_lines:
                continue

            # Deterministic repair for unsupported construct claims
            expl = item.explanation
            code_line = source_lines[item.line_number - 1].strip()

            # Check if this line had an unsupported claim
            matching_claims = [
                c for c in validation.unsupported_claims if f"Line {item.line_number}" in c
            ]
            if matching_claims:
                # Rewrite explanation to accurately reflect AST reality on this line
                if code_line.startswith(("def ", "function ")):
                    expl = f"Defines callable function header: {code_line}"
                elif code_line.startswith("class "):
                    expl = f"Defines object class header: {code_line}"
                elif code_line.startswith(("import ", "from ")):
                    expl = f"Import declaration: {code_line}"
                elif code_line.startswith(("if ", "elif ", "else:")):
                    expl = f"Evaluates conditional branch: {code_line}"
                elif code_line.startswith(("for ", "while ")):
                    expl = f"Executes iteration loop: {code_line}"
                elif code_line.startswith("return "):
                    expl = f"Returns computed expression: {code_line}"
                else:
                    expl = f"Executes line {item.line_number} statement: {code_line}"

            repaired_lines.append(
                LineExplanationItem(
                    line_number=item.line_number,
                    code=source_lines[item.line_number - 1],
                    explanation=expl,
                    uncertainty_note="Repaired deterministically against AST" if matching_claims else item.uncertainty_note,
                )
            )

        # Supplement missing coverage from AST blocks if coverage is sparse
        covered_lines = {it.line_number for it in repaired_lines}
        if ast_result and ast_result.blocks:
            for b in ast_result.blocks:
                start = max(1, min(b.line_start, total_lines))
                end = max(start, min(b.line_end, total_lines))
                for line_idx in range(start, end + 1):
                    if line_idx not in covered_lines and source_lines[line_idx - 1].strip():
                        repaired_lines.append(
                            LineExplanationItem(
                                line_number=line_idx,
                                code=source_lines[line_idx - 1],
                                explanation=f"Part of {b.block_type} block '{b.title}'.",
                                uncertainty_note="Supplemented from AST syntax blocks for coverage.",
                            )
                        )
                        covered_lines.add(line_idx)

        repaired_lines.sort(key=lambda x: x.line_number)
        structured.line_explanations = repaired_lines

        # Remove invalid references in issues
        structured.issues = [
            iss for iss in structured.issues
            if iss.line_number is None or (1 <= iss.line_number <= total_lines)
        ]

        # Sanitize invalid line references in textual narrative fields
        for bad_ln in validation.invalid_references:
            bad_pattern = re.compile(rf"\b(?:[Ll]ine|[Ll])\s*{bad_ln}\b", re.IGNORECASE)
            structured.summary = bad_pattern.sub("unreferenced step", structured.summary)
            structured.execution_walkthrough = [
                bad_pattern.sub("unreferenced step", step)
                for step in structured.execution_walkthrough
            ]
            structured.key_takeaways = [
                bad_pattern.sub("unreferenced step", t)
                for t in structured.key_takeaways
            ]

        repair_notes = []
        if validation.invalid_references:
            repair_notes.append(
                f"Discarded invalid line references: {validation.invalid_references}."
            )
        if validation.unsupported_claims:
            repair_notes.append(
                f"Corrected {len(validation.unsupported_claims)} unsupported construct claims using verified AST structures."
            )

        if repair_notes:
            structured.uncertainty_notes.append(
                "Deterministic Grounding Repair Applied: " + " ".join(repair_notes)
            )

        return structured

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
