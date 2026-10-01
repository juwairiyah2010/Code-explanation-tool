"""Mock LLM service providing realistic deterministic explanations for development & testing."""

from backend.services.llm.base import BaseLLMService, LLMExplanationResult

class MockLLMService(BaseLLMService):
    """Deterministic Mock LLM Service for local development and test suites."""

    async def generate_explanation(
        self,
        code: str,
        language: str,
        level: str,
        ast_context: str | None = None,
        required_blocks: list | None = None,
    ) -> LLMExplanationResult:
        from backend.schemas.explanation import AlgorithmComplexity, BlockExplanation, ConceptTag
        lang_title = language.capitalize()
        level_title = level.replace("_", " ").title()

        summary = f"This is a {lang_title} code snippet analyzed in '{level_title}' mode. It implements structured computation and control flow logic. The overall purpose is demonstrated clearly."
        
        if required_blocks:
            blocks = []
            for rb in required_blocks:
                # Add all except the last one to simulate a missing block occasionally for testing
                # Actually, let's just return all of them to pass normally, 
                # but we can test missing blocks via tests.
                blocks.append(
                    BlockExplanation(
                        title=rb.title,
                        explanation=f"Explanation for {rb.title}",
                        line_start=rb.line_start,
                        line_end=rb.line_end
                    )
                )
        else:
            blocks = [
                BlockExplanation(
                    title="Initialization",
                    explanation="Sets up variables and dependencies.",
                    line_start=1,
                    line_end=3
                ),
                BlockExplanation(
                    title="Main Logic",
                    explanation="Executes the core algorithm.",
                    line_start=4,
                    line_end=10
                )
            ]
        
        concepts = [
            ConceptTag(
                concept="Variables",
                definition="Containers for storing data values."
            )
        ]
        
        algorithm_steps = [
            "Initialize variables.",
            "Process the data.",
            "Return the result."
        ]
        
        complexity = AlgorithmComplexity(
            time_complexity="O(n)",
            space_complexity="O(1)",
            explanation="Linear time scan with in-place operations."
        )
        
        hints = [
            "Consider using more descriptive variable names.",
            "Add type hints if applicable."
        ]
        
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
    ):
        from backend.schemas.quiz import QuizResponse, QuizQuestion, QuizOption, GlossaryTerm, CodeImprovement
        
        # We need to return exactly 3 questions
        q1 = QuizQuestion(
            id="q1",
            text="What is the purpose of this code?" if locale == "en" else "इस कोड का उद्देश्य क्या है?",
            options=[
                QuizOption(id="o1", text="Option A"),
                QuizOption(id="o2", text="Option B"),
                QuizOption(id="o3", text="Option C"),
                QuizOption(id="o4", text="Option D"),
            ],
            correct_option_id="o1",
            explanation="Explanation for Q1",
            line_reference="1-5"
        )
        
        q2 = QuizQuestion(
            id="q2",
            text="What happens if the input is negative?",
            options=[
                QuizOption(id="o1", text="Error"),
                QuizOption(id="o2", text="Ignored"),
                QuizOption(id="o3", text="Processed normally"),
                QuizOption(id="o4", text="Throws Exception"),
            ],
            correct_option_id="o1",
            explanation="Explanation for Q2",
            line_reference="6-8"
        )
        
        q3 = QuizQuestion(
            id="q3",
            text="Which function is called?",
            options=[
                QuizOption(id="o1", text="funcA"),
                QuizOption(id="o2", text="funcB"),
                QuizOption(id="o3", text="funcC"),
                QuizOption(id="o4", text="funcD"),
            ],
            correct_option_id="o2",
            explanation="Explanation for Q3",
            line_reference="10"
        )
        
        glossary = [GlossaryTerm(term="Function", definition="A block of code.")]
        mistakes = ["Forgetting to return a value."]
        improvement = CodeImprovement(improved_code="def func(): return True", explanation="Better structure.")
        
        return QuizResponse(
            questions=[q1, q2, q3],
            glossary=glossary,
            common_mistakes=mistakes,
            improvement=improvement
        )
