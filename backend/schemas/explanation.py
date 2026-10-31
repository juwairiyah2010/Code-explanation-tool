"""Pydantic schemas for AST analysis, code constructs, static rules, and explanations."""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class AnalysisFinding(BaseModel):
    """Normalized static code analysis finding formatted for both developers and beginners."""

    rule_id: str = Field(..., description="Unique rule code (e.g. UNUSED_VARIABLE, BARE_EXCEPT)")
    language: str = Field("python", description="Target language: python or javascript")
    severity: str = Field("warning", description="Severity level: info, warning, error")
    line_number: int = Field(1, description="Line number where issue originates")
    column_number: int | None = Field(None, description="Column offset when available")
    category: str = Field("code quality", description="Category: syntax, unused code, complexity, control flow, return behavior, variable usage, imports, exception handling, code quality, security, performance")
    title: str = Field(..., description="Short human-friendly title of the finding")
    technical_description: str = Field(..., description="Concise technical description")
    beginner_explanation: str = Field(..., description="Intuitive educational explanation for beginners")
    suggested_fix: str = Field(..., description="Actionable code remediation advice")

    # Compatibility aliases for existing tests and UI referencing StaticHint
    line_start: int = 1
    line_end: int = 1
    message: str = ""
    suggestion: str | None = None

    @model_validator(mode="before")
    @classmethod
    def sync_finding_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Line numbers
            if "line_number" in data:
                data.setdefault("line_start", data["line_number"])
                data.setdefault("line_end", data.get("line_end", data["line_number"]))
            elif "line_start" in data:
                data.setdefault("line_number", data["line_start"])
                data.setdefault("line_end", data["line_start"])

            # Descriptions
            if not data.get("message"):
                data["message"] = data.get("technical_description") or data.get("title") or ""
            if not data.get("technical_description"):
                data["technical_description"] = data.get("message") or data.get("title") or ""

            # Suggestions
            if "suggested_fix" in data:
                data.setdefault("suggestion", data["suggested_fix"])
            elif "suggestion" in data:
                data.setdefault("suggested_fix", data["suggestion"] or "")

            # Title & Beginner explanation defaults
            if "title" not in data and "rule_id" in data:
                data["title"] = data["rule_id"].replace("_", " ").title()
            if "beginner_explanation" not in data:
                data["beginner_explanation"] = data.get("technical_description") or data.get("message", "")
        return data


# StaticHint is now an alias of AnalysisFinding for full backward compatibility
StaticHint = AnalysisFinding


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
    time_complexity: str = Field("O(1)", description="Time complexity estimate")
    space_complexity: str = Field("O(1)", description="Space complexity estimate")
    explanation: str = Field("", description="Complexity explanation")

    @model_validator(mode="before")
    @classmethod
    def _sync_complexity_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "time" in data and "time_complexity" not in data:
                data["time_complexity"] = data["time"]
            if "space" in data and "space_complexity" not in data:
                data["space_complexity"] = data["space"]
            if "explanation" not in data:
                data["explanation"] = ""
        return data

