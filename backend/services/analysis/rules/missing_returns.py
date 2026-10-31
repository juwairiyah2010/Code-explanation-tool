"""Rule checking for inconsistent or missing return statements in functions."""

import ast
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule


class MissingReturnsRule(BaseStaticRule):
    """Detects functions that return values on some paths but fall through on others."""

    @property
    def rule_id(self) -> str:
        return "MISSING_RETURN"

    @property
    def category(self) -> str:
        return "return behavior"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[AnalysisFinding]:
        hints: list[AnalysisFinding] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            hints.extend(self._analyze_python(ast_tree))
        elif language == "javascript":
            hints.extend(self._analyze_javascript(code, ast_tree))
        return hints

    def _analyze_python(self, tree: ast.AST) -> list[AnalysisFinding]:
        hints: list[AnalysisFinding] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in ("__init__", "__post_init__"):
                    continue

                returns_with_value = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Return) and sub.value is not None:
                        returns_with_value.append(sub)

                if returns_with_value:
                    last_stmt = node.body[-1] if node.body else None
                    if last_stmt and not isinstance(last_stmt, (ast.Return, ast.Raise)):
                        if isinstance(last_stmt, ast.If):
                            has_else_return = any(isinstance(s, (ast.Return, ast.Raise)) for s in last_stmt.orelse)
                            if not has_else_return:
                                hints.append(
                                    AnalysisFinding(
                                        rule_id=self.rule_id,
                                        language="python",
                                        severity="warning",
                                        line_number=node.lineno,
                                        column_number=getattr(node, "col_offset", None),
                                        category=self.category,
                                        title=f"Function '{node.name}' has incomplete return branches",
                                        technical_description=(
                                            f"Function '{node.name}' returns explicit values on some code paths, "
                                            "but the conditional branch falls through without an explicit return statement."
                                        ),
                                        beginner_explanation=(
                                            f"When Python runs your function '{node.name}', if the `if` conditions aren't met, "
                                            "it will silently finish and return `None`. If someone expects a number or string back, "
                                            "this can lead to unexpected crashes later in the program."
                                        ),
                                        suggested_fix="Add an `else` branch or a default `return` at the bottom of the function.",
                                        line_start=node.lineno,
                                        line_end=getattr(node, "end_lineno", node.lineno),
                                    )
                                )
                        else:
                            hints.append(
                                AnalysisFinding(
                                    rule_id=self.rule_id,
                                    language="python",
                                    severity="warning",
                                    line_number=node.lineno,
                                    column_number=getattr(node, "col_offset", None),
                                    category=self.category,
                                    title=f"Function '{node.name}' does not return on all paths",
                                    technical_description=(
                                        f"Function '{node.name}' returns a value on line {returns_with_value[0].lineno}, "
                                        "but does not terminate with an explicit return statement."
                                    ),
                                    beginner_explanation=(
                                        f"Your function '{node.name}' gives back a result in some cases, but reaches the end "
                                        "of the function body without returning anything. Python will give back `None` by default."
                                    ),
                                    suggested_fix="Ensure every path through the function finishes with a `return <value>` statement.",
                                    line_start=node.lineno,
                                    line_end=getattr(node, "end_lineno", node.lineno),
                                )
                            )

        return hints

    def _analyze_javascript(self, code: str, ast_tree: Any) -> list[AnalysisFinding]:
        hints: list[AnalysisFinding] = []
        if ast_tree and hasattr(ast_tree, "root_node"):
            def check_js_func(node: Any) -> None:
                if node.type in ("function_declaration", "method_definition"):
                    func_name = "function"
                    for child in node.children:
                        if child.type in ("identifier", "property_identifier"):
                            func_name = child.text.decode("utf8")

                    return_stmts = []
                    def find_returns(n: Any) -> None:
                        if n.type == "return_statement" and len(n.children) > 1:
                            return_stmts.append(n)
                        if n != node and n.type in ("function_declaration", "arrow_function", "method_definition"):
                            return
                        for c in n.children:
                            find_returns(c)

                    find_returns(node)

                    if return_stmts:
                        for child in node.children:
                            if child.type == "statement_block":
                                non_empty = [c for c in child.children if c.type not in ("{", "}", "comment")]
                                if non_empty and non_empty[-1].type not in ("return_statement", "throw_statement"):
                                    start_line = node.start_point[0] + 1
                                    start_col = node.start_point[1]
                                    end_line = node.end_point[0] + 1
                                    hints.append(
                                        AnalysisFinding(
                                            rule_id=self.rule_id,
                                            language="javascript",
                                            severity="warning",
                                            line_number=start_line,
                                            column_number=start_col,
                                            category=self.category,
                                            title=f"Function '{func_name}' has missing return path",
                                            technical_description=(
                                                f"JavaScript function '{func_name}' returns explicit expressions in some statements, "
                                                "but control flow reaches the end of block without a return statement (evaluating to undefined)."
                                            ),
                                            beginner_explanation=(
                                                f"In JavaScript, if a function doesn't hit a `return` statement, it automatically returns `undefined`. "
                                                f"Since '{func_name}' returns data elsewhere, you likely want to make sure it returns a consistent value everywhere."
                                            ),
                                            suggested_fix="Add an explicit fallback return or handle the remaining cases.",
                                            line_start=start_line,
                                            line_end=end_line,
                                        )
                                    )

                for child in node.children:
                    check_js_func(child)

            check_js_func(ast_tree.root_node)
        return hints
