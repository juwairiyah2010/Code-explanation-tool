"""FastAPI Dependency Injection providers."""

from fastapi import Depends
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.repositories.user_repo import UserRepository
from backend.repositories.submission_repo import SubmissionRepository
from backend.services.auth_service import AuthService
from backend.services.explanation_service import ExplanationService
from backend.services.history_service import HistoryService
from backend.services.quiz_service import QuizService
from backend.services.tracer_service import TracerService
from backend.services.rag.rag_service import RAGService
from backend.services.analysis.code_analyzer import CodeAnalyzer


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """Provide UserRepository instance bound to current database session."""
    return UserRepository(db)


def get_submission_repository(db: Session = Depends(get_db)) -> SubmissionRepository:
    """Provide SubmissionRepository instance bound to current database session."""
    return SubmissionRepository(db)


def get_auth_service(user_repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    """Provide AuthService instance with injected user repository."""
    return AuthService(user_repo)


def get_explanation_service(db: Session = Depends(get_db)) -> ExplanationService:
    """Provide ExplanationService instance with current database session."""
    return ExplanationService(db)


def get_history_service(
    submission_repo: SubmissionRepository = Depends(get_submission_repository),
) -> HistoryService:
    """Provide HistoryService instance with injected submission repository."""
    return HistoryService(submission_repo)


def get_quiz_service() -> QuizService:
    """Provide QuizService instance."""
    return QuizService()


def get_tracer_service() -> TracerService:
    """Provide TracerService instance."""
    return TracerService()


def get_rag_service(db: Session = Depends(get_db)) -> RAGService:
    """Provide RAGService instance with current database session."""
    return RAGService(db)


def get_code_analyzer() -> CodeAnalyzer:
    """Provide CodeAnalyzer service instance."""
    return CodeAnalyzer()