class LineExplanationItem(BaseModel):
    line_number: int = Field(..., description="Actual source line number (1-indexed)")
    code: str | None = Field(None, description="Actual code content of this line")
    explanation: str = Field(..., description="Explanation for this line")
    uncertainty_note: str | None = Field(None, description="Explicit uncertainty note if applicable")
    ast_node: str | None = Field(None, description="Associated AST construct type if any")

    @model_validator(mode="before")
    @classmethod
    def _sync_line_field(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "line" in data and "line_number" not in data:
                data["line_number"] = data["line"]
        return data

class ConceptItem(BaseModel):
    name: str = Field(..., description="Concept or technique name")
    explanation: str = Field(..., description="Educational explanation of the concept")
    reference_source: str | None = Field(None, description="Attributed reference if available")

class IssueItem(BaseModel):
    line_number: int | None = Field(None, description="Line number if related to a specific line")
    severity: str = Field("warning", description="info, warning, or error")
    category: str = Field("code quality", description="syntax, security, performance, bug, quality")
    description: str = Field(..., description="Clear explanation of the problem")
    suggested_fix: str | None = Field(None, description="How to fix or improve it")

class StructuredExplanationOutput(BaseModel):
    summary: str = Field("", description="High-level summary of the code and its purpose")
    line_explanations: list[LineExplanationItem] = Field(default_factory=list, description="Explanations mapped strictly to actual source lines")
    concepts: list[ConceptItem] = Field(default_factory=list, description="Core programming concepts demonstrated")
    issues: list[IssueItem] = Field(default_factory=list, description="Potential issues, security risks, bugs, or performance bottlenecks")
    execution_walkthrough: list[str] = Field(default_factory=list, description="Step-by-step runtime execution or logic walkthrough")
    key_takeaways: list[str] = Field(default_factory=list, description="Key learning takeaways for the developer")
    suggested_improvements: list[str] = Field(default_factory=list, description="Concrete suggestions to improve or optimize the code")
    uncertainty_notes: list[str] = Field(default_factory=list, description="Explicit disclosures of any uncertainties or assumptions")
    complexity: AlgorithmComplexity | None = Field(None, description="Complexity analysis if provided")
    hints: list[Any] = Field(default_factory=list, description="Optional hints list")

class LearnerProfile(BaseModel):
    level: str = Field("beginner", description="Learner expertise level: absolute beginner, beginner, intermediate, expert")
    mode: str = Field("beginner", description="Requested explanation mode: absolute beginner, beginner, intermediate, expert, line-by-line, debugging, security, performance")
    locale: str = Field("en", description="Target locale / language")
    focus_areas: list[str] = Field(default_factory=list, description="Special focus areas")

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
    static_hints: list[AnalysisFinding] = Field(default_factory=list, description="Static analysis rule findings (compatible with StaticHint)")
    findings: list[AnalysisFinding] = Field(default_factory=list, description="Structured analysis findings with beginner explanations")
    complexity_score: int = Field(1, description="Total cyclomatic complexity score")
    cyclomatic_complexity: int = Field(1, description="Cyclomatic complexity score")
    max_nesting_depth: int = Field(0, description="Maximum indentation / nesting level")
    maximum_nesting_depth: int = Field(0, description="Maximum indentation / nesting level")
    function_count: int = Field(0, description="Number of functions defined")
    class_count: int = Field(0, description="Number of classes defined")
    import_count: int = Field(0, description="Number of import statements")
    lines_of_code: dict[str, int] = Field(default_factory=dict, description="Breakdown of lines: total, code, comment, blank")
    duplicate_patterns: list[dict[str, Any]] = Field(default_factory=list, description="Repeated pattern findings")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Detailed metrics (lines, tokens, counts)")
    summary: str = Field("", description="Overview summary of code structure and findings")

    # Legacy & convenience fields for backward compatibility
    functions: list[Any] = Field(default_factory=list)
    classes: list[Any] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.is_valid_syntax

    @property
    def loops(self) -> list[LoopConstruct]:
        return self.constructs.loops if self.constructs else []

    @property
    def conditions(self) -> list[ConditionConstruct]:
        return self.constructs.conditions if self.constructs else []

    @property
    def assignments(self) -> list[AssignmentConstruct]:
        return self.constructs.assignments if self.constructs else []

    @property
    def calls(self) -> list[CallConstruct]:
        return self.constructs.calls if self.constructs else []

    @property
    def hints(self) -> list[AnalysisFinding]:
        return self.static_hints or self.findings

    @property
    def complexity(self) -> int:
        return self.complexity_score

    @model_validator(mode="after")
    def _populate_convenience_accessors(self) -> "CodeAnalysisResponse":
        if self.constructs:
            if not self.functions and self.constructs.functions:
                self.functions = list(self.constructs.functions)  # type: ignore
            if not self.classes and self.constructs.classes:
                self.classes = list(self.constructs.classes)  # type: ignore
        return self


# Alias AnalysisResult to CodeAnalysisResponse for unified interface
AnalysisResult = CodeAnalysisResponse


from backend.schemas.rag import RAGSourceCitation


class ExplainCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000, description="Code snippet to explain")
    language: LanguageType = Field("python", description="Programming language")
    filename: str | None = Field(None, description="Optional filename")
    level: str = Field("Beginner", description="Desired level of explanation (e.g. Absolute Beginner, Beginner, Intermediate, Expert)")
    mode: str | None = Field(None, description="Explanation mode: absolute beginner, beginner, intermediate, expert, line-by-line, debugging, security, performance")
    include_ast_analysis: bool = Field(True, description="Whether to include AST parsing metadata")
    enable_trace: bool = Field(True, description="Whether to run execution trace if applicable")
    enable_rag: bool = Field(True, description="Whether to retrieve and ground explanation on RAG knowledge base")
    save_history: bool = Field(True, description="Whether to persist the explanation in SQLite")
    user_id: int | None = Field(None, description="Optional authenticated user ID")
    learner_profile: LearnerProfile | None = Field(None, description="Learner profile details")


    @field_validator("code")
    @classmethod
    def validate_code_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Code snippet cannot be empty or solely whitespace.")
        return v


