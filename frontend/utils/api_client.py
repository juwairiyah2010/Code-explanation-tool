import os
import sys
from pathlib import Path
from typing import Any
import httpx

_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from backend.config import get_settings

settings = get_settings()
explicit_url = os.getenv("BACKEND_URL") or os.getenv("API_BASE_URL") or settings.BACKEND_URL
if explicit_url:
    BASE_URL = explicit_url.rstrip("/")
else:
    BASE_URL = f"http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}{settings.API_V1_STR}"


class APIClient:
    """Typed HTTP client wrapping every backend endpoint with secure session handling."""

    def __init__(self, base_url: str = BASE_URL, timeout: float = 30.0, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token: str | None = token

    def set_token(self, token: str | None) -> None:
        """Update authenticated session token."""
        self.token = token

    def _auth_headers(self, additional: dict[str, str] | None = None) -> dict[str, str]:
        """Construct headers including Authorization bearer token when session is active."""
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if additional:
            headers.update(additional)
        return headers

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
            res = c.post(f"{self.base_url}/explain", json=payload, headers=self._auth_headers())
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

    # ── Quiz & Interactive Learning ──────────────────────────────────
    def generate_quiz(
        self, code: str, language: str = "python", locale: str = "en", workflow: str = "learning"
    ) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            payload: dict[str, Any] = {
                "code": code,
                "language": language,
                "locale": locale,
                "workflow": workflow,
            }
            res = c.post(f"{self.base_url}/quiz", json=payload)
            res.raise_for_status()
            return res.json()

    def generate_learning_material(
        self, code: str, language: str = "python", locale: str = "en"
    ) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            payload: dict[str, Any] = {
                "code": code,
                "language": language,
                "locale": locale,
            }
            res = c.post(f"{self.base_url}/learning/material", json=payload)
            res.raise_for_status()
            return res.json()

    def submit_learning_answers(
        self,
        code: str,
        language: str,
        answers: dict[str, str],
        questions_payload: list[dict[str, Any]] | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            payload: dict[str, Any] = {
                "code": code,
                "language": language,
                "answers": answers,
                "questions_payload": questions_payload,
                "user_id": user_id,
            }
            res = c.post(f"{self.base_url}/learning/submit", json=payload, headers=self._auth_headers())
            res.raise_for_status()
            return res.json()

    def get_learner_progress(self, user_id: int | None = None) -> list[dict[str, Any]]:
        try:
            with httpx.Client(timeout=self.timeout) as c:
                params = {"user_id": user_id} if user_id else {}
                res = c.get(f"{self.base_url}/learning/progress", params=params, headers=self._auth_headers())
                if res.status_code == 200:
                    return res.json()
        except Exception:
            return []
        return []

    # ── History ───────────────────────────────────────────────────────
    def get_history(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        try:
            with httpx.Client(timeout=self.timeout) as c:
                res = c.get(
                    f"{self.base_url}/history",
                    params={"limit": limit, "offset": offset},
                    headers=self._auth_headers(),
                )
                if res.status_code == 200:
                    return res.json()
        except Exception:
            return []
        return []

    def get_history_item(self, record_id: int) -> dict[str, Any] | None:
        try:
            with httpx.Client(timeout=self.timeout) as c:
                res = c.get(f"{self.base_url}/history/{record_id}", headers=self._auth_headers())
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

    # ── Auth & Profile ───────────────────────────────────────────────
    def signup(self, username: str, password: str) -> dict[str, Any]:
        """Register a new user account. Returns user data with token or raises ValueError."""
        with httpx.Client(timeout=self.timeout) as c:
            payload = {"username": username, "password": password}
            res = c.post(f"{self.base_url}/auth/signup", json=payload)
            if res.status_code == 200:
                data = res.json()
                if data.get("token"):
                    self.set_token(data["token"])
                return data
            try:
                err_detail = res.json().get("detail", res.text)
            except Exception:
                err_detail = res.text
            raise ValueError(err_detail)

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate user credentials. Returns user data with token or raises ValueError."""
        with httpx.Client(timeout=self.timeout) as c:
            payload = {"username": username, "password": password}
            res = c.post(f"{self.base_url}/auth/login", json=payload)
            if res.status_code == 200:
                data = res.json()
                if data.get("token"):
                    self.set_token(data["token"])
                return data
            try:
                err_detail = res.json().get("detail", res.text)
            except Exception:
                err_detail = res.text
            raise ValueError(err_detail)

    def get_profile(self) -> dict[str, Any] | None:
        """Fetch current authenticated user profile."""
        try:
            with httpx.Client(timeout=self.timeout) as c:
                res = c.get(f"{self.base_url}/auth/me", headers=self._auth_headers())
                if res.status_code == 200:
                    return res.json()
        except Exception:
            return None
        return None


