"""Rule identifying syntax errors with beginner-friendly explanations."""

import ast
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule


class SyntaxErrorsRule(BaseStaticRule):
    """Detects syntax and parsing errors in code."""

    @property
    def rule_id(self) -> str:
        return "SYNTAX_ERROR"

    @property
    def category(self) -> str:
        return "syntax"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[AnalysisFinding]:
        hints: list[AnalysisFinding] = []
        if language == "python":
            hints.extend(self._analyze_python(code, ast_tree))
        elif language == "javascript":
            hints.extend(self._analyze_javascript(ast_tree))
        return hints

    def _analyze_python(self, code: str, ast_tree: Any) -> list[AnalysisFinding]:
        hints: list[AnalysisFinding] = []
        if ast_tree is None:
            try:
                ast.parse(code)
            except SyntaxError as exc:
                msg = exc.msg or "Invalid syntax"
                lineno = exc.lineno or 1
                offset = exc.offset or 1
                text = (exc.text or "").strip()

                beginner_explanation = self._explain_syntax_error(msg, text)
                suggested_fix = self._suggest_syntax_fix(msg, text)

                hints.append(
                    AnalysisFinding(
                        rule_id=self.rule_id,
                        language="python",
                        severity="error",
                        line_number=lineno,
                        column_number=offset,
                        category=self.category,
                        title=f"Syntax Error: {msg}",
                        technical_description=f"Python parser failed at line {lineno}, column {offset}: {msg}",
                        beginner_explanation=beginner_explanation,
                        suggested_fix=suggested_fix,
                        line_start=lineno,
                        line_end=lineno,
                    )
                )
        return hints

    def _analyze_javascript(self, ast_tree: Any) -> list[AnalysisFinding]:
        hints: list[AnalysisFinding] = []
        if ast_tree and hasattr(ast_tree, "root_node"):
            def visit_node(node: Any) -> None:
                if node.is_missing or node.type == "ERROR":
                    start_line = node.start_point[0] + 1
                    start_col = node.start_point[1]
                    hints.append(
                        AnalysisFinding(
                            rule_id=self.rule_id,
                            language="javascript",
                            severity="error",
                            line_number=start_line,
                            column_number=start_col,
                            category=self.category,
                            title="JavaScript Syntax Error",
                            technical_description=f"Syntax node parse error at line {start_line}, column {start_col}",
                            beginner_explanation=(
                                "There is a syntax error near this line. In JavaScript, this often means a missing closing bracket `}`, "
                                "a missing parenthesis `)`, an unmatched quote, or an invalid keyword."
                            ),
                            suggested_fix="Check your brackets, parentheses, and semicolons near this line.",
                            line_start=start_line,
                            line_end=node.end_point[0] + 1,
                        )
                    )
                for child in getattr(node, "children", []):
                    visit_node(child)

            visit_node(ast_tree.root_node)
        return hints

    def _explain_syntax_error(self, msg: str, text: str) -> str:
        low = msg.lower()
        if "expected ':'" in low:
            return "In Python, header statements like `def`, `if`, `for`, `while`, `class`, and `try` must end with a colon `:`."
        if "unmatched" in low or "was never closed" in low:
            return "You opened a bracket, parenthesis, or quote that was never closed. Python expects every `(`, `[`, `{` to have a matching pair."
        if "unexpected indent" in low:
            return "Python uses whitespace indentation to structure blocks of code. This line has spaces or tabs that don't match the surrounding block."
        if "expected an indented block" in low:
            return "After a statement ending with a colon `:` (like `def` or `if`), the next line must be indented by 4 spaces."
        if "invalid syntax" in low and "=" in text:
            return "Make sure you aren't using a single `=` (assignment) where you meant `==` (comparison), or assigning to a function call."
        return f"Python encountered a structure it cannot understand: '{msg}'. Check for typos, missing punctuation, or misplaced keywords."

    def _suggest_syntax_fix(self, msg: str, text: str) -> str:
        low = msg.lower()
        if "expected ':'" in low:
            return "Add a `:` to the end of the line."
        if "unmatched" in low or "was never closed" in low:
            return "Add the corresponding closing parenthesis `)`, bracket `]`, or quote."
        if "indent" in low:
            return "Align the indentation of this line with the previous statements in the same block."
        return "Review the code around this line for missing operators, quotes, or colons."
