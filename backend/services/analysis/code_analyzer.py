"""Normalized Static Code Analysis Engine.

Provides deterministic, beginner-friendly static analysis with structured findings,
code quality metrics, and multi-language support (Python primary, JavaScript preserved).
"""

import ast
import re
from typing import Any

from backend.schemas.explanation import (
    ASTNodeInfo,
    AnalysisFinding,
    AnalysisResult,
    CodeConstructs,
    SyntaxErrorInfo,
)
from backend.services.analysis.static_analyzer import StaticAnalyzer
# Try importing radon for complexity and raw metrics
try:
    import radon.complexity as radon_cc
    import radon.raw as radon_raw
    RADON_AVAILABLE = True
except Exception:
    RADON_AVAILABLE = False

# Try importing pyflakes for AST validation
try:
    import pyflakes.checker as pyflakes_checker
    PYFLAKES_AVAILABLE = True
except Exception:
    PYFLAKES_AVAILABLE = False


from collections import OrderedDict
import hashlib
import threading

class AnalysisCache:
    """Thread-safe LRU cache for deterministic AST analysis results."""

    def __init__(self, maxsize: int = 1024):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, AnalysisResult] = OrderedDict()
        self._lock = threading.Lock()

    def make_key(self, code: str, language: str, filename: str | None) -> str:
        content = f"{language}::{filename or ''}::{code}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get(self, code: str, language: str, filename: str | None) -> AnalysisResult | None:
        key = self.make_key(code, language, filename)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def put(self, code: str, language: str, filename: str | None, result: AnalysisResult) -> None:
        key = self.make_key(code, language, filename)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.maxsize:
                    self._cache.popitem(last=False)
                self._cache[key] = result

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)


