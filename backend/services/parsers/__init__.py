from backend.services.parsers.base import BaseCodeParser
from backend.services.parsers.python_parser import PythonCodeParser
from backend.services.parsers.javascript_parser import JavaScriptCodeParser


def get_parser(language: str) -> BaseCodeParser:
    """Factory function returning the corresponding parser instance."""
    lang = language.lower()
    if lang == "python":
        return PythonCodeParser()
    elif lang in ("javascript", "js"):
        return JavaScriptCodeParser()
    else:
        raise ValueError(f"Unsupported language: {language}. Supported: python, javascript")


__all__ = ["BaseCodeParser", "PythonCodeParser", "JavaScriptCodeParser", "get_parser"]
