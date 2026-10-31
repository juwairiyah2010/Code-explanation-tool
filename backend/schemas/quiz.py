from typing import Any, List, Optional
from pydantic import BaseModel, Field, model_validator


class QuizRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000, description="Code snippet for quiz generation")
    language: str = Field("python", max_length=32)
    explanation_context: Optional[str] = Field(None, max_length=20000)
    locale: str = Field("en", max_length=16)
    workflow: str = Field("standard", max_length=32)  # "standard" (3 questions) or "learning" (5 questions + workflow material)


class QuizOption(BaseModel):
    id: str
    text: str


class QuizQuestion(BaseModel):
    id: str
    text: str = ""
    question: Optional[str] = None
    options: List[QuizOption]
    correct_option_id: str = ""
    correct_answer: Optional[str] = None
    explanation: str
    line_reference: Optional[str] = None
    referenced_lines: List[int] = Field(default_factory=list)
    difficulty: str = "Beginner"
    language: str = "python"
    concept: str = "General"
    question_type: str = "comprehension"

    @model_validator(mode="before")
    @classmethod
    def sync_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Sync text / question
            if not data.get("text") and data.get("question"):
                data["text"] = data["question"]
            elif not data.get("question") and data.get("text"):
                data["question"] = data["text"]

            # Sync correct_option_id / correct_answer
            if not data.get("correct_option_id") and data.get("correct_answer"):
                data["correct_option_id"] = data["correct_answer"]
            elif not data.get("correct_answer") and data.get("correct_option_id"):
                data["correct_answer"] = data["correct_option_id"]

            # Sync line_reference / referenced_lines
            if not data.get("line_reference") and data.get("referenced_lines"):
                data["line_reference"] = f"Line {', '.join(map(str, data['referenced_lines']))}"
        return data


class GlossaryTerm(BaseModel):
    term: str
    definition: str


class CodeImprovement(BaseModel):
    improved_code: str
    explanation: str


class QuizResponse(BaseModel):
    questions: List[QuizQuestion] = Field(..., min_length=3)
    glossary: List[GlossaryTerm] = Field(default_factory=list)
    common_mistakes: List[str] = Field(default_factory=list)
    improvement: Optional[CodeImprovement] = None

    # Enhanced interactive code-learning material
    key_concepts: List[Any] = Field(default_factory=list)
    beginner_explanation: Optional[str] = None
    execution_walkthrough: List[str] = Field(default_factory=list)
    final_takeaway: Optional[str] = None
    concept_mastery: List[Any] = Field(default_factory=list)
