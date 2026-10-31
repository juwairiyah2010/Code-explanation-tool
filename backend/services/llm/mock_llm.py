"""Mock LLM service providing realistic deterministic explanations for development & testing."""

import json
import re
from typing import Any
from backend.schemas.explanation import AlgorithmComplexity, BlockExplanation, ConceptTag
from backend.schemas.quiz import QuizResponse
from backend.services.llm.base import BaseLLMService, LLMExplanationResult




class MockLLMService(BaseLLMService):
    """Deterministic Mock LLM Service for local development and test suites."""

    def __init__(self):
        self.should_fail_json: bool = False
        self.simulate_hallucinated_lines: bool = False

    async def generate_structured_explanation(
        self,
        code: str,
        language: str = "python",
        mode: str = "beginner",
    ):
        """Deterministically produce a validated StructuredExplanationOutput instance."""
        from backend.services.prompt_builder import PromptBuilder
        from backend.services.parsers.python_parser import PythonCodeParser
        from backend.services.parsers.javascript_parser import JavaScriptCodeParser
        from backend.services.explanation_validator import ExplanationValidator

        builder = PromptBuilder()
        if language == "javascript":
            ast_res = JavaScriptCodeParser().parse(code)
        else:
            ast_res = PythonCodeParser().parse(code)

        sys_prompt, user_prompt = builder.build_prompts(
            code=code,
            language=language,
            ast_result=ast_res,
            mode=mode,
        )
        raw_json = await self.generate_chat_completion(sys_prompt, user_prompt)
        validator = ExplanationValidator()
        structured, err = validator.validate_and_sanitize(raw_json, code)
        if structured is None:
            raise ValueError(f"Failed to parse or validate structured explanation: {err}")
        return structured

    async def generate_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        json_mode: bool = True,
    ) -> str:
        """Deterministically simulate chat completions producing schema-compliant JSON."""
        if self.should_fail_json:
            return "INVALID JSON {{{ unclosed and broken"

        # Extract language
        lang_match = re.search(r"\*\*Programming Language\*\*:\s*([a-zA-Z0-9_]+)", user_prompt)
        language = lang_match.group(1).lower() if lang_match else "python"

        # Extract mode
        mode_match = re.search(r"\*\*Requested Mode\*\*:\s*([a-zA-Z0-9_\- ]+)", user_prompt)
        mode = mode_match.group(1).strip().lower() if mode_match else "beginner"

        # Extract total lines
        lines_match = re.search(r"\(Total Lines:\s*(\d+)\)", user_prompt)
        total_lines = int(lines_match.group(1)) if lines_match else 5

        # Extract code lines
        code_lines: list[tuple[int, str]] = []
        code_block_match = re.search(r"```" + language + r"\n([\s\S]*?)\n```", user_prompt)
        if code_block_match:
            for raw_line in code_block_match.group(1).splitlines():
                line_m = re.match(r"^\s*(\d+)\s*\|\s*(.*)$", raw_line)
                if line_m:
                    code_lines.append((int(line_m.group(1)), line_m.group(2)))

        if not code_lines:
            code_lines = [(i + 1, f"line {i + 1}") for i in range(total_lines)]

        # Line explanations
        line_explanations = []
        for line_num, code_text in code_lines:
            clean_code = code_text.strip()
            if not clean_code:
                expl = "Blank line separating code statements."
            elif clean_code.startswith(("def ", "function ")):
                expl = f"Defines callable function: {clean_code}."
            elif clean_code.startswith("class "):
                expl = f"Defines object-oriented class structure: {clean_code}."
            elif clean_code.startswith(("import ", "from ")):
                expl = f"Imports library module dependency: {clean_code}."
            elif clean_code.startswith(("if ", "elif ", "else:")):
                expl = f"Evaluates conditional branch logic: {clean_code}."
            elif clean_code.startswith(("for ", "while ")):
                expl = f"Executes iteration loop: {clean_code}."
            elif clean_code.startswith("return "):
                expl = f"Returns computed value: {clean_code}."
            else:
                expl = f"Executes statement: {clean_code}."

            line_explanations.append({
                "line_number": line_num,
                "code": code_text,
                "explanation": expl,
                "uncertainty_note": None,
            })

        if self.simulate_hallucinated_lines:
            # Add an illegal line out of range to test validator rejection
            line_explanations.append({
                "line_number": total_lines + 999,
                "code": "hallucinated_call()",
                "explanation": "This line does not exist in the source code.",
                "uncertainty_note": "Hallucinated line test",
            })

        summary = (
            f"This {language.capitalize()} snippet was analyzed under '{mode.title()}' mode. "
            f"It implements structured computation across {len(code_lines)} lines with deterministic execution logic."
        )

        concepts = [
            {
                "name": f"{language.capitalize()} Syntax & Constructs",
                "explanation": f"Core lexical and structural elements of the {language.capitalize()} programming language.",
                "reference_source": "Language Specification",
            }
        ]

        # Extract any RAG concepts mentioned
        if "### [" in user_prompt:
            for title_match in re.finditer(r"### \[([^\]]+)\]", user_prompt):
                concepts.append({
                    "name": title_match.group(1),
                    "explanation": f"Grounded concept from reference documentation: {title_match.group(1)}.",
                    "reference_source": "Verified Knowledge Base",
                })

        issues = []
        # Extract AST findings if present in prompt
        if "Deterministic Static Analysis Rule Findings:" in user_prompt:
            finding_matches = re.finditer(r"\*\s*\[(INFO|WARNING|ERROR)\]\s*L(\d+)\s+([^:(]+)\s*\(([^)]+)\):\s*([^|]+)\|\s*Remediation:\s*([^\n]+)", user_prompt)
            for fm in finding_matches:
                issues.append({
                    "line_number": int(fm.group(2)),
                    "severity": fm.group(1).lower(),
                    "category": fm.group(4).strip(),
                    "description": fm.group(5).strip(),
                    "suggested_fix": fm.group(6).strip(),
                })

        execution_walkthrough = [
            f"Step 1: Module loaded and language runtime initialized for {language}.",
            "Step 2: Control flow proceeds sequentially through top-level definitions.",
            "Step 3: Expressions evaluate and return output.",
        ]

        key_takeaways = [
            f"Code structure adheres to standard {language.capitalize()} idioms.",
            "Modular decomposition keeps logical blocks clear and testable.",
        ]

        suggested_improvements = [
            "Consider adding docstrings and explicit type hints to improve readability.",
            "Ensure edge cases such as empty or negative inputs are handled gracefully.",
        ]

        payload = {
            "summary": summary,
            "line_explanations": line_explanations,
            "concepts": concepts,
            "issues": issues,
            "execution_walkthrough": execution_walkthrough,
            "key_takeaways": key_takeaways,
            "suggested_improvements": suggested_improvements,
            "uncertainty_notes": [],
        }

        return json.dumps(payload, indent=2)

    async def generate_explanation(
        self,
        code: str,
        language: str,
        level: str,
        ast_context: str | None = None,
        required_blocks: list | None = None,
        rag_context: str | None = None,
        rag_citations: list | None = None,
        **kwargs: Any,
    ) -> LLMExplanationResult:
        """Legacy explanation generator for backward compatibility."""
        lang_title = language.capitalize()
        level_title = level.replace("_", " ").title()

        summary = f"This is a {lang_title} code snippet analyzed in '{level_title}' mode. It implements structured computation and control flow logic. The overall purpose is demonstrated clearly."
        
        if required_blocks:
            blocks = []
            for rb in required_blocks:
                blocks.append(
                    BlockExplanation(
                        title=rb.title,
                        explanation=f"Explanation for {rb.title}",
                        line_start=rb.line_start,
                        line_end=rb.line_end,
                    )
                )
        else:
            blocks = [
                BlockExplanation(
                    title="Initialization",
                    explanation="Sets up variables and dependencies.",
                    line_start=1,
                    line_end=min(3, len(code.splitlines())),
                ),
                BlockExplanation(
                    title="Main Logic",
                    explanation="Executes the core algorithm.",
                    line_start=min(4, len(code.splitlines())),
                    line_end=len(code.splitlines()),
                ),
            ]
        
        concepts = [
            ConceptTag(
                concept="Variables",
                definition="Containers for storing data values.",
            )
        ]

        hints = [
            "Consider using more descriptive variable names.",
            "Add type hints if applicable.",
        ]

        if rag_citations:
            for cite in rag_citations:
                snip = cite.snippet or cite.text or ""
                concepts.append(
                    ConceptTag(
                        concept=cite.title,
                        definition=f"Grounded from {cite.source}: {snip[:90]}...",
                    )
                )
                hints.append(f"Grounded recommendation based on [{cite.title}] ({cite.source}).")
        
        algorithm_steps = [
            "Initialize variables.",
            "Process the data.",
            "Return the result.",
        ]
        
        complexity = AlgorithmComplexity(
            time_complexity="O(n)",
            space_complexity="O(1)",
            explanation="Linear time scan with in-place operations.",
        )
        
        return LLMExplanationResult(
            summary=summary,
            blocks=blocks,
            concepts=concepts,
            algorithm_steps=algorithm_steps,
            complexity=complexity,
            hints=hints,
        )

    async def generate_quiz(
        self,
        code: str,
        language: str,
        explanation_context: str | None = None,
        locale: str = "en",
    ) -> QuizResponse:
        """Deterministic quiz generator."""
        from backend.schemas.quiz import CodeImprovement, GlossaryTerm, QuizOption, QuizQuestion, QuizResponse
        is_hi = locale == "hi"
        q1_text = "इस कोड का मुख्य उद्देश्य क्या है?" if is_hi else "What is the purpose of this code?"
        q2_text = "कोड में कौन सा नियंत्रण प्रवाह मौजूद है?" if is_hi else "What control flow is present in this code?"
        q3_text = "इस कोड के लिए सबसे अच्छा सुधार क्या हो सकता है?" if is_hi else "What is a recommended practice for this code?"

        questions = [
            QuizQuestion(
                id="1",
                text=q1_text,
                options=[
                    QuizOption(id="A", text="गणना और मान संसाधित करना" if is_hi else "It calculates and processes structured values."),
                    QuizOption(id="B", text="डेटाबेस सॉकेट खोलना" if is_hi else "It opens a network socket to a database."),
                    QuizOption(id="C", text="कर्नेल मॉड्यूल कंपाइल करना" if is_hi else "It compiles a kernel module."),
                    QuizOption(id="D", text="छवि फ़ाइल पार्स करना" if is_hi else "It parses an image file."),
                ],
                correct_option_id="A",
                explanation="The code performs logical calculation and processing.",
                line_reference="Line 1",
            ),
            QuizQuestion(
                id="2",
                text=q2_text,
                options=[
                    QuizOption(id="A", text="अनुक्रमिक निष्पादन और फ़ंक्शन" if is_hi else "Sequential execution and function/loop evaluations."),
                    QuizOption(id="B", text="प्रत्यक्ष असेंबली सिस्टम इंटरप्ट" if is_hi else "Direct assembly system interrupts."),
                    QuizOption(id="C", text="माइक्रोकंट्रोलर GPIO टॉगलिंग" if is_hi else "Microcontroller GPIO toggling."),
                    QuizOption(id="D", text="वेबअसेंबली बाइनरी संकलन" if is_hi else "WebAssembly binary compilation."),
                ],
                correct_option_id="A",
                explanation="The code executes standard control flow and language operations.",
                line_reference="Line 1",
            ),
            QuizQuestion(
                id="3",
                text=q3_text,
                options=[
                    QuizOption(id="A", text="स्वचालित परीक्षण जोड़ना" if is_hi else "Add automated tests and validate edge cases."),
                    QuizOption(id="B", text="सभी टिप्पणियां हटाना" if is_hi else "Delete all comments and variable names."),
                    QuizOption(id="C", text="हर चीज़ के लिए वैश्विक चर उपयोग करना" if is_hi else "Use global variables for everything."),
                    QuizOption(id="D", text="त्रुटि प्रबंधन अक्षम करना" if is_hi else "Disable all error handling."),
                ],
                correct_option_id="A",
                explanation="Unit testing and edge case validation ensure correctness.",
                line_reference="Line 1",
            ),
        ]

        glossary = [
            GlossaryTerm(term="Function", definition="A reusable block of code designed to perform a specific task."),
            GlossaryTerm(term="Variable", definition="A named storage location holding a value in computer memory."),
        ]
        common_mistakes = [
            "Modifying mutable default arguments across function calls.",
            "Not accounting for edge-case empty inputs.",
        ]
        improvement = CodeImprovement(
            improved_code=code,
            explanation="Structure code with clear naming and modular functions."
        )
        return QuizResponse(
            questions=questions,
            glossary=glossary,
            common_mistakes=common_mistakes,
            improvement=improvement,
        )

