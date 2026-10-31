"""Rule checking code quality patterns like mutable default arguments and redundant boolean comparisons."""

import ast
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule


class CodeQualityRule(BaseStaticRule):
    """Detects code quality and idiomatic code issues."""

    @property
    def rule_id(self) -> str:
        return "CODE_QUALITY"

    @property
    def category(self) -> str:
        return "code quality"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            findings.extend(self._analyze_python(ast_tree))
        return findings

    def _analyze_python(self, tree: ast.AST) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []

        for node in ast.walk(tree):
            # 1. Mutable default arguments in functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default is not None and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        type_name = "list" if isinstance(default, ast.List) else ("dict" if isinstance(default, ast.Dict) else "set")
                        findings.append(
                            AnalysisFinding(
                                rule_id="MUTABLE_DEFAULT_ARG",
                                language="python",
                                severity="warning",
                                line_number=default.lineno,
                                column_number=getattr(default, "col_offset", None),
                                category=self.category,
                                title=f"Mutable default argument ({type_name}) in '{node.name}'",
                                technical_description=f"Default argument in '{node.name}' uses a mutable container ({type_name}).",
                                beginner_explanation=(
                                    f"In Python, default arguments are created only ONCE when the function is defined, not every time it is called. "
                                    f"If you modify this {type_name} inside the function, changes will persist across future function calls, causing bizarre bugs!"
                                ),
                                suggested_fix=f"Use `None` as the default argument value: `def {node.name}(..., param=None):` and initialize inside: `if param is None: param = []`.",
                                line_start=default.lineno,
                                line_end=getattr(default, "end_lineno", default.lineno),
                            )
                        )

            # 2. Redundant boolean comparison: x == True or x == False
            if isinstance(node, ast.Compare):
                for op, comparator in zip(node.ops, node.comparators):
                    if isinstance(op, (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)):
                        is_bool = False
                        bool_val = None
                        if isinstance(comparator, ast.Constant) and isinstance(comparator.value, bool):
                            is_bool = True
                            bool_val = comparator.value
                        elif isinstance(comparator, ast.NameConstant) and isinstance(comparator.value, bool):
                            is_bool = True
                            bool_val = comparator.value

                        if is_bool:
                            findings.append(
                                AnalysisFinding(
                                    rule_id="REDUNDANT_BOOLEAN_COMPARISON",
                                    language="python",
                                    severity="info",
                                    line_number=node.lineno,
                                    column_number=getattr(node, "col_offset", None),
                                    category=self.category,
                                    title=f"Redundant comparison with boolean literal '{bool_val}'",
                                    technical_description=f"Comparison expression explicitly compares against boolean literal '{bool_val}'.",
                                    beginner_explanation=(
                                        f"In Python, expressions are already evaluated for truthiness. Writing `if condition == {bool_val}:` "
                                        f"is redundant and considered unpythonic."
                                    ),
                                    suggested_fix="Write `if condition:` or `if not condition:` instead.",
                                    line_start=node.lineno,
                                    line_end=getattr(node, "end_lineno", node.lineno),
                                )
                            )

            # 3. Unnecessary pass statement in non-empty block
            if hasattr(node, "body") and isinstance(node.body, list) and len(node.body) > 1:
                for stmt in node.body:
                    if isinstance(stmt, ast.Pass):
                        findings.append(
                            AnalysisFinding(
                                rule_id="UNNECESSARY_PASS",
                                language="python",
                                severity="info",
                                line_number=stmt.lineno,
                                column_number=getattr(stmt, "col_offset", None),
                                category=self.category,
                                title="Unnecessary 'pass' statement",
                                technical_description="'pass' is only needed as a placeholder when a block has no other statements.",
                                beginner_explanation=(
                                    "`pass` in Python is a placeholder used only when a block has no other code. "
                                    "Since this block already has working statements, `pass` does nothing."
                                ),
                                suggested_fix="Remove the `pass` statement.",
                                line_start=stmt.lineno,
                                line_end=stmt.lineno,
                            )
                        )

        return findings
