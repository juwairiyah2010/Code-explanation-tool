"""Rule checking for inconsistent or missing return statements in functions."""

import ast
from typing import Any
from backend.schemas.explanation import StaticHint
from backend.services.analysis.rules.base_rule import BaseStaticRule


class MissingReturnsRule(BaseStaticRule):
    """Detects functions that return values on some paths but fall through on others."""

    @property
    def rule_id(self) -> str:
        return "MISSING_RETURN"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[StaticHint]:
        hints: list[StaticHint] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            hints.extend(self._analyze_python(ast_tree))
        elif language == "javascript":
            hints.extend(self._analyze_javascript(code, ast_tree))
        return hints

    def _analyze_python(self, tree: ast.AST) -> list[StaticHint]:
        hints: list[StaticHint] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Ignore generators and special methods like __init__
                if node.name in ("__init__", "__post_init__"):
                    continue

                returns_with_value = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Return) and sub.value is not None:
                        returns_with_value.append(sub)

                if returns_with_value:
                    # Check if the last statement in the top-level body is a return or raise
                    last_stmt = node.body[-1] if node.body else None
                    if last_stmt and not isinstance(last_stmt, (ast.Return, ast.Raise)):
                        # If the last statement is an If statement, check if both body and orelse return
                        if isinstance(last_stmt, ast.If):
                            has_else_return = any(isinstance(s, (ast.Return, ast.Raise)) for s in last_stmt.orelse)
                            if not has_else_return:
                                hints.append(
                                    StaticHint(
                                        rule_id=self.rule_id,
                                        severity="info",
                                        message=f"Function '{node.name}' has return values in some branches, but may fall through without an explicit return.",
                                        line_start=node.lineno,
                                        line_end=getattr(node, "end_lineno", node.lineno),
                                        suggestion="Ensure all execution branches explicitly return a value or raise an exception.",
                                    )
                                )
                        else:
                            hints.append(
                                StaticHint(
                                    rule_id=self.rule_id,
                                    severity="info",
                                    message=f"Function '{node.name}' returns a value on line {returns_with_value[0].lineno}, but does not explicitly return at the end of the function.",
                                    line_start=node.lineno,
                                    line_end=getattr(node, "end_lineno", node.lineno),
                                    suggestion="Add an explicit fallback return (e.g. 'return None' or default value).",
                                )
                            )

        return hints

    def _analyze_javascript(self, code: str, ast_tree: Any) -> list[StaticHint]:
        hints: list[StaticHint] = []
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
                        # Do not traverse into nested functions
                        if n != node and n.type in ("function_declaration", "arrow_function", "method_definition"):
                            return
                        for c in n.children:
                            find_returns(c)

                    find_returns(node)

                    # If it has returns with values, check if body ends with return
                    if return_stmts:
                        # Find statement block
                        for child in node.children:
                            if child.type == "statement_block":
                                non_empty = [c for c in child.children if c.type not in ("{", "}", "comment")]
                                if non_empty and non_empty[-1].type not in ("return_statement", "throw_statement"):
                                    start_line = node.start_point[0] + 1
                                    end_line = node.end_point[0] + 1
                                    hints.append(
                                        StaticHint(
                                            rule_id=self.rule_id,
                                            severity="info",
                                            message=f"Function '{func_name}' has return statements but ends without an explicit return.",
                                            line_start=start_line,
                                            line_end=end_line,
                                            suggestion="Ensure all control branches return a consistent value.",
                                        )
                                    )

                for child in node.children:
                    check_js_func(child)

            check_js_func(ast_tree.root_node)
        return hints
