"""Rule checking for security vulnerabilities like eval/exec and hardcoded secrets."""

import ast
from typing import Any
from backend.schemas.explanation import AnalysisFinding
from backend.services.analysis.rules.base_rule import BaseStaticRule

SECRET_KEYWORDS = {"password", "secret", "secret_key", "api_key", "auth_token", "private_key"}


class SecurityRule(BaseStaticRule):
    """Detects security vulnerabilities and risky language constructs."""

    @property
    def rule_id(self) -> str:
        return "SECURITY_ISSUE"

    @property
    def category(self) -> str:
        return "security"

    def analyze(self, code: str, language: str, ast_tree: Any, raw_constructs: Any) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        if language == "python" and isinstance(ast_tree, ast.AST):
            findings.extend(self._analyze_python(ast_tree))
        return findings

    def _analyze_python(self, tree: ast.AST) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []

        for node in ast.walk(tree):
            # 1. Dangerous eval/exec calls
            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id

                if func_name in ("eval", "exec"):
                    findings.append(
                        AnalysisFinding(
                            rule_id=f"DANGEROUS_{func_name.upper()}",
                            language="python",
                            severity="error",
                            line_number=node.lineno,
                            column_number=getattr(node, "col_offset", None),
                            category=self.category,
                            title=f"Dangerous use of '{func_name}()'",
                            technical_description=f"Direct invocation of '{func_name}()' allows arbitrary dynamic code execution.",
                            beginner_explanation=(
                                f"`{func_name}()` runs any arbitrary text as raw Python code. If any untrusted input is passed to it, "
                                "an attacker can read files, delete data, or take over your computer."
                            ),
                            suggested_fix="Avoid dynamic execution. If parsing numbers or data structures, use `ast.literal_eval()` or `json.loads()`.",
                            line_start=node.lineno,
                            line_end=getattr(node, "end_lineno", node.lineno),
                        )
                    )

            # 2. Insecure assert statements in functions
            if isinstance(node, ast.Assert):
                findings.append(
                    AnalysisFinding(
                        rule_id="INSECURE_ASSERT",
                        language="python",
                        severity="info",
                        line_number=node.lineno,
                        column_number=getattr(node, "col_offset", None),
                        category=self.category,
                        title="Use of 'assert' for validation",
                        technical_description="Assert statements are completely removed when Python runs with optimization flags (-O or -OO).",
                        beginner_explanation=(
                            "`assert` is meant only for internal debugging during testing. When Python runs in production with `-O` mode, "
                            "all `assert` statements are silently ignored! Never use `assert` to validate user input or check permissions."
                        ),
                        suggested_fix="Use an `if not condition: raise ValueError(...)` statement instead of `assert`.",
                        line_start=node.lineno,
                        line_end=getattr(node, "end_lineno", node.lineno),
                    )
                )

            # 3. Hardcoded secrets / credentials
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name_lower = target.id.lower()
                        if any(k in name_lower for k in SECRET_KEYWORDS):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                val = node.value.value
                                if len(val) >= 8 and not val.startswith("your_") and val not in ("test", "example", "dummy"):
                                    findings.append(
                                        AnalysisFinding(
                                            rule_id="HARDCODED_SECRET",
                                            language="python",
                                            severity="warning",
                                            line_number=target.lineno,
                                            column_number=getattr(target, "col_offset", None),
                                            category=self.category,
                                            title=f"Potential Hardcoded Secret in '{target.id}'",
                                            technical_description=f"Variable '{target.id}' appears to contain a hardcoded credential or secret string.",
                                            beginner_explanation=(
                                                "Storing secrets, passwords, or API keys directly in source code is dangerous because "
                                                "anyone who views the code (or git history) can see your private keys."
                                            ),
                                            suggested_fix="Use environment variables: `os.getenv('KEY_NAME')` instead of writing secrets in code.",
                                            line_start=target.lineno,
                                            line_end=getattr(node, "end_lineno", target.lineno),
                                        )
                                    )

        return findings
