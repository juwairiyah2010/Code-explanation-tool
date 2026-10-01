"""Reusable HTTP client for the FastAPI backend."""

from typing import Any
import httpx
from backend.config import get_settings

settings = get_settings()
BASE_URL = f"http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}{settings.API_V1_STR}"


class APIClient:
    """Typed HTTP client wrapping every backend endpoint."""

    def __init__(self, base_url: str = BASE_URL, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ── Health ────────────────────────────────────────────────────────
    def check_health(self) -> dict[str, Any] | None:
        try:
            with httpx.Client(timeout=self.timeout) as c:
                res = c.get(f"{self.base_url}/health")
                if res.status_code == 200:
                    return res.json()
        except Exception:
            return None
        return None

    # ── AST / Static Analysis ────────────────────────────────────────
    def analyze_ast(
        self, code: str, language: str = "auto", filename: str | None = None
    ) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            payload: dict[str, Any] = {"code": code, "language": language}
            if filename:
                payload["filename"] = filename
            res = c.post(f"{self.base_url}/ast/analyze", json=payload)
            res.raise_for_status()
            return res.json()

    # ── Explain ──────────────────────────────────────────────────────
    def explain_code(
        self,
        code: str,
        language: str = "auto",
        level: str = "Beginner",
        include_ast: bool = True,
        enable_rag: bool = True,
        save_history: bool = True,
        filename: str | None = None,
    ) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            payload: dict[str, Any] = {
                "code": code,
                "language": language,
                "level": level,
                "include_ast_analysis": include_ast,
                "enable_rag": enable_rag,
                "save_history": save_history,
            }
            if filename:
                payload["filename"] = filename
            res = c.post(f"{self.base_url}/explain", json=payload)
            res.raise_for_status()
            return res.json()

    # ── Trace ────────────────────────────────────────────────────────
    def trace_code(
        self,
        code: str,
        language: str = "python",
        input_data: str | None = None,
        generate_flowchart: bool = False,
    ) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            payload: dict[str, Any] = {
                "code": code,
                "language": language,
                "generate_flowchart": generate_flowchart,
            }
            if input_data:
                payload["input_data"] = input_data
            res = c.post(f"{self.base_url}/trace", json=payload)
            res.raise_for_status()
            return res.json()

    # ── Quiz ─────────────────────────────────────────────────────────
    def generate_quiz(
        self, code: str, language: str = "python", locale: str = "en"
    ) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            payload: dict[str, Any] = {
                "code": code,
                "language": language,
                "locale": locale,
            }
            res = c.post(f"{self.base_url}/quiz", json=payload)
            res.raise_for_status()
            return res.json()

    # ── History ───────────────────────────────────────────────────────
    def get_history(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        try:
            with httpx.Client(timeout=self.timeout) as c:
                res = c.get(
                    f"{self.base_url}/history",
                    params={"limit": limit, "offset": offset},
                )
                if res.status_code == 200:
                    return res.json()
        except Exception:
            return []
        return []

    def get_history_item(self, record_id: int) -> dict[str, Any] | None:
        try:
            with httpx.Client(timeout=self.timeout) as c:
                res = c.get(f"{self.base_url}/history/{record_id}")
                if res.status_code == 200:
                    return res.json()
        except Exception:
            return None
        return None

    # ── Concepts ─────────────────────────────────────────────────────
    def get_concepts(self, name: str, limit: int = 20) -> list[dict[str, Any]]:
        try:
            with httpx.Client(timeout=self.timeout) as c:
                res = c.get(
                    f"{self.base_url}/concepts/{name}",
                    params={"limit": limit},
                )
                if res.status_code == 200:
                    return res.json()
        except Exception:
            return []
        return []

    # ── RAG Knowledge Base ───────────────────────────────────────────
    def search_rag(
        self,
        query: str,
        language: str = "auto",
        top_k: int = 3,
        similarity_threshold: float = 0.35,
    ) -> dict[str, Any] | None:
        try:
            with httpx.Client(timeout=self.timeout) as c:
                payload = {
                    "query": query,
                    "language": language,
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold,
                }
                res = c.post(f"{self.base_url}/rag/retrieve", json=payload)
                if res.status_code == 200:
                    return res.json()
        except Exception:
            return None
        return None

    def get_rag_stats(self) -> dict[str, int]:
        try:
            with httpx.Client(timeout=self.timeout) as c:
                res = c.get(f"{self.base_url}/rag/stats")
                if res.status_code == 200:
                    return res.json()
        except Exception:
            return {"documents": 0, "chunks": 0}
        return {"documents": 0, "chunks": 0}

    # ── Auth ─────────────────────────────────────────────────────────
    def signup(self, username: str, password: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            payload = {"username": username, "password": password}
            res = c.post(f"{self.base_url}/auth/signup", json=payload)
            res.raise_for_status()
            return res.json()

    def login(self, username: str, password: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            payload = {"username": username, "password": password}
            res = c.post(f"{self.base_url}/auth/login", json=payload)
            res.raise_for_status()
            return res.json()

