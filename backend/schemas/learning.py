"""Pydantic schemas for the Interactive Code-Learning Workflow and Learner Progress Model."""

from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


QuestionCategory = Literal["comprehension", "debugging", "predict_output"]
DifficultyLevel = Literal["Beginner", "Intermediate", "Advanced"]


class LearningOption(BaseModel):
    id: str = Field(..., description="Option identifier (A, B, C, D)")
    text: str = Field(..., description="Option description text")


class LearningQuestion(BaseModel):
    id: str = Field(..., description="Unique question ID")
    question: str = Field(..., description="Question prompt text")
    question_type: QuestionCategory = Field("comprehension", description="Question category: comprehension, debugging, or predict_output")
    options: list[LearningOption] = Field(..., min_length=2, max_length=6, description="Multiple-choice options")
    correct_answer: str = Field(..., description="Identifier of the correct option (e.g. A, B, C, D)")
    explanation: str = Field(..., description="Detailed explanation of the correct answer and reasoning")
    referenced_lines: list[int] = Field(default_factory=list, description="Validated source code lines referenced by this question")
    difficulty: DifficultyLevel = Field("Beginner", description="Question difficulty")
    language: str = Field("python", description="Programming language of the code")
    concept: str = Field("General", description="Core programming concept assessed (e.g., Loops, Functions, Conditionals)")

    # Backward compatibility with QuizQuestion
    @property
    def text(self) -> str:
        return self.question

    @property
    def correct_option_id(self) -> str:
        return self.correct_answer

    @property
    def line_reference(self) -> str:
        return f"Lines {', '.join(map(str, self.referenced_lines))}" if self.referenced_lines else ""


class KeyConceptItem(BaseModel):
    name: str = Field(..., description="Concept name (e.g., Loops, Functions, Conditionals)")
    description: str = Field(..., description="Clear explanation of how this concept applies in the submitted code")
    referenced_lines: list[int] = Field(default_factory=list, description="Lines where this concept appears in code")


class LearningMaterialResponse(BaseModel):
    code: str = Field(..., description="Source code analyzed")
    language: str = Field(..., description="Programming language")
    
    # 8 Core Learning Material Requirements
    key_concepts: list[KeyConceptItem] = Field(default_factory=list, description="1. Key concepts identified in the code")
    beginner_explanation: str = Field(..., description="2. Approachable beginner-friendly explanation")
    execution_walkthrough: list[str] = Field(default_factory=list, description="3. Step-by-step execution walkthrough")
    common_mistakes: list[str] = Field(default_factory=list, description="4. Common mistakes and pitfalls related to this code")
    comprehension_questions: list[LearningQuestion] = Field(default_factory=list, description="5. Three comprehension questions")
    debugging_question: LearningQuestion = Field(..., description="6. One debugging question")
    predict_output_question: LearningQuestion = Field(..., description="7. One predict the output question")
    final_takeaway: str = Field(..., description="8. Memorable final takeaway summarizing key lesson")
    
    # Aggregated questions list (all 5 questions: 3 comprehension + 1 debugging + 1 predict output)
    questions: list[LearningQuestion] = Field(default_factory=list, description="All 5 questions in workflow order")

    @model_validator(mode="after")
    def populate_aggregated_questions(self) -> "LearningMaterialResponse":
        if not self.questions:
            all_q = list(self.comprehension_questions)
            if self.debugging_question:
                all_q.append(self.debugging_question)
            if self.predict_output_question:
                all_q.append(self.predict_output_question)
            self.questions = all_q
        return self


class SubmitAnswersRequest(BaseModel):
    code: str = Field(..., description="Source code for the learning session")
    language: str = Field("python", description="Programming language")
    answers: dict[str, str] = Field(..., description="Mapping of question id to chosen option id (e.g. {'1': 'A', '2': 'B'})")
    questions_payload: list[dict[str, Any]] | None = Field(None, description="Optional question definitions for standalone stateless scoring")
    session_id: str | None = Field(None, description="Optional session or submission ID")
    user_id: int | None = Field(None, description="Optional user ID for progress tracking")


class ConceptMasteryItem(BaseModel):
    concept: str = Field(..., description="Concept name (e.g. Loops, Functions)")
    mastery: float = Field(..., description="Mastery percentage (0.0 to 100.0%)")
    total_attempted: int = Field(0, description="Total questions attempted for this concept")
    total_correct: int = Field(0, description="Total questions answered correctly for this concept")


class QuestionEvaluationResult(BaseModel):
    question_id: str
    question: str
    question_type: str
    concept: str
    referenced_lines: list[int]
    user_answer: str | None
    correct_answer: str
    is_correct: bool
    explanation: str


class LearningEvaluationResponse(BaseModel):
    attempts: int = Field(1, description="Number of attempts for this session")
    score: float = Field(..., description="Score percentage (0.0 to 100.0%)")
    correct_count: int = Field(..., description="Count of correct answers")
    total_questions: int = Field(..., description="Total questions evaluated")
    incorrect_concepts: list[str] = Field(default_factory=list, description="List of concepts where questions were missed")
    completion_status: str = Field("completed", description="Session completion status: not_started, in_progress, completed")
    question_results: list[QuestionEvaluationResult] = Field(default_factory=list, description="Detailed per-question results")
    concept_mastery: list[ConceptMasteryItem] = Field(default_factory=list, description="Updated learner progress model breakdown")
