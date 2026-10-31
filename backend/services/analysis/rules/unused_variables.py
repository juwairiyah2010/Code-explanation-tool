"""Rule checking for variables and imports defined or assigned but never subsequently referenced."""

import ast
import re
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule


class UnusedVariablesRule(BaseStaticRule):
    """Detects local variables assigned but never referenced in subsequent statements."""

    @property
    def rule_id(self) -> str:
        return "UNUSED_VARIABLE"

    @property
    def category(self) -> str:
        return "unused code"

    def analyze(
        self, code: str, language: str, ast_tree: Any, raw_constructs: Any
    ) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            findings.extend(self._analyze_python(ast_tree))
        elif language == "javascript":
            findings.extend(self._analyze_javascript(code, ast_tree, raw_constructs))
        return findings

    def _analyze_python(self, tree: ast.AST) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []

        # Analyze each function scope
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assigned_vars: dict[str, tuple[int, int | None]] = {}
                loaded_vars: set[str] = set()

                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Name):
                        name = subnode.id
                        # Ignore standard dummy / ignored variables and builtins
                        if name.startswith("_") or name in ("self", "cls"):
                            continue

                        if isinstance(subnode.ctx, ast.Store):
                            if name not in assigned_vars:
                                col = getattr(subnode, "col_offset", None)
                                assigned_vars[name] = (subnode.lineno, col)
                        elif isinstance(subnode.ctx, ast.Load):
                            loaded_vars.add(name)

                # Check which assigned variables were never loaded
                for var_name, (lineno, col) in assigned_vars.items():
                    params = [a.arg for a in node.args.args]
                    if var_name not in loaded_vars and var_name not in params:
                        tech_desc = f"Variable '{var_name}' is assigned on line {lineno} but never used."
                        beginner_exp = (
                            f"You created a box named '{var_name}' and stored something inside it, "
                            f"but your program never reads from this box again. Leaving unused variables "
                            f"clutters your code and can confuse someone trying to read it."
                        )
                        suggested_fix = (
                            f"Remove '{var_name}' if it is not needed, or prefix with '_' "
                            f"(e.g. '_{var_name}') if you intentionally want to ignore it."
                        )
                        findings.append(
                            AnalysisFinding(
                                rule_id=self.rule_id,
                                language="python",
                                severity="warning",
                                line_number=lineno,
                                column_number=col,
                                category="unused code",
                                title="Unused Variable Assignment",
                                technical_description=tech_desc,
                                beginner_explanation=beginner_exp,
                                suggested_fix=suggested_fix,
                                line_start=lineno,
                                line_end=lineno,
                                message=tech_desc,
                                suggestion=suggested_fix,
                            )
                        )

        return findings

    def _analyze_javascript(
        self, code: str, ast_tree: Any, raw_constructs: Any
    ) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        lines = code.splitlines()

        if raw_constructs and hasattr(raw_constructs, "assignments"):
            for assign in raw_constructs.assignments:
                for target in assign.targets:
                    if target.startswith("_") or target in ("this", "window", "global"):
                        continue
                    line_idx = assign.line_start - 1
                    subsequent_code = (
                        "\n".join(lines[line_idx + 1 :]) if line_idx + 1 < len(lines) else ""
                    )
                    pattern = rf"\b{re.escape(target)}\b"
                    if not re.search(pattern, subsequent_code):
                        tech_desc = f"Variable '{target}' is declared on line {assign.line_start} but never referenced afterwards."
                        beginner_exp = (
                            f"Variable '{target}' was declared but never read. "
                            f"Unused variables waste memory and make code harder to read."
                        )
                        suggested_fix = f"Remove '{target}' or prefix with '_' if intentionally ignored."
                        findings.append(
                            AnalysisFinding(
                                rule_id=self.rule_id,
                                language="javascript",
                                severity="warning",
                                line_number=assign.line_start,
                                column_number=None,
                                category="unused code",
                                title="Unused Variable Declaration",
                                technical_description=tech_desc,
                                beginner_explanation=beginner_exp,
                                suggested_fix=suggested_fix,
                                line_start=assign.line_start,
                                line_end=assign.line_end,
                                message=tech_desc,
                                suggestion=suggested_fix,
                            )
                        )

        return findings
