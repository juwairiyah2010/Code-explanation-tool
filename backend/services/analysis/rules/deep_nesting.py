"""Rule checking for excessive nesting depth in control flow and blocks."""

import ast
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule

MAX_RECOMMENDED_DEPTH = 3


class DeepNestingRule(BaseStaticRule):
    """Detects control flow blocks nested deeper than the recommended threshold."""

    def __init__(self, max_depth: int = MAX_RECOMMENDED_DEPTH):
        self.max_depth = max_depth

    @property
    def rule_id(self) -> str:
        return "DEEP_NESTING"

    @property
    def category(self) -> str:
        return "complexity"

    def analyze(
        self, code: str, language: str, ast_tree: Any, raw_constructs: Any
    ) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            findings.extend(self._analyze_python(ast_tree))
        elif language == "javascript":
            findings.extend(self._analyze_javascript(code, ast_tree))
        return findings

    def _analyze_python(self, tree: ast.AST) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []

        def check_node(node: ast.AST, current_depth: int) -> None:
            is_nesting_construct = isinstance(
                node,
                (
                    ast.If,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                    ast.Try,
                    ast.With,
                    ast.AsyncWith,
                ),
            )

            new_depth = current_depth + 1 if is_nesting_construct else current_depth

            if is_nesting_construct and new_depth > self.max_depth:
                end_lineno = getattr(node, "end_lineno", node.lineno)
                col = getattr(node, "col_offset", None)
                tech_desc = f"Deeply nested control structure at depth {new_depth} (exceeds recommended threshold of {self.max_depth})."
                beginner_exp = (
                    f"Your code is indented {new_depth} levels deep (like boxes inside boxes inside boxes). "
                    f"When code is nested too deeply, it becomes very hard to keep track of all the conditions "
                    f"required to reach this line. This is often called the 'Pyramid of Doom'."
                )
                suggested_fix = (
                    "Use 'guard clauses' (check for invalid cases early and `return` immediately), "
                    "or extract the inner loop/logic into a separate helper function."
                )
                findings.append(
                    AnalysisFinding(
                        rule_id=self.rule_id,
                        language="python",
                        severity="warning",
                        line_number=node.lineno,
                        column_number=col,
                        category="complexity",
                        title="Excessive Nesting Depth",
                        technical_description=tech_desc,
                        beginner_explanation=beginner_exp,
                        suggested_fix=suggested_fix,
                        line_start=node.lineno,
                        line_end=end_lineno,
                        message=tech_desc,
                        suggestion=suggested_fix,
                    )
                )

            for child in ast.iter_child_nodes(node):
                check_node(child, new_depth)

        for top_node in ast.iter_child_nodes(tree):
            check_node(top_node, 0)

        return findings

    def _analyze_javascript(self, code: str, ast_tree: Any) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                continue

            leading_spaces = len(line) - len(stripped)
            indent_level = leading_spaces // 4 if "\t" not in line else leading_spaces
            if "\t" in line:
                indent_level = line.count("\t")

            if indent_level > self.max_depth and any(
                stripped.startswith(kw) for kw in ("if", "for", "while", "switch", "try")
            ):
                tech_desc = f"Deeply nested block at indentation level {indent_level} (exceeds {self.max_depth})."
                beginner_exp = (
                    f"This block is nested {indent_level} levels deep. Code that slopes sharply to the right "
                    f"makes it difficult to read and test."
                )
                suggested_fix = (
                    "Refactor using early returns or extract inner loops into named functions."
                )
                findings.append(
                    AnalysisFinding(
                        rule_id=self.rule_id,
                        language="javascript",
                        severity="warning",
                        line_number=idx,
                        column_number=leading_spaces,
                        category="complexity",
                        title="Excessive Nesting Depth",
                        technical_description=tech_desc,
                        beginner_explanation=beginner_exp,
                        suggested_fix=suggested_fix,
                        line_start=idx,
                        line_end=idx,
                        message=tech_desc,
                        suggestion=suggested_fix,
                    )
                )

        return findings
