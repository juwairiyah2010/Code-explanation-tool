"""Rule checking for dangerous or unhandled exception patterns."""

import ast
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule


class ExceptionHandlingRule(BaseStaticRule):
    """Detects bare except clauses, silent pass handlers, and broad catch blocks."""

    @property
    def rule_id(self) -> str:
        return "EXCEPTION_HANDLING"

    @property
    def category(self) -> str:
        return "exception handling"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            findings.extend(self._analyze_python(ast_tree))
        return findings

    def _analyze_python(self, tree: ast.AST) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # 1. Bare except:
                if node.type is None:
                    findings.append(
                        AnalysisFinding(
                            rule_id="BARE_EXCEPT",
                            language="python",
                            severity="warning",
                            line_number=node.lineno,
                            column_number=getattr(node, "col_offset", None),
                            category=self.category,
                            title="Bare 'except:' Clause Used",
                            technical_description="A bare 'except:' catches all exceptions, including KeyboardInterrupt and SystemExit.",
                            beginner_explanation=(
                                "Writing `except:` without an error name catches *every* possible problem in Python, "
                                "including when you press Ctrl+C to stop the program! This hides critical errors and makes bugs almost impossible to find."
                            ),
                            suggested_fix="Catch specific exceptions, like `except ValueError:` or `except Exception:`.",
                            line_start=node.lineno,
                            line_end=getattr(node, "end_lineno", node.lineno),
                        )
                    )
                elif isinstance(node.type, ast.Name) and node.type.id == "BaseException":
                    findings.append(
                        AnalysisFinding(
                            rule_id="BROAD_EXCEPT_BASE",
                            language="python",
                            severity="warning",
                            line_number=node.lineno,
                            column_number=getattr(node, "col_offset", None),
                            category=self.category,
                            title="Catching 'BaseException' Directly",
                            technical_description="Catching 'BaseException' intercepts system exit signals and interrupts.",
                            beginner_explanation=(
                                "In Python, `BaseException` is the parent of both regular errors and system events (like stopping the program). "
                                "Catching it prevents normal process termination."
                            ),
                            suggested_fix="Catch `Exception` instead of `BaseException`.",
                            line_start=node.lineno,
                            line_end=getattr(node, "end_lineno", node.lineno),
                        )
                    )

                # 2. Silent pass: except ...: pass
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    findings.append(
                        AnalysisFinding(
                            rule_id="SILENT_EXCEPTION",
                            language="python",
                            severity="warning",
                            line_number=node.lineno,
                            column_number=getattr(node, "col_offset", None),
                            category=self.category,
                            title="Exception Silently Ignored ('pass')",
                            technical_description="An exception handler containing only 'pass' silently suppresses errors.",
                            beginner_explanation=(
                                "When an error occurs, your code quietly swallows it with `pass` without printing or logging anything. "
                                "If a real problem happens later, you will have no error message to explain why the program failed."
                            ),
                            suggested_fix="At least print or log the error (e.g. `print(f'Error occurred: {err}')`) or handle the fallback properly.",
                            line_start=node.lineno,
                            line_end=getattr(node, "end_lineno", node.lineno),
                        )
                    )

        return findings
