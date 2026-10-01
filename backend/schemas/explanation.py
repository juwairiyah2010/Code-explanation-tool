"""Pydantic schemas for AST analysis, code constructs, static rules, and explanations."""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


LanguageType = Literal["python", "javascript", "auto", "unknown"]
ExplanationLevelType = Literal["Absolute Beginner", "Beginner", "Intermediate"]
HintSeverity = Literal["info", "warning", "error"]


class ASTNodeInfo(BaseModel):
    """General AST node description for backward compatibility."""
    name: str = Field(..., description="Name of the node/symbol")
    node_type: str = Field(..., description="Node classification")
    line_start: int = Field(..., description="Starting line number (1-indexed)")
    line_end: int = Field(..., description="Ending line number (1-indexed)")
    docstring: str | None = Field(None, description="Docstring or comment if available")
    parameters: list[str] = Field(default_factory=list, description="Parameters if function/method")


# Detailed constructs models
class FunctionConstruct(BaseModel):
    name: str = Field(..., description="Function/Method name")
    parameters: list[str] = Field(default_factory=list, description="Parameter names")
    is_async: bool = Field(False, description="Whether the function is async")
    docstring: str | None = Field(None, description="Docstring if present")
    line_start: int = Field(..., description="1-indexed starting line")
    line_end: int = Field(..., description="1-indexed ending line")
    return_type: str | None = Field(None, description="Return type annotation if present")


class ClassConstruct(BaseModel):
    name: str = Field(..., description="Class name")
    bases: list[str] = Field(default_factory=list, description="Base / Superclass names")
    methods: list[str] = Field(default_factory=list, description="Defined method names")
    docstring: str | None = Field(None, description="Class docstring")
    line_start: int = Field(..., description="1-indexed starting line")
    line_end: int = Field(..., description="1-indexed ending line")


class LoopConstruct(BaseModel):
    loop_type: str = Field(..., description="Loop type (for, while, for_in, for_of, async_for)")
    target: str | None = Field(None, description="Loop target variable or condition")
    line_start: int = Field(..., description="1-indexed starting line")
    line_end: int = Field(..., description="1-indexed ending line")


class ConditionConstruct(BaseModel):
    condition_type: str = Field(..., description="Condition type (if, elif, else, switch, ternary)")
    test_expression: str | None = Field(None, description="Test expression")
    line_start: int = Field(..., description="1-indexed starting line")
    line_end: int = Field(..., description="1-indexed ending line")


class AssignmentConstruct(BaseModel):
    targets: list[str] = Field(default_factory=list, description="Target variable names")
    line_start: int = Field(..., description="1-indexed starting line")
    line_end: int = Field(..., description="1-indexed ending line")
    is_constant: bool = Field(False, description="Whether assignment is constant (e.g. const in JS)")


class ImportConstruct(BaseModel):
    module: str = Field(..., description="Imported module name")
    names: list[str] = Field(default_factory=list, description="Specific symbols imported")
    alias: str | None = Field(None, description="Alias if imported as")
    line_start: int = Field(..., description="1-indexed starting line")
    line_end: int = Field(..., description="1-indexed ending line")


class CallConstruct(BaseModel):
    callee: str = Field(..., description="Name of function/method called")
    arg_count: int = Field(0, description="Number of arguments passed")
    line_start: int = Field(..., description="1-indexed starting line")
    line_end: int = Field(..., description="1-indexed ending line")


class CodeConstructs(BaseModel):
    functions: list[FunctionConstruct] = Field(default_factory=list)
    classes: list[ClassConstruct] = Field(default_factory=list)
    loops: list[LoopConstruct] = Field(default_factory=list)
    conditions: list[ConditionConstruct] = Field(default_factory=list)
    assignments: list[AssignmentConstruct] = Field(default_factory=list)
    imports: list[ImportConstruct] = Field(default_factory=list)
    calls: list[CallConstruct] = Field(default_factory=list)


class SyntaxBlock(BaseModel):
    block_id: str = Field(..., description="Unique block identifier")
    block_type: str = Field(..., description="Block category: function, class, loop, branch, imports, top_level")
    title: str = Field(..., description="Human-readable block title")
    line_start: int = Field(..., description="1-indexed start line")
    line_end: int = Field(..., description="1-indexed end line")
    code_content: str = Field(..., description="Source code for this block")
    complexity_score: int = Field(1, description="Cyclomatic complexity within this block")


