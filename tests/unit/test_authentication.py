"""Unit tests for authentication service, password policies, and PBKDF2 hashing."""

import hashlib
import pytest
from backend.services.auth_service import AuthService, PBKDF2_ITERATIONS, LEGACY_ITERATIONS
from backend.repositories.user_repo import UserRepository


@pytest.fixture
def auth_service(db_session) -> AuthService:
    repo = UserRepository(db_session)
    return AuthService(repo)


def test_hash_and_verify_password(auth_service: AuthService):
    """Verify PBKDF2-HMAC-SHA256 password hashing and verification."""
    pwd = "SecureStudentPass2026!"
    hashed = auth_service.hash_password(pwd)
    assert hashed.startswith(f"pbkdf2:sha256:{PBKDF2_ITERATIONS}$")
    assert auth_service.verify_password(pwd, hashed) is True
    assert auth_service.verify_password("wrongPassword", hashed) is False


def test_legacy_password_hash_verification(auth_service: AuthService):
    """Verify backward compatibility with legacy 100,000-iteration hashes."""
    salt = "abcdef1234567890"
    key = hashlib.pbkdf2_hmac("sha256", b"legacySecretPass", salt.encode("utf-8"), LEGACY_ITERATIONS)
    legacy_hash = f"{salt}${key.hex()}"
    assert auth_service.verify_password("legacySecretPass", legacy_hash) is True
    assert auth_service.verify_password("wrongSecretPass", legacy_hash) is False


def test_register_and_authenticate_user(auth_service: AuthService):
    """Verify end-to-end registration and credential authentication."""
    user = auth_service.register_user("student_coder", "mySecretPass123!")
    assert user.id is not None
    assert user.username == "student_coder"

    # Successful auth
    auth_user = auth_service.authenticate_user("student_coder", "mySecretPass123!")
    assert auth_user is not None
    assert auth_user.id == user.id

    # Failed auth with wrong password
    bad_auth = auth_service.authenticate_user("student_coder", "wrongPass")
    assert bad_auth is None

    # Failed auth with unknown user
    unknown_auth = auth_service.authenticate_user("nonexistent", "pass")
    assert unknown_auth is None


def test_password_policy_rejections(auth_service: AuthService):
    """Verify password and username policy rejections."""
    # Password too short (< 8 chars)
    with pytest.raises(ValueError, match="at least 8"):
        auth_service.register_user("alice", "short")

    # Username too short (< 3 chars)
    with pytest.raises(ValueError, match="between 3 and 64"):
        auth_service.register_user("al", "validPass123!")

    # Duplicate username
    auth_service.register_user("duplicate_user", "validPass123!")
    with pytest.raises(ValueError, match="already registered"):
        auth_service.register_user("duplicate_user", "anotherPass123!")


def test_session_token_generation_and_verification(auth_service: AuthService):
    """Verify cryptographic session token generation, verification, and tampering rejection."""
    token = auth_service.create_access_token(user_id=42, username="test_learner")
    assert isinstance(token, str)
    assert len(token) > 20

    # Successful verification
    payload = auth_service.verify_access_token(token)
    assert payload is not None
    assert payload["user_id"] == 42
    assert payload["username"] == "test_learner"

    # Tampered token rejection
    tampered = token[:-4] + "fake"
    assert auth_service.verify_access_token(tampered) is None

    # Invalid string / empty token rejection
    assert auth_service.verify_access_token("") is None
    assert auth_service.verify_access_token("completely_invalid_garbage") is None

