"""Rule checking for common performance antipatterns like string concatenation in loops."""

import ast
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule


class PerformanceRule(BaseStaticRule):
    """Detects performance antipatterns such as repeated string concatenation in loops."""

    @property
    def rule_id(self) -> str:
        return "PERFORMANCE_ANTIPATTERN"

    @property
    def category(self) -> str:
        return "performance"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            findings.extend(self._analyze_python(ast_tree))
        return findings

    def _analyze_python(self, tree: ast.AST) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []

        for node in ast.walk(tree):
            # Check for string concatenation in loop: s += ...
            if isinstance(node, (ast.For, ast.While)):
                for child in node.body:
                    for sub in ast.walk(child):
                        if isinstance(sub, ast.AugAssign) and isinstance(sub.op, ast.Add):
                            if isinstance(sub.target, ast.Name):
                                # Check if variable name looks like string or value being added is string/call
                                is_str_target = any(k in sub.target.id.lower() for k in ("str", "msg", "text", "line", "html", "out"))
                                is_str_val = (
                                    (isinstance(sub.value, ast.Constant) and isinstance(sub.value.value, str))
                                    or (isinstance(sub.value, ast.Call) and isinstance(sub.value.func, ast.Name) and sub.value.func.id == "str")
                                )
                                if is_str_target or is_str_val:
                                    findings.append(
                                        AnalysisFinding(
                                            rule_id="INEFFICIENT_STRING_CONCAT",
                                            language="python",
                                            severity="info",
                                            line_number=sub.lineno,
                                            column_number=getattr(sub, "col_offset", None),
                                            category=self.category,
                                            title=f"Repeated string concatenation on '{sub.target.id}' in loop",
                                            technical_description=(
                                                "Using `+=` to accumulate strings inside a loop causes O(n^2) time complexity "
                                                "due to string immutability in Python creating a new copy each iteration."
                                            ),
                                            beginner_explanation=(
                                                f"In Python, strings cannot be modified in place. Each time you run `{sub.target.id} += ...` "
                                                "inside this loop, Python copies the entire text to a new memory location. "
                                                "For large data, this makes your code run very slowly."
                                            ),
                                            suggested_fix=(
                                                f"Append each piece to a list: `parts.append(...)` and join them all at once at the end: "
                                                f"`{sub.target.id} = ''.join(parts)`."
                                            ),
                                            line_start=sub.lineno,
                                            line_end=sub.lineno,
                                        )
                                    )

        return findings