class CodeAnalyzer:
    """Core static code analysis service providing beginner-friendly normalized findings."""

    def __init__(self, static_analyzer: StaticAnalyzer | None = None) -> None:
        self.static_analyzer = static_analyzer or StaticAnalyzer()
        self._python_parser = None
        self._js_parser = None
        self.cache = AnalysisCache()

    @property
    def python_parser(self):
        if self._python_parser is None:
            from backend.services.parsers.python_parser import PythonCodeParser
            self._python_parser = PythonCodeParser()
        return self._python_parser

    @property
    def js_parser(self):
        if self._js_parser is None:
            from backend.services.parsers.javascript_parser import JavaScriptCodeParser
            self._js_parser = JavaScriptCodeParser()
        return self._js_parser

    def analyze(
        self,
        code: str,
        language: str = "auto",
        filename: str | None = None,
        use_cache: bool = True,
    ) -> AnalysisResult:
        """Run deterministic static analysis on code and return normalized AnalysisResult."""
        if use_cache:
            cached = self.cache.get(code, language, filename)
            if cached is not None:
                return cached

        resolved_language, detection_method = self._resolve_language(code, language, filename)

        if resolved_language == "javascript":
            result = self._analyze_javascript(code, detection_method)
        else:
            result = self._analyze_python(code, detection_method)

        if use_cache:
            self.cache.put(code, language, filename, result)
        return result

    def _resolve_language(
        self,
        code: str,
        language: str,
        filename: str | None,
    ) -> tuple[str, str]:
        """Detect language using explicit parameter, filename extension, or syntactic heuristics."""
        lang_clean = (language or "auto").lower().strip()
        if lang_clean in ("python", "py"):
            return "python", "explicit"
        if lang_clean in ("javascript", "js", "typescript", "ts"):
            return "javascript", "explicit"

        # Check filename extension
        if filename:
            fn_lower = filename.lower()
            if fn_lower.endswith((".py", ".pyw")):
                return "python", "filename"
            if fn_lower.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
                return "javascript", "filename"

        # Heuristic detection
        js_indicators = [
            r"\bfunction\s+[a-zA-Z_]",
            r"\bconst\s+[a-zA-Z_]",
            r"\blet\s+[a-zA-Z_]",
            r"\bvar\s+[a-zA-Z_]",
            r"console\.log\(",
            r"=>",
            r"\bdocument\.",
            r"\bwindow\.",
        ]
        py_indicators = [
            r"\bdef\s+[a-zA-Z_]",
            r"\belif\s+",
            r"\bimport\s+[a-zA-Z_]",
            r"\bfrom\s+[a-zA-Z_]+\s+import",
            r"print\(",
            r":\s*$",
            r"\bself\b",
        ]

        js_score = sum(1 for p in js_indicators if re.search(p, code, re.MULTILINE))
        py_score = sum(1 for p in py_indicators if re.search(p, code, re.MULTILINE))

        if js_score > py_score:
            return "javascript", "syntax_heuristic"
        return "python", "syntax_heuristic"

    def _analyze_python(self, code: str, detection_method: str) -> AnalysisResult:
        """Execute comprehensive Python static analysis."""
        lines = code.splitlines()
        total_lines = len(lines)

        # 1. Calculate raw line metrics
        loc_metrics = self._calculate_python_loc(code, lines)

        # 2. Syntax check via AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # Produce structured beginner-friendly syntax finding
            error_finding = self._build_syntax_error_finding(e)
            syntax_err = SyntaxErrorInfo(
                line=e.lineno or 1,
                column=e.offset or 1,
                message=e.msg or "Syntax error",
            )
            return AnalysisResult(
                language="python",
                detection_method=detection_method,
                is_valid_syntax=False,
                syntax_error=f"Line {e.lineno}, Col {e.offset}: {e.msg}",
                syntax_errors=[syntax_err],
                blocks=[],
                constructs=CodeConstructs(),
                static_hints=[error_finding],
                findings=[error_finding],
                complexity_score=1,
                cyclomatic_complexity=1,
                max_nesting_depth=0,
                maximum_nesting_depth=0,
                function_count=0,
                class_count=0,
                import_count=0,
                lines_of_code=loc_metrics,
                duplicate_patterns=[],
                metrics={"total_lines": total_lines, "error_line": e.lineno},
                summary=f"Syntax error at line {e.lineno}: {error_finding.beginner_explanation}",
                functions=[],
                classes=[],
                imports=[],
            )

        # 3. Extract AST constructs and nesting
        from backend.services.parsers.python_parser import PythonComprehensiveASTVisitor
        visitor = PythonComprehensiveASTVisitor()
        visitor.visit(tree)

        constructs = CodeConstructs(
            functions=visitor.functions,
            classes=visitor.classes,
            loops=visitor.loops,
            conditions=visitor.conditions,
            assignments=visitor.assignments,
            imports=visitor.imports,
            calls=visitor.calls,
        )

        # 4. Calculate cyclomatic complexity (using radon if available, fallback to visitor)
        cyclomatic_complexity = self._calculate_python_complexity(code, visitor.complexity_score)

        # 5. Detect repeated/duplicate patterns
        duplicate_patterns = self._detect_duplicate_patterns(tree, lines)

        # 6. Run all rule modules through static analyzer
        rule_findings = self.static_analyzer.run_rules(code, "python", tree, constructs)

        # 7. Run pyflakes for undefined names and unused imports
        pyflakes_findings = self._run_pyflakes(tree)

        # Merge findings and deduplicate
        all_findings = self._merge_findings(rule_findings, pyflakes_findings)

        # 8. Split syntax blocks
        blocks = self.static_analyzer.split_syntax_blocks(code, constructs)

        # 9. Build metrics dictionary
        metrics: dict[str, Any] = {
            "total_lines": loc_metrics["total"],
            "code_lines": loc_metrics["code"],
            "blank_lines": loc_metrics["blank"],
            "comment_lines": loc_metrics["comment"],
            "cyclomatic_complexity": cyclomatic_complexity,
            "max_nesting_depth": visitor.max_nesting_depth,
            "num_functions": len(visitor.functions),
            "num_classes": len(visitor.classes),
            "num_loops": len(visitor.loops),
            "num_conditions": len(visitor.conditions),
            "num_assignments": len(visitor.assignments),
            "num_imports": len(visitor.imports),
            "num_calls": len(visitor.calls),
            "num_blocks": len(blocks),
            "num_findings": len(all_findings),
            "num_duplicate_patterns": len(duplicate_patterns),
        }

        # 10. Summary description
        summary = self._generate_summary("python", loc_metrics["total"], all_findings, cyclomatic_complexity)

        legacy_functions = [
            ASTNodeInfo(
                name=f.name,
                node_type="AsyncFunctionDef" if f.is_async else "FunctionDef",
                line_start=f.line_start,
                line_end=f.line_end,
                docstring=f.docstring,
                parameters=f.parameters,
            )
            for f in visitor.functions
        ]
        legacy_classes = [
            ASTNodeInfo(
                name=c.name,
                node_type="ClassDef",
                line_start=c.line_start,
                line_end=c.line_end,
                docstring=c.docstring,
                parameters=[],
            )
            for c in visitor.classes
        ]

        return AnalysisResult(
            language="python",
            detection_method=detection_method,
            is_valid_syntax=True,
            syntax_error=None,
            syntax_errors=[],
            blocks=blocks,
            constructs=constructs,
            static_hints=all_findings,
            findings=all_findings,
            complexity_score=cyclomatic_complexity,
            cyclomatic_complexity=cyclomatic_complexity,
            max_nesting_depth=visitor.max_nesting_depth,
            maximum_nesting_depth=visitor.max_nesting_depth,
            function_count=len(visitor.functions),
            class_count=len(visitor.classes),
            import_count=len(visitor.imports),
            lines_of_code=loc_metrics,
            duplicate_patterns=duplicate_patterns,
            metrics=metrics,
            summary=summary,
            functions=legacy_functions,
            classes=legacy_classes,
            imports=[imp.module for imp in visitor.imports],
        )

    def _analyze_javascript(self, code: str, detection_method: str) -> AnalysisResult:
        """Execute JavaScript static analysis using Tree-sitter / JavaScript parser."""
        resp = self.js_parser.parse(code, detection_method=detection_method)

        lines = code.splitlines()
        loc_metrics = {
            "total": len(lines),
            "code": max(0, len(lines) - resp.metrics.get("blank_lines", 0) - resp.metrics.get("comment_lines", 0)),
            "blank": resp.metrics.get("blank_lines", 0),
            "comment": resp.metrics.get("comment_lines", 0),
        }

        # Extract duplicate patterns in JS
        duplicate_patterns = self._detect_js_duplicate_lines(lines)

        findings = resp.static_hints
        summary = self._generate_summary("javascript", loc_metrics["total"], findings, resp.complexity_score)

        return AnalysisResult(
            language="javascript",
            detection_method=detection_method,
            is_valid_syntax=resp.is_valid_syntax,
            syntax_error=resp.syntax_error,
            syntax_errors=resp.syntax_errors,
            blocks=resp.blocks,
            constructs=resp.constructs,
            static_hints=findings,
            findings=findings,
            complexity_score=resp.complexity_score,
            cyclomatic_complexity=resp.complexity_score,
            max_nesting_depth=resp.max_nesting_depth,
            maximum_nesting_depth=resp.max_nesting_depth,
            function_count=len(resp.constructs.functions),
            class_count=len(resp.constructs.classes),
            import_count=len(resp.constructs.imports),
            lines_of_code=loc_metrics,
            duplicate_patterns=duplicate_patterns,
            metrics=resp.metrics,
            summary=summary,
            functions=resp.functions,
            classes=resp.classes,
            imports=resp.imports,
        )

    def _calculate_python_loc(self, code: str, lines: list[str]) -> dict[str, int]:
        """Calculate line metrics: total, code, comment, blank."""
        if RADON_AVAILABLE:
            try:
                raw = radon_raw.analyze(code)
                return {
                    "total": raw.loc,
                    "code": raw.sloc,
                    "comment": raw.comments + raw.single_comments,
                    "blank": raw.blank,
                }
            except Exception:
                pass

        total = len(lines)
        blank = sum(1 for line in lines if not line.strip())
        comment = sum(1 for line in lines if line.strip().startswith("#"))
        return {
            "total": total,
            "code": max(0, total - blank - comment),
            "blank": blank,
            "comment": comment,
        }

    def _calculate_python_complexity(self, code: str, fallback_score: int) -> int:
        """Calculate cyclomatic complexity score using Radon if available."""
        if RADON_AVAILABLE:
            try:
                blocks = radon_cc.cc_visit(code)
                if blocks:
                    return sum(b.complexity for b in blocks)
            except Exception:
                pass
        return fallback_score

    def _build_syntax_error_finding(self, exc: SyntaxError) -> AnalysisFinding:
        """Construct beginner-friendly finding for a syntax error."""
        lineno = exc.lineno or 1
        offset = exc.offset or 1
        msg = exc.msg or "Invalid syntax"

        # Beginner explanation mapping
        msg_low = msg.lower()
        if "expected ':'" in msg_low:
            beg_exp = "In Python, header statements like `def`, `if`, `for`, `while`, and `class` must end with a colon `:`."
            fix = "Add a colon `:` at the end of the line."
        elif "was never closed" in msg_low or "unmatched" in msg_low:
            beg_exp = "A parenthesis `(`, bracket `[`, or quotation mark `'` was opened but never closed."
            fix = "Add the matching closing parenthesis, bracket, or quote."
        elif "indent" in msg_low:
            beg_exp = "Python relies on 4-space indentation to define blocks of code. This line's indentation does not match the surrounding block."
            fix = "Adjust the indentation (spaces) to match the surrounding block."
        else:
            beg_exp = f"Python encountered a syntax issue it could not understand: '{msg}'. Check for typos or missing punctuation."
            fix = "Review the syntax around this line for missing colons, quotes, or keywords."

        return AnalysisFinding(
            rule_id="SYNTAX_ERROR",
            language="python",
            severity="error",
            line_number=lineno,
            column_number=offset,
            category="syntax",
            title=f"Syntax Error: {msg}",
            technical_description=f"Python parser failed at line {lineno}, column {offset}: {msg}",
            beginner_explanation=beg_exp,
            suggested_fix=fix,
            line_start=lineno,
            line_end=lineno,
        )

    def _detect_duplicate_patterns(self, tree: ast.AST, lines: list[str]) -> list[dict[str, Any]]:
        """Detect simple repeated patterns such as duplicate statements or consecutive calls."""
        duplicates: list[dict[str, Any]] = []

        # 1. Look for identical consecutive statements in blocks
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and len(body) >= 2:
                for i in range(len(body) - 1):
                    s1 = body[i]
                    s2 = body[i + 1]
                    # Skip pass, docstrings, or simple constants
                    if isinstance(s1, (ast.Pass, ast.Expr)) and isinstance(getattr(s1, "value", None), ast.Constant):
                        continue
                    try:
                        d1 = ast.dump(s1)
                        d2 = ast.dump(s2)
                        if d1 == d2 and s1.lineno != s2.lineno:
                            code_snippet = lines[s1.lineno - 1].strip() if s1.lineno <= len(lines) else ""
                            duplicates.append({
                                "pattern_type": "consecutive_duplicate_statement",
                                "line_start": s1.lineno,
                                "line_end": s2.lineno,
                                "snippet": code_snippet,
                                "description": f"Consecutive duplicate statement detected on lines {s1.lineno} and {s2.lineno}.",
                            })
                    except Exception:
                        continue

        # 2. Look for identical non-trivial code lines appearing 3+ times
        line_counts: dict[str, list[int]] = {}
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            # Ignore trivial lines like pass, return, closing brackets, empty
            if len(stripped) > 10 and not stripped.startswith("#") and stripped not in ("return None", "pass"):
                line_counts.setdefault(stripped, []).append(idx)

        for snippet, line_nums in line_counts.items():
            if len(line_nums) >= 3:
                duplicates.append({
                    "pattern_type": "repeated_code_pattern",
                    "line_start": line_nums[0],
                    "line_end": line_nums[-1],
                    "occurrences": len(line_nums),
                    "lines": line_nums,
                    "snippet": snippet,
                    "description": f"Line '{snippet[:40]}...' appears {len(line_nums)} times. Consider extracting to a function or loop.",
                })

        return duplicates

    def _detect_js_duplicate_lines(self, lines: list[str]) -> list[dict[str, Any]]:
        """Detect simple repeated lines in JavaScript."""
        duplicates: list[dict[str, Any]] = []
        line_counts: dict[str, list[int]] = {}
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if len(stripped) > 10 and not stripped.startswith("//") and stripped not in ("}", "break;", "return;"):
                line_counts.setdefault(stripped, []).append(idx)

        for snippet, line_nums in line_counts.items():
            if len(line_nums) >= 3:
                duplicates.append({
                    "pattern_type": "repeated_code_pattern",
                    "line_start": line_nums[0],
                    "line_end": line_nums[-1],
                    "occurrences": len(line_nums),
                    "lines": line_nums,
                    "snippet": snippet,
                    "description": f"Code pattern '{snippet[:40]}...' is repeated {len(line_nums)} times.",
                })
        return duplicates

    def _run_pyflakes(self, tree: ast.AST) -> list[AnalysisFinding]:
        """Run pyflakes checker to detect undefined variables and unused imports."""
        findings: list[AnalysisFinding] = []
        if not PYFLAKES_AVAILABLE:
            return findings

        try:
            checker = pyflakes_checker.Checker(tree)
            for msg in checker.messages:
                msg_type = type(msg).__name__
                line = msg.lineno
                col = getattr(msg, "col", None)

                if msg_type == "UndefinedName":
                    var_name = msg.message_args[0] if msg.message_args else "variable"
                    findings.append(
                        AnalysisFinding(
                            rule_id="UNDEFINED_VARIABLE",
                            language="python",
                            severity="error",
                            line_number=line,
                            column_number=col,
                            category="variable usage",
                            title=f"Undefined variable '{var_name}'",
                            technical_description=f"Name '{var_name}' is used without being defined in the local or global scope.",
                            beginner_explanation=(
                                f"You are trying to use `{var_name}`, but Python has never heard of it yet. "
                                f"Make sure you created `{var_name} = ...` earlier, or check for spelling mistakes."
                            ),
                            suggested_fix=f"Define `{var_name}` before using it, or check the spelling.",
                            line_start=line,
                            line_end=line,
                        )
                    )
                elif msg_type == "UnusedImport":
                    mod_name = msg.message_args[0] if msg.message_args else "module"
                    findings.append(
                        AnalysisFinding(
                            rule_id="UNUSED_IMPORT",
                            language="python",
                            severity="info",
                            line_number=line,
                            column_number=col,
                            category="unused code",
                            title=f"Unused import '{mod_name}'",
                            technical_description=f"Imported symbol '{mod_name}' is never referenced in this module.",
                            beginner_explanation=(
                                f"You imported `{mod_name}`, but never used it anywhere in your code. "
                                "Removing unused imports keeps your code clean and loads faster."
                            ),
                            suggested_fix=f"Remove `import {mod_name}` if it is not needed.",
                            line_start=line,
                            line_end=line,
                        )
                    )
                elif msg_type == "DuplicateArgument":
                    arg_name = msg.message_args[0] if msg.message_args else "arg"
                    findings.append(
                        AnalysisFinding(
                            rule_id="DUPLICATE_ARGUMENT",
                            language="python",
                            severity="error",
                            line_number=line,
                            column_number=col,
                            category="syntax",
                            title=f"Duplicate argument '{arg_name}' in function definition",
                            technical_description=f"Function defines multiple arguments with the same name '{arg_name}'.",
                            beginner_explanation=(
                                f"The function lists `{arg_name}` twice in its parameter list. Each parameter must have a unique name."
                            ),
                            suggested_fix=f"Rename one of the `{arg_name}` parameters.",
                            line_start=line,
                            line_end=line,
                        )
                    )
        except Exception:
            pass

        return findings

    def _merge_findings(
        self,
        rule_findings: list[AnalysisFinding],
        pyflakes_findings: list[AnalysisFinding],
    ) -> list[AnalysisFinding]:
        """Merge findings while deduplicating by rule_id and line_number."""
        seen: set[tuple[str, int]] = set()
        merged: list[AnalysisFinding] = []

        for f in rule_findings:
            key = (f.rule_id, f.line_number)
            if key not in seen:
                seen.add(key)
                merged.append(f)

        for f in pyflakes_findings:
            key = (f.rule_id, f.line_number)
            if key not in seen:
                seen.add(key)
                merged.append(f)

        return sorted(merged, key=lambda x: (x.line_number, 0 if x.severity == "error" else 1))

    def _generate_summary(
        self,
        language: str,
        total_lines: int,
        findings: list[AnalysisFinding],
        complexity: int,
    ) -> str:
        """Create a human-friendly overview of the code analysis result."""
        errors = sum(1 for f in findings if f.severity == "error")
        warnings = sum(1 for f in findings if f.severity == "warning")
        infos = sum(1 for f in findings if f.severity == "info")

        categories = {f.category for f in findings}
        cat_str = f" across {len(categories)} categories ({', '.join(sorted(categories))})" if categories else ""

        if not findings:
            return f"Clean {language.capitalize()} code ({total_lines} lines, cyclomatic complexity {complexity}). No issues detected!"

        return (
            f"{language.capitalize()} analysis completed for {total_lines} lines (complexity: {complexity}). "
            f"Found {len(findings)} items{cat_str}: {errors} error(s), {warnings} warning(s), {infos} suggestion(s)."
        )
