"""Rule checking for variable usage anomalies like shadowed built-ins and loop variable modification."""

import ast
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule

COMMON_BUILTINS = {
    "list", "dict", "str", "int", "float", "set", "tuple", "bool",
    "type", "id", "sum", "max", "min", "input", "open", "map",
    "filter", "range", "len", "format", "dir", "hash", "any", "all",
}


class VariableUsageRule(BaseStaticRule):
    """Detects problematic variable naming and modification patterns."""

    @property
    def rule_id(self) -> str:
        return "VARIABLE_USAGE"

    @property
    def category(self) -> str:
        return "variable usage"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            findings.extend(self._analyze_python(ast_tree))
        return findings

    def _analyze_python(self, tree: ast.AST) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []

        for node in ast.walk(tree):
            # Check function arguments for shadowed builtins
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args:
                    if arg.arg in COMMON_BUILTINS:
                        findings.append(
                            AnalysisFinding(
                                rule_id="SHADOWED_BUILTIN",
                                language="python",
                                severity="warning",
                                line_number=arg.lineno,
                                column_number=getattr(arg, "col_offset", None),
                                category=self.category,
                                title=f"Parameter '{arg.arg}' shadows Python built-in",
                                technical_description=f"Function argument '{arg.arg}' overrides Python's built-in symbol '{arg.arg}'.",
                                beginner_explanation=(
                                    f"In Python, `{arg.arg}` is already a built-in standard tool. Naming your parameter `{arg.arg}` "
                                    f"overwrites it inside this function. If you try to use the real `{arg.arg}()` function later, "
                                    "Python will get confused and might give you a 'TypeError'."
                                ),
                                suggested_fix=f"Rename parameter `{arg.arg}` to something more descriptive (e.g., `{arg.arg}_val` or `items`).",
                                line_start=arg.lineno,
                                line_end=arg.lineno,
                            )
                        )

            # Check variable assignments for shadowed builtins & self-assignment
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id in COMMON_BUILTINS:
                            findings.append(
                                AnalysisFinding(
                                    rule_id="SHADOWED_BUILTIN",
                                    language="python",
                                    severity="warning",
                                    line_number=target.lineno,
                                    column_number=getattr(target, "col_offset", None),
                                    category=self.category,
                                    title=f"Variable '{target.id}' shadows Python built-in",
                                    technical_description=f"Assignment to '{target.id}' overrides Python's built-in '{target.id}'.",
                                    beginner_explanation=(
                                        f"`{target.id}` is a reserved built-in function or type in Python. If you assign a variable "
                                        f"named `{target.id} = ...`, you won't be able to call the original `{target.id}()` function in this scope."
                                    ),
                                    suggested_fix=f"Rename variable `{target.id}` to something descriptive, e.g. `{target.id}_list` or `data`.",
                                    line_start=target.lineno,
                                    line_end=target.lineno,
                                )
                            )
                        # Check self-assignment: x = x
                        if isinstance(node.value, ast.Name) and node.value.id == target.id:
                            findings.append(
                                AnalysisFinding(
                                    rule_id="SELF_ASSIGNMENT",
                                    language="python",
                                    severity="info",
                                    line_number=target.lineno,
                                    column_number=getattr(target, "col_offset", None),
                                    category=self.category,
                                    title=f"Redundant self-assignment '{target.id} = {target.id}'",
                                    technical_description=f"Variable '{target.id}' is being assigned to itself.",
                                    beginner_explanation=(
                                        f"Assigning a variable to itself (`{target.id} = {target.id}`) does nothing and has no effect."
                                    ),
                                    suggested_fix="Remove this line or check if you intended to assign a different value.",
                                    line_start=target.lineno,
                                    line_end=target.lineno,
                                )
                            )

            # Check modifying loop variable inside for-loop
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                loop_var = node.target.id
                for child in node.body:
                    for sub in ast.walk(child):
                        if isinstance(sub, ast.Assign):
                            for t in sub.targets:
                                if isinstance(t, ast.Name) and t.id == loop_var:
                                    findings.append(
                                        AnalysisFinding(
                                            rule_id="MODIFIED_LOOP_VARIABLE",
                                            language="python",
                                            severity="info",
                                            line_number=t.lineno,
                                            column_number=getattr(t, "col_offset", None),
                                            category=self.category,
                                            title=f"Loop variable '{loop_var}' modified inside loop",
                                            technical_description=f"Target '{loop_var}' of for-loop is reassigned within the loop body.",
                                            beginner_explanation=(
                                                f"In Python, changing `{loop_var}` inside the loop will not skip items or alter the next iteration. "
                                                f"On the next round, `{loop_var}` will simply be overwritten with the next value in the sequence."
                                            ),
                                            suggested_fix="If you need custom stepping, use a `while` loop or store the modified value in a new variable.",
                                            line_start=t.lineno,
                                            line_end=t.lineno,
                                        )
                                    )
                                    break

        return findings
