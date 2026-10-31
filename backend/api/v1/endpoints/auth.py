"""Authentication and user registration endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.api.deps import get_auth_service, get_current_user
from backend.core.security import rate_limit_auth
from backend.models.persistence import User
from backend.schemas.auth import UserCreate, UserLogin, UserResponse
from backend.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Register a new user",
    dependencies=[Depends(rate_limit_auth)],
)
def signup(
    user: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Register a new user account with hashed password and return session token."""
    try:
        new_user = auth_service.register_user(username=user.username, password=user.password)
        token = auth_service.create_access_token(user_id=new_user.id, username=new_user.username)
        return UserResponse(id=new_user.id, username=new_user.username, token=token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/login",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user credentials",
    dependencies=[Depends(rate_limit_auth)],
)
def login(
    user: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Validate user credentials and return user profile with session token."""
    authenticated = auth_service.authenticate_user(username=user.username, password=user.password)
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid username or password",
        )
    token = auth_service.create_access_token(user_id=authenticated.id, username=authenticated.username)
    return UserResponse(id=authenticated.id, username=authenticated.username, token=token)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return profile details for current authenticated session."""
    return UserResponse(id=current_user.id, username=current_user.username)

