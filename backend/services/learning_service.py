"""Interactive Code-Learning Workflow Service.

Synthesizes structured learning material from deterministic AST analysis,
execution traces, and explanation heuristics. Produces 8 core learning components
including 5 grounded questions (3 comprehension, 1 debugging, 1 predict output)
and manages deterministic scoring and learner progress tracking.
"""

import json
import re
from typing import Any
from backend.core.logging import logger
from backend.schemas.explanation import CodeAnalysisResponse
from backend.schemas.learning import (
    KeyConceptItem,
    LearningMaterialResponse,
    LearningOption,
    LearningQuestion,
)
from backend.schemas.quiz import QuizOption, QuizQuestion, QuizResponse
from backend.schemas.trace import TraceResponse
from backend.services.analysis.analysis_service import AnalysisService
from backend.services.detector.language_detector import LanguageDetector
from backend.services.llm import get_llm_service
from backend.services.llm.base import BaseLLMService
from backend.services.tracer_service import TraceService


from collections import OrderedDict
import hashlib
import threading

class LearningMaterialCache:
    """Thread-safe LRU cache for synthesized learning materials."""

    def __init__(self, maxsize: int = 512):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, LearningMaterialResponse] = OrderedDict()
        self._lock = threading.Lock()

    def make_key(self, code: str, language: str, locale: str) -> str:
        content = f"{language}::{locale}::{code}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get(self, code: str, language: str, locale: str) -> LearningMaterialResponse | None:
        key = self.make_key(code, language, locale)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def put(self, code: str, language: str, locale: str, result: LearningMaterialResponse) -> None:
        key = self.make_key(code, language, locale)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.maxsize:
                    self._cache.popitem(last=False)
                self._cache[key] = result

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class LearningService:
    """Orchestrates deterministic code analysis into interactive learning workflows."""

    def __init__(
        self,
        llm_service: BaseLLMService | None = None,
        analysis_service: AnalysisService | None = None,
        trace_service: TraceService | None = None,
        language_detector: LanguageDetector | None = None,
    ):
        self.llm = llm_service or get_llm_service()
        self.analyzer = analysis_service or AnalysisService()
        self.tracer = trace_service or TraceService()
        self.detector = language_detector or LanguageDetector()
        self.cache = LearningMaterialCache()

    async def generate_learning_material(
        self,
        code: str,
        language: str = "auto",
        explanation_context: str | None = None,
        locale: str = "en",
        ast_result: CodeAnalysisResponse | None = None,
        trace_result: TraceResponse | None = None,
        use_cache: bool = True,
    ) -> LearningMaterialResponse:
        """Generate complete 8-component learning material grounded in AST analysis and execution trace."""
        if use_cache:
            cached = self.cache.get(code, language, locale)
            if cached is not None:
                return cached

        # 1. Resolve language
        if not language or language == "auto":
            det = self.detector.detect(code)
            resolved_lang = det.language
        else:
            resolved_lang = language.lower()

        # 2. Deterministic AST Analysis (reused if provided, else cached)
        if ast_result is None:
            ast_result = self.analyzer.analyze(code, language=resolved_lang)

        # 3. Execution Trace when applicable (reused if provided, else cached)
        if trace_result is None and resolved_lang == "python":
            try:
                trace_result = await self.tracer.trace_if_applicable(code, language=resolved_lang)
            except Exception as e:
                logger.warning(f"Trace skipped during learning material generation: {e}")

        # 4. Attempt LLM generation if available and not MockLLM
        material: LearningMaterialResponse | None = None
        try:
            material = await self._try_llm_generation(
                code=code,
                language=resolved_lang,
                ast_result=ast_result,
                trace_result=trace_result,
                explanation_context=explanation_context,
                locale=locale,
            )
        except Exception as e:
            logger.warning(f"LLM learning generation failed or bypassed ({e}); using deterministic synthesis.")

        # 5. Deterministic Synthesis Fallback if LLM was unavailable or invalid
        if material is None:
            material = self.synthesize_deterministic_material(
                code=code,
                language=resolved_lang,
                ast_result=ast_result,
                trace_result=trace_result,
                locale=locale,
            )

        # 6. Enforce Grounding and Line Reference Integrity
        self.validate_and_sanitize_material(material, code)
        if use_cache:
            self.cache.put(code, language, locale, material)
        return material

    def validate_and_sanitize_material(
        self, material: LearningMaterialResponse, code: str
    ) -> None:
        """Validate question options, grounded line bounds, and ensure question types match requirements."""
        total_lines = max(1, len(code.splitlines()))

        for q in material.questions:
            opt_ids = [opt.id for opt in q.options]
            if q.correct_answer not in opt_ids:
                q.correct_answer = opt_ids[0]

            # Enforce line bounds
            valid_lines = [ln for ln in q.referenced_lines if 1 <= ln <= total_lines]
            q.referenced_lines = valid_lines if valid_lines else [1]

        # Verify exactly 3 comprehension, 1 debugging, 1 predict_output
        comp_q = [q for q in material.questions if q.question_type == "comprehension"]
        debug_q = [q for q in material.questions if q.question_type == "debugging"]
        predict_q = [q for q in material.questions if q.question_type == "predict_output"]

        # Ensure correct counts
        material.comprehension_questions = comp_q[:3]
        material.debugging_question = debug_q[0] if debug_q else material.questions[min(3, len(material.questions) - 1)]
        material.debugging_question.question_type = "debugging"
        material.predict_output_question = predict_q[0] if predict_q else material.questions[-1]
        material.predict_output_question.question_type = "predict_output"

    def synthesize_deterministic_material(
        self,
        code: str,
        language: str,
        ast_result: CodeAnalysisResponse | None,
        trace_result: TraceResponse | None = None,
        locale: str = "en",
    ) -> LearningMaterialResponse:
        """Deterministically derive all 8 learning items from verified AST nodes and trace steps."""
        lines = code.splitlines()
        total_lines = len(lines)
        is_hi = locale == "hi"

        # 1. Key Concepts
        key_concepts: list[KeyConceptItem] = []
        identified_concepts: list[str] = []

        if ast_result and ast_result.constructs:
            c = ast_result.constructs
            if c.functions:
                key_concepts.append(
                    KeyConceptItem(
                        name="Functions",
                        description=f"Defines reusable callable logic ({', '.join(f.name for f in c.functions)}).",
                        referenced_lines=[f.line_start for f in c.functions],
                    )
                )
                identified_concepts.append("Functions")
            if c.loops:
                key_concepts.append(
                    KeyConceptItem(
                        name="Loops",
                        description="Executes repetitive iteration over data or ranges.",
                        referenced_lines=[lp.line_start for lp in c.loops],
                    )
                )
                identified_concepts.append("Loops")
            if c.conditions:
                key_concepts.append(
                    KeyConceptItem(
                        name="Conditionals",
                        description="Performs branch evaluation and decision-making logic.",
                        referenced_lines=[cd.line_start for cd in c.conditions],
                    )
                )
                identified_concepts.append("Conditionals")
            if c.imports:
                key_concepts.append(
                    KeyConceptItem(
                        name="Imports",
                        description="Includes external library modules into the namespace.",
                        referenced_lines=[im.line_start for im in c.imports],
                    )
                )
                identified_concepts.append("Imports")
            if c.assignments:
                key_concepts.append(
                    KeyConceptItem(
                        name="Variables",
                        description="Allocates and updates state in memory.",
                        referenced_lines=[asgn.line_start for asgn in c.assignments[:3]],
                    )
                )
                identified_concepts.append("Variables")

        if not key_concepts:
            key_concepts.append(
                KeyConceptItem(
                    name="Sequential Execution",
                    description=f"Executes statements linearly in {language.capitalize()}.",
                    referenced_lines=[1],
                )
            )
            identified_concepts.append("Sequential Execution")

        # 2. Beginner Explanation
        primary_concept = identified_concepts[0] if identified_concepts else "Core Logic"
        beginner_explanation = (
            f"यह {language.capitalize()} कोड {total_lines} पंक्तियों में मुख्य रूप से '{primary_concept}' का उपयोग करके तार्किक गणना करता है।"
            if is_hi
            else f"This {language.capitalize()} code operates across {total_lines} lines to implement structured computation centered on {primary_concept}."
        )

        # 3. Execution Walkthrough
        execution_walkthrough: list[str] = []
        if trace_result and trace_result.success and trace_result.steps:
            for i, step in enumerate(trace_result.steps[:4]):
                step_desc = f"Step {i+1}: Line {step.line_number} executed"
                event = getattr(step, "event_type", getattr(step, "event", "line"))
                func = getattr(step, "function_name", "<module>")
                if event == "call" and func != "<module>":
                    step_desc += f" (called function '{func}')"
                elif getattr(step, "output", None):
                    step_desc += f" (output: {step.output})"
                execution_walkthrough.append(step_desc)
        else:
            execution_walkthrough = [
                f"Step 1: Program starts at line 1, parsing declarations and imports in {language}.",
                "Step 2: Control flow evaluates expressions and branches sequentially.",
                "Step 3: Program completes execution, yielding final state and output.",
            ]

        # 4. Common Mistakes
        common_mistakes = [
            f"Failing to validate inputs before evaluating operations in {language}.",
            "Off-by-one boundary errors when iterating over index-based collections.",
            "Assuming state modifications persist across independent execution scopes.",
        ]
        if ast_result and ast_result.static_hints:
            for hint in ast_result.static_hints[:2]:
                common_mistakes.append(f"Line {hint.line_start}: {hint.message} ({hint.suggestion})")

        # 5. Three Comprehension Questions Grounded in Code
        first_func = ast_result.constructs.functions[0] if (ast_result and ast_result.constructs and ast_result.constructs.functions) else None
        first_loop = ast_result.constructs.loops[0] if (ast_result and ast_result.constructs and ast_result.constructs.loops) else None
        first_cond = ast_result.constructs.conditions[0] if (ast_result and ast_result.constructs and ast_result.constructs.conditions) else None

        # Question 1: Purpose / Architecture
        q1_lines = [first_func.line_start] if first_func else [1]
        q1 = LearningQuestion(
            id="q1",
            question="इस कोड का मुख्य उद्देश्य क्या है?" if is_hi else "What is the primary architectural purpose of this code?",
            question_type="comprehension",
            options=[
                LearningOption(id="A", text="डेटा संसाधित और गणना करना" if is_hi else "To calculate and process structured values deterministically."),
                LearningOption(id="B", text="नेटवर्क सॉकेट खोलना" if is_hi else "To initialize a remote TCP socket listener."),
                LearningOption(id="C", text="ऑपरेटिंग सिस्टम कर्नेल संकलित करना" if is_hi else "To compile OS kernel memory drivers."),
                LearningOption(id="D", text="छवि फ़ाइल पार्स करना" if is_hi else "To decode a compressed image stream."),
            ],
            correct_answer="A",
            explanation="The code defines procedural operations to compute and transform data values.",
            referenced_lines=q1_lines,
            difficulty="Beginner",
            language=language,
            concept="Functions" if first_func else "Variables",
        )

        # Question 2: Control flow / Branching / Loop
        q2_lines = [first_loop.line_start] if first_loop else ([first_cond.line_start] if first_cond else [min(2, total_lines)])
        q2_concept = "Loops" if first_loop else ("Conditionals" if first_cond else "Control Flow")
        q2 = LearningQuestion(
            id="q2",
            question=f"Line {q2_lines[0]} पर निष्पादन व्यवहार क्या है?" if is_hi else f"How does control flow behave at line {q2_lines[0]}?",
            question_type="comprehension",
            options=[
                LearningOption(id="A", text="यह शर्तों और अनुक्रम के अनुसार निष्पादित होता है" if is_hi else f"It evaluates {q2_concept.lower()} logic within the current execution frame."),
                LearningOption(id="B", text="यह निष्पादन तुरंत बंद कर देता है" if is_hi else "It halts the OS process unconditionally."),
                LearningOption(id="C", text="यह हार्डवेयर व्यवधान उत्पन्न करता है" if is_hi else "It triggers a direct hardware interrupt."),
                LearningOption(id="D", text="यह मेमोरी खाली करता है" if is_hi else "It unlinks the source code file from disk."),
            ],
            correct_answer="A",
            explanation=f"Line {q2_lines[0]} directs control flow according to standard {language} semantic rules.",
            referenced_lines=q2_lines,
            difficulty="Beginner",
            language=language,
            concept=q2_concept,
        )

        # Question 3: State & Data Transformation
        q3_lines = [total_lines]
        q3 = LearningQuestion(
            id="q3",
            question="अंतिम पंक्ति निष्पादित होने पर प्रोग्राम की स्थिति क्या होती है?" if is_hi else f"What state is finalized when the program completes around line {q3_lines[0]}?",
            question_type="comprehension",
            options=[
                LearningOption(id="A", text="प्रोग्राम मान लौटाता है या आउटपुट प्रिंट करता है" if is_hi else "The routine finishes computing and yields its resolved value or output."),
                LearningOption(id="B", text="सभी चर रीसेट हो जाते हैं" if is_hi else "An infinite loop blocks the main thread."),
                LearningOption(id="C", text="फ़ाइल सहेज दी जाती है" if is_hi else "A syntax parsing exception aborts the program."),
                LearningOption(id="D", text="कोई परिवर्तन नहीं होता" if is_hi else "The runtime enters an unrecoverable panic."),
            ],
            correct_answer="A",
            explanation="The code successfully concludes its transformation and returns/outputs the final result.",
            referenced_lines=q3_lines,
            difficulty="Intermediate",
            language=language,
            concept="Variables",
        )

        # 6. One Debugging Question Grounded in Code
        debug_line = first_cond.line_start if first_cond else (first_loop.line_start if first_loop else 1)
        q4 = LearningQuestion(
            id="q4",
            question=f"यदि line {debug_line} को अमान्य या अप्रत्याशित इनपुट दिया जाए, तो क्या संभावित बग हो सकता है?"
            if is_hi
            else f"Which potential bug or edge case should be accounted for around line {debug_line}?",
            question_type="debugging",
            options=[
                LearningOption(id="A", text="अप्रत्याशित इनपुट प्रकार या खाली मान अपवाद उत्पन्न कर सकते हैं" if is_hi else "Unhandled input types or boundary values could trigger a runtime error."),
                LearningOption(id="B", text="हार्ड डिस्क भर जाएगी" if is_hi else "Disk space will immediately exhaust."),
                LearningOption(id="C", text="सॉफ़्टवेयर स्वतः अपडेट हो जाएगा" if is_hi else "The interpreter will automatically modify the original source file."),
                LearningOption(id="D", text="सीपीयू फ़्रीक्वेंसी दोगुनी हो जाएगी" if is_hi else "Hardware clock rates will double."),
            ],
            correct_answer="A",
            explanation=f"Validating boundary conditions around line {debug_line} prevents runtime exceptions.",
            referenced_lines=[debug_line],
            difficulty="Intermediate",
            language=language,
            concept=q2_concept,
        )

        # 7. One Predict the Output Question
        predict_lines = [total_lines]
        traced_output = None
        if trace_result and trace_result.success and getattr(trace_result, "output", None):
            traced_output = trace_result.output.strip()
        elif trace_result and trace_result.success and trace_result.steps:
            for step in reversed(trace_result.steps):
                step_out = getattr(step, "output", None) or getattr(step, "stdout", None)
                if step_out:
                    traced_output = str(step_out).strip()
                    break

        ans_text = f"Result matching: {traced_output}" if traced_output else "Computes output based on the provided inputs and statements."
        q5 = LearningQuestion(
            id="q5",
            question="इस कोड को दिए गए इनपुट के साथ चलाने पर अपेक्षित आउटपुट क्या होगा?" if is_hi else "What is the expected output or terminal evaluation of this code?",
            question_type="predict_output",
            options=[
                LearningOption(id="A", text=ans_text),
                LearningOption(id="B", text="Undefined / Void with no execution" if is_hi else "An unexpected KeyError or ReferenceError."),
                LearningOption(id="C", text="None / null" if is_hi else "Zero (0) regardless of any inputs."),
                LearningOption(id="D", text="Error: Stack Overflow" if is_hi else "An infinite loop preventing termination."),
            ],
            correct_answer="A",
            explanation="Tracing the sequential execution of lines produces the deterministic evaluation outcome.",
            referenced_lines=predict_lines,
            difficulty="Intermediate",
            language=language,
            concept="Sequential Execution",
        )

        # 8. Final Takeaway
        final_takeaway = (
            f"कुंजी सीख: {primary_concept} का सही और स्पष्ट उपयोग कोड को विश्वसनीय, समझने में आसान और बनाए रखने योग्य बनाता है।"
            if is_hi
            else f"Key Takeaway: Clear structuring of {primary_concept} and defensive handling of input boundaries ensures predictable, testable execution."
        )

        return LearningMaterialResponse(
            code=code,
            language=language,
            key_concepts=key_concepts,
            beginner_explanation=beginner_explanation,
            execution_walkthrough=execution_walkthrough,
            common_mistakes=common_mistakes,
            comprehension_questions=[q1, q2, q3],
            debugging_question=q4,
            predict_output_question=q5,
            final_takeaway=final_takeaway,
            questions=[q1, q2, q3, q4, q5],
        )

    async def _try_llm_generation(
        self,
        code: str,
        language: str,
        ast_result: CodeAnalysisResponse | None,
        trace_result: TraceResponse | None,
        explanation_context: str | None,
        locale: str,
    ) -> LearningMaterialResponse | None:
        """Attempt to synthesize learning material via LLM with strict JSON schema."""
        # Check if LLM is MockLLMService - if so, delegate to deterministic synthesis directly
        if self.llm.__class__.__name__ == "MockLLMService":
            return None

        # Build prompt for LLM
        prompt = (
            f"Generate an interactive code-learning package for this {language} code in locale '{locale}'.\n"
            f"Code:\n```\n{code}\n```\n"
        )
        if ast_result and ast_result.constructs:
            c = ast_result.constructs
            prompt += f"\nAST Constructs: {len(c.functions)} functions, {len(c.loops)} loops, {len(c.conditions)} branches."

        raw = await self.llm.generate_chat_completion(
            system_prompt=(
                "You are an expert computer science tutor. Output valid JSON containing: "
                "key_concepts (list of name, description, referenced_lines), beginner_explanation, "
                "execution_walkthrough (list of strings), common_mistakes (list of strings), "
                "comprehension_questions (list of 3 questions with id, question, options, correct_answer, explanation, referenced_lines, difficulty, concept), "
                "debugging_question (1 question with same fields, question_type='debugging'), "
                "predict_output_question (1 question with same fields, question_type='predict_output'), "
                "final_takeaway."
            ),
            user_prompt=prompt,
            json_mode=True,
        )

        # Parse JSON
        clean_json = raw.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", clean_json)
        data = json.loads(clean_json)

        return LearningMaterialResponse.model_validate({
            "code": code,
            "language": language,
            **data,
        })

    def to_quiz_response(self, material: LearningMaterialResponse) -> QuizResponse:
        """Convert LearningMaterialResponse into a backward-compatible QuizResponse."""
        quiz_questions = [
            QuizQuestion(
                id=q.id,
                text=q.question,
                question=q.question,
                options=[QuizOption(id=opt.id, text=opt.text) for opt in q.options],
                correct_option_id=q.correct_answer,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                line_reference=f"Line {', '.join(map(str, q.referenced_lines))}" if q.referenced_lines else "Line 1",
                referenced_lines=q.referenced_lines,
                difficulty=q.difficulty,
                language=q.language,
                concept=q.concept,
                question_type=q.question_type,
            )
            for q in material.questions
        ]

        # Glossary from key concepts
        glossary = [
            {"term": kc.name, "definition": kc.description}
            for kc in material.key_concepts
        ]

        return QuizResponse(
            questions=quiz_questions,
            glossary=glossary,  # type: ignore
            common_mistakes=material.common_mistakes,
            key_concepts=[kc.model_dump() for kc in material.key_concepts],
            beginner_explanation=material.beginner_explanation,
            execution_walkthrough=material.execution_walkthrough,
            final_takeaway=material.final_takeaway,
        )

    def evaluate_answers(
        self,
        answers: dict[str, str],
        questions_payload: list[dict[str, Any]],
        user_id: int | None = None,
        db: Any = None,
    ):
        """Deterministically evaluate quiz answers and calculate concept mastery."""
        from backend.core.database import SessionLocal
        from backend.repositories.learning_repo import LearningRepository

        session = db or SessionLocal()
        try:
            repo = LearningRepository(session)
            return repo.evaluate_and_record_attempt(
                questions=questions_payload,
                answers=answers,
                user_id=user_id,
            )
        finally:
            if db is None:
                session.close()
