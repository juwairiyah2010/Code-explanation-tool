"""PromptBuilder constructing structured context from deterministic analysis, tracing, and RAG."""

import json
from backend.schemas.explanation import CodeAnalysisResponse, LearnerProfile

from backend.schemas.rag import RAGSourceCitation
from backend.schemas.trace import TraceResponse


MODE_INSTRUCTIONS: dict[str, str] = {
    "absolute beginner": (
        "Target Audience: Absolute Beginner (zero programming experience).\n"
        "Tone & Style: Use relatable real-world analogies, friendly language, and avoid technical jargon. "
        "Explain what the computer is doing step-by-step as if explaining to a curious student."
    ),
    "beginner": (
        "Target Audience: Beginner developer.\n"
        "Tone & Style: Explain programming concepts and syntax clearly. Assume familiarity with basic terminology "
        "(variables, functions, loops) while guiding on best practices and clean code structure."
    ),
    "intermediate": (
        "Target Audience: Intermediate software engineer.\n"
        "Tone & Style: Focus on algorithmic logic, idiomatic design patterns, efficiency, and common edge cases."
    ),
    "expert": (
        "Target Audience: Senior software architect and staff engineer.\n"
        "Tone & Style: Conduct a deep architectural and systems-level review. Discuss runtime mechanics, "
        "memory allocation/garbage collection implications, language specifications, and trade-offs."
    ),
    "line-by-line": (
        "Target Audience: Developer needing an exhaustive line-by-line walkthrough.\n"
        "Tone & Style: Analyze every single line of code in sequential order. Explain the exact operational effect "
        "of each line on the execution environment and memory."
    ),
    "debugging": (
        "Target Audience: Developer diagnosing a bug or defect.\n"
        "Tone & Style: Focus intensely on bug hunting, boundary condition failures, off-by-one errors, "
        "unexpected data types, unhandled exceptions, and defensive programming countermeasures."
    ),
    "security": (
        "Target Audience: Application Security Engineer & Developer.\n"
        "Tone & Style: Focus on threat modeling, vulnerability assessment, malicious input handling, "
        "injection vulnerabilities, sensitive data leakage, and security hardening recommendations."
    ),
    "performance": (
        "Target Audience: Performance Optimization Engineer.\n"
        "Tone & Style: Focus on time and space complexity, resource bottlenecks, loop overhead, "
        "cache locality, memory churn, and concrete algorithmic speedups."
    ),
}

JSON_SCHEMA_INSTRUCTIONS = """
You MUST return a single, valid JSON object with EXACTLY this structure:
{
  "summary": "Clear, comprehensive summary of what the code does according to the requested mode.",
  "line_explanations": [
    {
      "line_number": 1,
      "code": "exact code line",
      "explanation": "Detailed explanation of this specific line.",
      "uncertainty_note": null
    }
  ],
  "concepts": [
    {
      "name": "Concept name",
      "explanation": "Educational explanation of the concept and how it is used here.",
      "reference_source": "Attributed documentation source if applicable"
    }
  ],
  "issues": [
    {
      "line_number": 1,
      "severity": "warning",
      "category": "code quality",
      "description": "Specific issue or potential bug.",
      "suggested_fix": "How to resolve this issue."
    }
  ],
  "execution_walkthrough": [
    "Step 1: ...",
    "Step 2: ..."
  ],
  "key_takeaways": [
    "Key takeaway 1",
    "Key takeaway 2"
  ],
  "suggested_improvements": [
    "Concrete actionable improvement 1",
    "Concrete actionable improvement 2"
  ],
  "uncertainty_notes": []
}

CRITICAL RULES:
1. Return ONLY the raw JSON object. Do not enclose it in backticks, conversational preamble, or markdown tags.
2. The code has {total_lines} total lines. Every item in 'line_explanations' MUST reference an actual line number between 1 and {total_lines}. NEVER invent, hallucinate, or reference non-existent line numbers.
3. If any aspect of the code, runtime behavior, or context is uncertain or cannot be definitively verified, explicitly state your uncertainty in 'uncertainty_notes' or within the specific explanation's 'uncertainty_note'.
4. Ground your explanations in the verified reference documentation and deterministic AST findings provided. Do not hallucinate external library behaviors.
"""


