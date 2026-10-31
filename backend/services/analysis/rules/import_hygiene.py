"""Rule checking for import hygiene issues like wildcard imports and duplicate imports."""

import ast
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule


class ImportHygieneRule(BaseStaticRule):
    """Detects wildcard imports, duplicate imports, and unused imports."""

    @property
    def rule_id(self) -> str:
        return "IMPORT_HYGIENE"

    @property
    def category(self) -> str:
        return "imports"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            findings.extend(self._analyze_python(ast_tree))
        return findings

    def _analyze_python(self, tree: ast.AST) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        imported_names: dict[str, int] = {}

        for node in ast.walk(tree):
            # Check wildcard imports: from module import *
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        findings.append(
                            AnalysisFinding(
                                rule_id="WILDCARD_IMPORT",
                                language="python",
                                severity="warning",
                                line_number=node.lineno,
                                column_number=getattr(node, "col_offset", None),
                                category=self.category,
                                title=f"Wildcard import 'from {node.module or ''} import *'",
                                technical_description="Wildcard imports pollute the namespace and make static analysis difficult.",
                                beginner_explanation=(
                                    f"Using `from {node.module or ''} import *` brings every single variable and function from that library "
                                    "directly into your code. It becomes impossible to tell where functions come from, and can accidentally "
                                    "overwrite your own variables."
                                ),
                                suggested_fix=f"Explicitly import only what you need, e.g. `from {node.module or 'module'} import specific_function`.",
                                line_start=node.lineno,
                                line_end=getattr(node, "end_lineno", node.lineno),
                            )
                        )
                    else:
                        name_key = alias.asname or alias.name
                        if name_key in imported_names:
                            findings.append(
                                AnalysisFinding(
                                    rule_id="DUPLICATE_IMPORT",
                                    language="python",
                                    severity="info",
                                    line_number=node.lineno,
                                    column_number=getattr(node, "col_offset", None),
                                    category=self.category,
                                    title=f"Duplicate import of '{name_key}'",
                                    technical_description=f"'{name_key}' was already imported on line {imported_names[name_key]}.",
                                    beginner_explanation=(
                                        f"You have already imported `{name_key}` earlier in the file (line {imported_names[name_key]}). "
                                        "Importing it again is unnecessary."
                                    ),
                                    suggested_fix="Remove the duplicate import line.",
                                    line_start=node.lineno,
                                    line_end=getattr(node, "end_lineno", node.lineno),
                                )
                            )
                        else:
                            imported_names[name_key] = node.lineno

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name_key = alias.asname or alias.name
                    if name_key in imported_names:
                        findings.append(
                            AnalysisFinding(
                                rule_id="DUPLICATE_IMPORT",
                                language="python",
                                severity="info",
                                line_number=node.lineno,
                                column_number=getattr(node, "col_offset", None),
                                category=self.category,
                                title=f"Duplicate import of '{name_key}'",
                                technical_description=f"'{name_key}' was already imported on line {imported_names[name_key]}.",
                                beginner_explanation=(
                                    f"Module `{name_key}` is imported more than once in this file. "
                                    "You only need to import each library once, usually at the very top of the file."
                                ),
                                suggested_fix="Remove the duplicate import line.",
                                line_start=node.lineno,
                                line_end=getattr(node, "end_lineno", node.lineno),
                            )
                        )
                    else:
                        imported_names[name_key] = node.lineno

        return findings