class ExplanationValidationResult(BaseModel):
    valid: bool = Field(..., description="Whether the explanation passed deterministic grounding checks")
    coverage_score: float = Field(..., description="Proportion of significant source lines explained (0.0 to 1.0)")
    referenced_lines: list[int] = Field(default_factory=list, description="Validated source lines directly referenced in the explanation")
    invalid_references: list[int] = Field(default_factory=list, description="Referenced line numbers that do not exist in the source code")
    unsupported_claims: list[str] = Field(default_factory=list, description="Claims about AST constructs or symbols not supported by code/AST")
    warnings: list[str] = Field(default_factory=list, description="Warnings regarding coverage, static finding drift, or assumptions")
    grounding_level: str = Field("High", description="Confidence rating: High, Moderate, Low")
    repaired: bool = Field(False, description="Whether the response was deterministically repaired after validation")

class ExplainCodeResponse(BaseModel):
    id: int | None = Field(None, description="Record ID if saved to database")
    language: str
    level: str
    summary: str = Field(..., description="Overall summary of the code")
    blocks: list[BlockExplanation] = Field(default_factory=list, description="Block-by-block explanations")
    concepts: list[ConceptTag] = Field(default_factory=list, description="Concept tags with simple definitions")
    algorithm_steps: list[str] = Field(default_factory=list, description="Algorithm steps")
    complexity: AlgorithmComplexity = Field(..., description="Complexity estimates")
    hints: list[str] = Field(default_factory=list, description="Common mistakes and improvement hints")
    ast_analysis: CodeAnalysisResponse | None = None
    rag_sources: list[RAGSourceCitation] = Field(default_factory=list, description="Retrieved RAG knowledge citations and references")
    rag_context_used: bool = Field(False, description="Whether RAG knowledge was retrieved and used in the explanation")
    
    # Enhanced structured pipeline fields
    structured_output: StructuredExplanationOutput | None = None
    line_explanations: list[LineExplanationItem] = Field(default_factory=list, description="Line-by-line explanations referencing actual source lines")
    issues: list[IssueItem] = Field(default_factory=list, description="Categorized issues and findings")
    execution_walkthrough: list[str] = Field(default_factory=list, description="Runtime execution trace walkthrough")
    key_takeaways: list[str] = Field(default_factory=list, description="Key takeaways")
    suggested_improvements: list[str] = Field(default_factory=list, description="Actionable improvement suggestions")
    uncertainty_notes: list[str] = Field(default_factory=list, description="Disclosures of any uncertainties")
    execution_trace: Any | None = Field(None, description="Trace response if tracing was executed")
    explanation_mode: str = Field("beginner", description="Mode used for generating the explanation")
    validation_result: ExplanationValidationResult | None = Field(None, description="Deterministic grounding validation report")
    
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