class PromptBuilder:
    """Service that compiles deterministic analysis and RAG artifacts into structured LLM prompts."""

    def normalize_mode(self, mode: str | None, level: str | None = None) -> str:
        """Normalize mode or legacy level to one of the 8 supported explanation modes."""
        candidate = (mode or level or "beginner").strip().lower().replace("_", " ").replace("-", " ")
        if "absolute" in candidate:
            return "absolute beginner"
        elif "line" in candidate:
            return "line-by-line"
        elif "debug" in candidate:
            return "debugging"
        elif "sec" in candidate:
            return "security"
        elif "perf" in candidate:
            return "performance"
        elif "expert" in candidate or "advanced" in candidate:
            return "expert"
        elif "inter" in candidate:
            return "intermediate"
        return "beginner"

    def format_code_with_line_numbers(self, code: str) -> str:
        """Format source code with explicit 1-indexed line numbers."""
        lines = code.splitlines()
        width = len(str(len(lines)))
        return "\n".join(f"{i + 1:>{width}} | {line}" for i, line in enumerate(lines))

    def format_ast_findings(self, ast_result: CodeAnalysisResponse | None) -> str:
        """Format AST constructs and static rule findings into structured markdown."""
        if not ast_result:
            return "No AST data available."

        parts: list[str] = []
        # Complexity & Structural metrics
        parts.append(
            f"- Cyclomatic Complexity: {ast_result.complexity_score} (Max Nesting Depth: {ast_result.max_nesting_depth})\n"
            f"- Functions: {ast_result.function_count}, Classes: {ast_result.class_count}, Imports: {ast_result.import_count}\n"
            f"- Lines of Code Breakdown: {json.dumps(ast_result.lines_of_code)}"
        )

        # Constructs
        if hasattr(ast_result, "constructs") and ast_result.constructs:
            c = ast_result.constructs
            if c.functions:
                funcs = [f"{f.name}({', '.join(f.parameters)}) [L{f.line_start}-L{f.line_end}]" for f in c.functions]
                parts.append(f"- Defined Functions: {'; '.join(funcs)}")
            if c.classes:
                classes = [f"{cls.name} [L{cls.line_start}-L{cls.line_end}]" for cls in c.classes]
                parts.append(f"- Defined Classes: {'; '.join(classes)}")
            if c.loops:
                loops = [f"{lp.loop_type} [L{lp.line_start}-L{lp.line_end}]" for lp in c.loops]
                parts.append(f"- Control Loops: {'; '.join(loops)}")

        # Deterministic rule findings
        findings = getattr(ast_result, "findings", []) or getattr(ast_result, "static_hints", [])
        if findings:
            parts.append("Deterministic Static Analysis Rule Findings:")
            for f in findings:
                parts.append(
                    f"  * [{f.severity.upper()}] L{f.line_number} {f.title} ({f.category}): {f.technical_description} "
                    f"| Remediation: {f.suggested_fix}"
                )

        return "\n".join(parts)

    def format_trace_result(self, trace_result: TraceResponse | None) -> str:
        """Format runtime execution trace into a step-by-step summary."""
        if not trace_result or not trace_result.success:
            if trace_result and trace_result.error:
                return f"Runtime Execution Note: Tracing encountered an error: {trace_result.error}"
            return "No execution trace available (static analysis only)."

        steps = trace_result.steps or []
        parts = [
            f"Execution Success: Completed {len(steps)} steps in {trace_result.execution_time:.3f}s.",
            f"Printed Output (stdout):\n{trace_result.output if trace_result.output.strip() else '(No printed output)'}",
        ]

        if steps:
            parts.append("Step-by-Step Runtime Events:")
            for idx, s in enumerate(steps[:15]):  # Up to 15 key steps
                var_changes = [f"{k}={v}" for k, v in s.changed_variables.items()]
                change_str = f" | Changed: {', '.join(var_changes)}" if var_changes else ""
                parts.append(
                    f"  {idx + 1}. [L{s.line_number} - {s.event_type}] {s.executed_code or ''}{change_str}"
                )
            if len(steps) > 15:
                parts.append(f"  ... ({len(steps) - 15} additional execution steps omitted for brevity)")

        if trace_result.final_state:
            parts.append(f"Final Variable State: {json.dumps(trace_result.final_state)}")

        return "\n".join(parts)

    def format_rag_context(self, rag_citations: list[RAGSourceCitation] | None, formatted_context: str | None = None) -> str:
        """Format verified reference documentation citations."""
        if formatted_context:
            return formatted_context
        if not rag_citations:
            return "No specific reference documentation retrieved."

        docs = []
        for c in rag_citations:
            snippet = c.text or c.snippet or ""
            docs.append(f"### [{c.title}] (Source: {c.source} | Topic: {c.topic})\n{snippet}")
        return "\n\n".join(docs)

    def build_prompts(
        self,
        code: str,
        language: str,
        mode: str = "beginner",
        ast_result: CodeAnalysisResponse | None = None,
        trace_result: TraceResponse | None = None,
        rag_citations: list[RAGSourceCitation] | None = None,
        rag_formatted_context: str | None = None,
        learner_profile: LearnerProfile | None = None,
    ) -> tuple[str, str]:
        """Compile complete (system_prompt, user_prompt) adhering to the 12 pipeline requirements."""
        norm_mode = self.normalize_mode(mode, learner_profile.level if learner_profile else None)
        mode_instruction = MODE_INSTRUCTIONS.get(norm_mode, MODE_INSTRUCTIONS["beginner"])
        total_lines = len(code.splitlines())

        system_prompt = (
            "You are the Core Code Explanation Engine of Code Lore, a rigorous pedagogical programming assistant.\n"
            "You must synthesize explanations strictly grounded in deterministic AST analysis, execution traces, "
            "and verified reference documentation.\n"
            + JSON_SCHEMA_INSTRUCTIONS.replace("{total_lines}", str(total_lines))
        )


        user_prompt_sections = [
            "# EXPLANATION REQUEST",
            f"**Programming Language**: {language}",

            f"**Requested Mode**: {norm_mode}",
            f"**Mode Guidelines**:\n{mode_instruction}",
            "",
            f"# SOURCE CODE (Total Lines: {total_lines})",
            "```" + language,
            self.format_code_with_line_numbers(code),
            "```",
            "",
            "# DETERMINISTIC AST & STATIC ANALYSIS FINDINGS",
            self.format_ast_findings(ast_result),
            "",
            "# RUNTIME EXECUTION TRACE",
            self.format_trace_result(trace_result),
            "",
            "# VERIFIED REFERENCE DOCUMENTATION",
            self.format_rag_context(rag_citations, rag_formatted_context),
            "",
            "# FINAL INSTRUCTION",
            f"Generate the complete explanation in {norm_mode} mode. Every line in 'line_explanations' MUST be within 1 and {total_lines}. Output ONLY the raw JSON object.",
        ]

        user_prompt = "\n".join(user_prompt_sections)
        return system_prompt, user_prompt
