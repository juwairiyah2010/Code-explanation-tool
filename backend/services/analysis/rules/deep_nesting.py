"""Rule checking for excessive nesting depth in control flow and blocks."""

import ast
from typing import Any
from backend.schemas.explanation import StaticHint
from backend.services.analysis.rules.base_rule import BaseStaticRule

MAX_RECOMMENDED_DEPTH = 3


class DeepNestingRule(BaseStaticRule):
    """Detects control flow blocks nested deeper than the recommended threshold."""

    def __init__(self, max_depth: int = MAX_RECOMMENDED_DEPTH):
        self.max_depth = max_depth

    @property
    def rule_id(self) -> str:
        return "DEEP_NESTING"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[StaticHint]:
        hints: list[StaticHint] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            hints.extend(self._analyze_python(ast_tree))
        elif language == "javascript":
            hints.extend(self._analyze_javascript(code, ast_tree))
        return hints

    def _analyze_python(self, tree: ast.AST) -> list[StaticHint]:
        hints: list[StaticHint] = []

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
                hints.append(
                    StaticHint(
                        rule_id=self.rule_id,
                        severity="warning",
                        message=f"Deeply nested control structure at depth {new_depth} (exceeds recommended threshold of {self.max_depth}).",
                        line_start=node.lineno,
                        line_end=end_lineno,
                        suggestion="Refactor using guard clauses, early returns, or decompose into smaller helper functions.",
                    )
                )

            for child in ast.iter_child_nodes(node):
                check_node(child, new_depth)

        check_node(tree, 0)
        return hints

    def _analyze_javascript(self, code: str, ast_tree: Any) -> list[StaticHint]:
        hints: list[StaticHint] = []
        if ast_tree and hasattr(ast_tree, "root_node"):
            # Tree-sitter AST
            def check_ts_node(node: Any, current_depth: int) -> None:
                is_nest = node.type in (
                    "if_statement",
                    "for_statement",
                    "for_in_statement",
                    "for_of_statement",
                    "while_statement",
                    "do_statement",
                    "try_statement",
                    "switch_statement",
                )
                new_depth = current_depth + 1 if is_nest else current_depth
                if is_nest and new_depth > self.max_depth:
                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1
                    hints.append(
                        StaticHint(
                            rule_id=self.rule_id,
                            severity="warning",
                            message=f"Deeply nested block at depth {new_depth} (exceeds recommended threshold of {self.max_depth}).",
                            line_start=start_line,
                            line_end=end_line,
                            suggestion="Refactor with guard clauses, early returns, or extract helper functions.",
                        )
                    )
                for child in node.children:
                    check_ts_node(child, new_depth)

            check_ts_node(ast_tree.root_node, 0)
        else:
            # Indentation-based heuristic fallback
            for i, line in enumerate(code.splitlines(), start=1):
                if not line.strip() or line.strip().startswith("//"):
                    continue
                leading_spaces = len(line) - len(line.lstrip(" "))
                depth = leading_spaces // 4 if "    " in line else leading_spaces // 2
                if depth > self.max_depth + 1 and any(kw in line for kw in ("if ", "for ", "while ", "switch ")):
                    hints.append(
                        StaticHint(
                            rule_id=self.rule_id,
                            severity="warning",
                            message=f"Deeply nested structure detected at line {i} (depth ~{depth}).",
                            line_start=i,
                            line_end=i,
                            suggestion="Refactor complex blocks using early returns or modular methods.",
                        )
                    )
        return hints