class StaticHint(BaseModel):
    rule_id: str = Field(..., description="Unique rule identifier (e.g. UNUSED_VARIABLE, DEEP_NESTING)")
    severity: HintSeverity = Field("warning", description="Severity level: info, warning, error")
    message: str = Field(..., description="Issue explanation")
    line_start: int = Field(..., description="Line where issue begins")
    line_end: int = Field(..., description="Line where issue ends")
    suggestion: str | None = Field(None, description="Recommended remediation")


class SyntaxErrorInfo(BaseModel):
    line: int = Field(1, description="Line number of syntax error")
    column: int = Field(1, description="Column offset of syntax error")
    message: str = Field(..., description="Description of the syntax error")


# Request & Response schemas


class BlockExplanation(BaseModel):
    title: str = Field(..., description="Block title")
    explanation: str = Field(..., description="Explanation of the block")
    line_start: int = Field(..., description="Starting line reference")
    line_end: int = Field(..., description="Ending line reference")

class ConceptTag(BaseModel):
    concept: str = Field(..., description="Concept name")
    definition: str = Field(..., description="Simple definition")

class AlgorithmComplexity(BaseModel):
    time_complexity: str = Field(..., description="Time complexity estimate")
    space_complexity: str = Field(..., description="Space complexity estimate")
    explanation: str = Field(..., description="Complexity explanation")

class CodeAnalysisRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000, description="Source code snippet to analyze")
    language: LanguageType = Field("auto", description="Language of snippet ('auto', 'python', 'javascript')")
    filename: str | None = Field(None, description="Optional filename for extension-based language detection")

    @field_validator("code")
    @classmethod
    def validate_code_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Code snippet cannot be empty or solely whitespace.")
        return v


class CodeAnalysisResponse(BaseModel):
    language: str = Field(..., description="Detected or specified programming language")
    detection_method: str = Field("explicit", description="How language was determined (filename, syntax_heuristic, explicit)")
    is_valid_syntax: bool = Field(True, description="Whether the code parses successfully without fatal errors")
    syntax_error: str | None = Field(None, description="Primary syntax error message if invalid")
    syntax_errors: list[SyntaxErrorInfo] = Field(default_factory=list, description="List of syntax error details")
    blocks: list[SyntaxBlock] = Field(default_factory=list, description="Logical syntax blocks")
    constructs: CodeConstructs = Field(default_factory=CodeConstructs, description="Extracted language constructs")
    static_hints: list[StaticHint] = Field(default_factory=list, description="Static analysis rule hints")
    complexity_score: int = Field(1, description="Total cyclomatic complexity score")
    max_nesting_depth: int = Field(0, description="Maximum indentation / nesting level")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Detailed metrics (lines, tokens, counts)")

    # Legacy fields for backward compatibility
    functions: list[ASTNodeInfo] = Field(default_factory=list)
    classes: list[ASTNodeInfo] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)


class ExplainCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000, description="Code snippet to explain")
    language: LanguageType = Field("python", description="Programming language")
    filename: str | None = Field(None, description="Optional filename")
    level: ExplanationLevelType = Field("Beginner", description="Desired level of explanation")
    include_ast_analysis: bool = Field(True, description="Whether to include AST parsing metadata")
    save_history: bool = Field(True, description="Whether to persist the explanation in SQLite")

    @field_validator("code")
    @classmethod
    def validate_code_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Code snippet cannot be empty or solely whitespace.")
        return v


class ExplainCodeResponse(BaseModel):
    id: int | None = Field(None, description="Record ID if saved to database")
    language: str
    level: ExplanationLevelType
    summary: str = Field(..., description="Three-sentence overall summary")
    blocks: list[BlockExplanation] = Field(default_factory=list, description="Block-by-block explanations")
    concepts: list[ConceptTag] = Field(default_factory=list, description="Concept tags with simple definitions")
    algorithm_steps: list[str] = Field(default_factory=list, description="Algorithm steps")
    complexity: AlgorithmComplexity = Field(..., description="Complexity estimates")
    hints: list[str] = Field(default_factory=list, description="Common mistakes and improvement hints")
    ast_analysis: CodeAnalysisResponse | None = None
    created_at: datetime | None = None


class ExplanationHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    language: str
    code_snippet: str
    explanation_style: str
    summary: str | None = None
    detailed_explanation: str
    created_at: datetime
