"""Rule checking for control flow issues such as infinite loops and unreachable code."""

import ast
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule


class ControlFlowRule(BaseStaticRule):
    """Detects control flow anomalies including infinite loops, unreachable statements, and duplicate branches."""

    @property
    def rule_id(self) -> str:
        return "CONTROL_FLOW_ISSUE"

    @property
    def category(self) -> str:
        return "control flow"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            findings.extend(self._analyze_python(ast_tree))
        return findings

    def _analyze_python(self, tree: ast.AST) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []

        for node in ast.walk(tree):
            # 1. Check for infinite loops: while True: without break, return, raise
            if isinstance(node, ast.While):
                is_constant_true = False
                if isinstance(node.test, ast.Constant) and bool(node.test.value) is True:
                    is_constant_true = True
                elif isinstance(node.test, ast.NameConstant) and node.test.value is True:  # Python 3.7 compat
                    is_constant_true = True

                if is_constant_true:
                    has_exit = False
                    for child in ast.walk(node):
                        if isinstance(child, (ast.Break, ast.Return, ast.Raise)):
                            has_exit = True
                            break
                    if not has_exit:
                        findings.append(
                            AnalysisFinding(
                                rule_id="INFINITE_LOOP",
                                language="python",
                                severity="warning",
                                line_number=node.lineno,
                                column_number=getattr(node, "col_offset", None),
                                category=self.category,
                                title="Potential Infinite Loop Detected",
                                technical_description=(
                                    "A `while True` loop was detected that contains no `break`, `return`, or `raise` statements."
                                ),
                                beginner_explanation=(
                                    "This loop has a condition that is always True (`while True`) and doesn't contain a way to exit. "
                                    "When executed, this program will run forever and freeze or crash your machine."
                                ),
                                suggested_fix="Add a condition to exit the loop using `break`, or update the `while` condition so it eventually turns False.",
                                line_start=node.lineno,
                                line_end=getattr(node, "end_lineno", node.lineno),
                            )
                        )

            # 2. Check for unreachable code after return/break/continue/raise
            if hasattr(node, "body") and isinstance(node.body, list):
                self._check_unreachable_in_body(node.body, findings)
            if hasattr(node, "orelse") and isinstance(node.orelse, list):
                self._check_unreachable_in_body(node.orelse, findings)

            # 3. Check for duplicate branches in if-else
            if isinstance(node, ast.If) and node.orelse:
                # Compare bodies as dumped AST strings
                if len(node.body) > 0 and len(node.orelse) > 0:
                    body_dumps = [ast.dump(s) for s in node.body]
                    orelse_dumps = [ast.dump(s) for s in node.orelse]
                    if body_dumps == orelse_dumps:
                        findings.append(
                            AnalysisFinding(
                                rule_id="DUPLICATE_BRANCH",
                                language="python",
                                severity="info",
                                line_number=node.lineno,
                                column_number=getattr(node, "col_offset", None),
                                category=self.category,
                                title="Duplicate 'if' and 'else' Branches",
                                technical_description="The 'if' and 'else' branches execute identical statements.",
                                beginner_explanation=(
                                    "Both the `if` condition and the `else` condition perform the exact same actions. "
                                    "This means the conditional check doesn't change what happens."
                                ),
                                suggested_fix="Remove the condition or update one branch to perform the intended different behavior.",
                                line_start=node.lineno,
                                line_end=getattr(node, "end_lineno", node.lineno),
                            )
                        )

        return findings

    def _check_unreachable_in_body(self, stmts: list[ast.stmt], findings: list[AnalysisFinding]) -> None:
        terminating_seen = False
        for stmt in stmts:
            if terminating_seen:
                findings.append(
                    AnalysisFinding(
                        rule_id="UNREACHABLE_CODE",
                        language="python",
                        severity="warning",
                        line_number=stmt.lineno,
                        column_number=getattr(stmt, "col_offset", None),
                        category=self.category,
                        title="Unreachable Code Detected",
                        technical_description="Statements placed after a terminal jump statement (return, raise, break, continue) cannot be reached.",
                        beginner_explanation=(
                            "This code is written immediately after a `return`, `break`, `continue`, or `raise` statement. "
                            "Because the previous line immediately exits or jumps, this line will never be executed by Python."
                        ),
                        suggested_fix="Move this code before the exit statement, or remove it if it is no longer needed.",
                        line_start=stmt.lineno,
                        line_end=getattr(stmt, "end_lineno", stmt.lineno),
                    )
                )
                break  # Flag first unreachable statement in block
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                terminating_seen = True
