"""Language detection using file extensions and syntax-based heuristic fallback."""

import os
import re
from typing import Any, Literal

Language = Literal["python", "javascript", "unknown"]
DetectionMethod = Literal["filename", "syntax_heuristic", "explicit"]


class LanguageDetectionResult:
    def __init__(self, language: Language, method: DetectionMethod, confidence: float):
        self.language = language
        self.method = method
        self.confidence = confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "method": self.method,
            "confidence": self.confidence,
        }


# File extension mappings
EXTENSION_MAP: dict[str, Language] = {
    ".py": "python",
    ".pyw": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
}


def detect_language(code: str, filename: str | None = None, explicit_language: str | None = None) -> LanguageDetectionResult:
    """Detect code language using filename extension, explicit request, or syntax fallback."""
    # 1. Explicit valid language
    if explicit_language and explicit_language.lower() in ("python", "py"):
        return LanguageDetectionResult("python", "explicit", 1.0)
    elif explicit_language and explicit_language.lower() in ("javascript", "js", "typescript", "ts"):
        return LanguageDetectionResult("javascript", "explicit", 1.0)

    # 2. Filename extension detection
    if filename:
        _, ext = os.path.splitext(filename.lower())
        if ext in EXTENSION_MAP:
            return LanguageDetectionResult(EXTENSION_MAP[ext], "filename", 0.95)

    # 3. Syntax-based heuristic detection
    return detect_by_syntax(code)


def detect_by_syntax(code: str) -> LanguageDetectionResult:
    """Score code patterns to detect Python vs JavaScript."""
    if not code or not code.strip():
        return LanguageDetectionResult("unknown", "syntax_heuristic", 0.0)

    py_score = 0
    js_score = 0

    # Strong Python indicators
    if re.search(r"^\s*def\s+[a-zA-Z0-9_]+\s*\(.*?\)\s*:", code, re.MULTILINE):
        py_score += 5
    if re.search(r"^\s*class\s+[a-zA-Z0-9_]+(?:\(.*?\))?\s*:", code, re.MULTILINE):
        py_score += 4
    if re.search(r"^\s*(?:import\s+[a-zA-Z0-9_.]+|from\s+[a-zA-Z0-9_.]+\s+import)", code, re.MULTILINE):
        py_score += 4
    if re.search(r"\b(?:elif|True|False|None|self|__init__|pass|lambda|async def)\b", code):
        py_score += 3
    if re.search(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', code):
        py_score += 2
    if re.search(r":\s*$", code, re.MULTILINE):
        py_score += 2

    # Strong JavaScript indicators
    if re.search(r"\b(?:function\s+[a-zA-Z0-9_$]+|function\s*\(|=>)", code):
        js_score += 5
    if re.search(r"\b(?:const|let|var)\s+[a-zA-Z0-9_$]+\s*=", code):
        js_score += 5
    if re.search(r"\bconsole\.(?:log|warn|error|info)\b", code):
        js_score += 4
    if re.search(r"\b(?:===|!==|typeof|instanceof|null|undefined|require\(|module\.exports|export\s+default)\b", code):
        js_score += 4
    if re.search(r"[{};]\s*$", code, re.MULTILINE):
        js_score += 3
    if re.search(r"\bclass\s+[a-zA-Z0-9_$]+(?:\s+extends\s+[a-zA-Z0-9_$]+)?\s*\{", code):
        js_score += 4

    total = py_score + js_score
    if total == 0:
        # Default fallback: try python ast
        import ast
        try:
            ast.parse(code)
            return LanguageDetectionResult("python", "syntax_heuristic", 0.6)
        except Exception:
            return LanguageDetectionResult("javascript", "syntax_heuristic", 0.5)

    if py_score > js_score:
        confidence = round(py_score / max(1, total), 2)
        return LanguageDetectionResult("python", "syntax_heuristic", confidence)
    elif js_score > py_score:
        confidence = round(js_score / max(1, total), 2)
        return LanguageDetectionResult("javascript", "syntax_heuristic", confidence)
    else:
        # Tie breaker - try Python AST
        import ast
        try:
            ast.parse(code)
            return LanguageDetectionResult("python", "syntax_heuristic", 0.6)
        except Exception:
            return LanguageDetectionResult("javascript", "syntax_heuristic", 0.6)
