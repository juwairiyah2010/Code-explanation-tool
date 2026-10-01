"""Rule checking for variables defined or assigned but never subsequently referenced."""

import ast
import re
from typing import Any
from backend.schemas.explanation import StaticHint
from backend.services.analysis.rules.base_rule import BaseStaticRule


class UnusedVariablesRule(BaseStaticRule):
    """Detects local variables assigned but never referenced in subsequent statements."""

    @property
    def rule_id(self) -> str:
        return "UNUSED_VARIABLE"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[StaticHint]:
        hints: list[StaticHint] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            hints.extend(self._analyze_python(ast_tree))
        elif language == "javascript":
            hints.extend(self._analyze_javascript(code, ast_tree, raw_constructs))
        return hints

    def _analyze_python(self, tree: ast.AST) -> list[StaticHint]:
        hints: list[StaticHint] = []

        # Analyze each function scope
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assigned_vars: dict[str, int] = {}
                loaded_vars: set[str] = set()

                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Name):
                        name = subnode.id
                        # Ignore standard dummy / ignored variables and builtins
                        if name.startswith("_") or name in ("self", "cls"):
                            continue

                        if isinstance(subnode.ctx, ast.Store):
                            if name not in assigned_vars:
                                assigned_vars[name] = subnode.lineno
                        elif isinstance(subnode.ctx, ast.Load):
                            loaded_vars.add(name)

                # Check which assigned variables were never loaded
                for var_name, lineno in assigned_vars.items():
                    # Exclude function parameters from strict assignment check
                    params = [a.arg for a in node.args.args]
                    if var_name not in loaded_vars and var_name not in params:
                        hints.append(
                            StaticHint(
                                rule_id=self.rule_id,
                                severity="warning",
                                message=f"Variable '{var_name}' is assigned on line {lineno} but never used.",
                                line_start=lineno,
                                line_end=lineno,
                                suggestion=f"Remove '{var_name}' or prefix with '_' (e.g. '_{var_name}') if intentionally unused.",
                            )
                        )

        return hints

    def _analyze_javascript(self, code: str, ast_tree: Any, raw_constructs: Any) -> list[StaticHint]:
        hints: list[StaticHint] = []
        lines = code.splitlines()

        # Check declared variables from constructs
        if raw_constructs and hasattr(raw_constructs, "assignments"):
            for assign in raw_constructs.assignments:
                for target in assign.targets:
                    if target.startswith("_") or target in ("this", "window", "global"):
                        continue
                    line_idx = assign.line_start - 1
                    # Look at rest of the file/function for usages
                    subsequent_code = "\n".join(lines[line_idx + 1 :]) if line_idx + 1 < len(lines) else ""
                    # Check if target is referenced as a whole identifier in subsequent lines
                    pattern = rf"\b{re.escape(target)}\b"
                    if not re.search(pattern, subsequent_code):
                        hints.append(
                            StaticHint(
                                rule_id=self.rule_id,
                                severity="warning",
                                message=f"Variable '{target}' is declared on line {assign.line_start} but never referenced afterwards.",
                                line_start=assign.line_start,
                                line_end=assign.line_end,
                                suggestion=f"Remove '{target}' or prefix with '_' if intentionally ignored.",
                            )
                        )

        return hints
