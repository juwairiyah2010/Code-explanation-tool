"""Authentication service encapsulating password hashing and credential validation."""

import hashlib
import hmac
import secrets
from backend.models.persistence import User
from backend.repositories.user_repo import UserRepository


class AuthService:
    """Service handling user account registration and authentication logic."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> str:
        """Hash password with PBKDF2-HMAC-SHA256 and cryptographic salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return f"{salt}${key.hex()}"

    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        """Verify password against stored salt and key using constant-time comparison."""
        try:
            salt, key = password_hash.split("$")
            computed = cls.hash_password(password, salt)
            return hmac.compare_digest(computed, password_hash)
        except (ValueError, AttributeError):
            return False

    def register_user(self, username: str, password: str) -> User:
        """Register a new user account if username is available."""
        clean_username = username.strip()
        if not clean_username or not password:
            raise ValueError("Username and password must not be empty.")

        existing = self.user_repo.get_by_username(clean_username)
        if existing:
            raise ValueError("Username already registered")

        password_hash = self.hash_password(password)
        return self.user_repo.create(username=clean_username, password_hash=password_hash)

    def authenticate_user(self, username: str, password: str) -> User | None:
        """Verify user credentials and return User record if valid."""
        clean_username = username.strip()
        user = self.user_repo.get_by_username(clean_username)
        if not user:
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        return user
