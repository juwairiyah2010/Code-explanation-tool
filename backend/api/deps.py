"""FastAPI Dependency Injection providers."""

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models.persistence import User
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


security_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    auth_header: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    x_auth_token: str | None = Header(None, alias="X-Auth-Token"),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Extract and authenticate session token from Bearer header or X-Auth-Token header."""
    token = None
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    elif x_auth_token:
        token = x_auth_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = AuthService.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_repo.get_by_id(payload["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_current_user(
    auth_header: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    x_auth_token: str | None = Header(None, alias="X-Auth-Token"),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User | None:
    """Return authenticated User if token is present and valid, otherwise None."""
    token = None
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    elif x_auth_token:
        token = x_auth_token

    if not token:
        return None

    payload = AuthService.verify_access_token(token)
    if not payload:
        return None

    return user_repo.get_by_id(payload["user_id"])



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
