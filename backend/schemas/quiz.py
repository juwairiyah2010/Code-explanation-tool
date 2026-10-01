from pydantic import BaseModel, Field
from typing import List, Optional

class QuizRequest(BaseModel):
    code: str
    language: str = "python"
    explanation_context: Optional[str] = None
    locale: str = "en"

class QuizOption(BaseModel):
    id: str
    text: str

class QuizQuestion(BaseModel):
    id: str
    text: str
    options: List[QuizOption]
    correct_option_id: str
    explanation: str
    line_reference: Optional[str] = None

class GlossaryTerm(BaseModel):
    term: str
    definition: str

class CodeImprovement(BaseModel):
    improved_code: str
    explanation: str

class QuizResponse(BaseModel):
    questions: List[QuizQuestion] = Field(..., min_length=3, max_length=3)
    glossary: List[GlossaryTerm]
    common_mistakes: List[str]
    improvement: Optional[CodeImprovement] = None
