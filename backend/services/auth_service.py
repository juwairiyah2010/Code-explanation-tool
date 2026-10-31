"""Authentication service encapsulating password hashing and credential validation."""

import hashlib
import hmac
import secrets
from backend.models.persistence import User
from backend.repositories.user_repo import UserRepository


PBKDF2_ITERATIONS = 600000  # OWASP recommended minimum for PBKDF2-HMAC-SHA256
LEGACY_ITERATIONS = 100000
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class AuthService:
    """Service handling user account registration and authentication logic."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    @staticmethod
    def hash_password(password: str, salt: str | None = None, iterations: int = PBKDF2_ITERATIONS) -> str:
        """Hash password with PBKDF2-HMAC-SHA256 and cryptographic salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return f"pbkdf2:sha256:{iterations}${salt}${key.hex()}"

    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        """Verify password against stored hash using constant-time comparison."""
        try:
            if password_hash.startswith("pbkdf2:sha256:"):
                # Modern format: pbkdf2:sha256:<iterations>$<salt>$<key>
                parts = password_hash.split("$")
                if len(parts) != 3:
                    return False
                header, salt, _ = parts
                iter_str = header.split(":")[-1]
                iterations = int(iter_str)
                computed = cls.hash_password(password, salt, iterations=iterations)
                return hmac.compare_digest(computed, password_hash)
            else:
                # Legacy format: <salt>$<key> (100,000 iterations)
                parts = password_hash.split("$")
                if len(parts) != 2:
                    return False
                salt, _ = parts
                key = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt.encode("utf-8"),
                    LEGACY_ITERATIONS,
                )
                computed = f"{salt}${key.hex()}"
                return hmac.compare_digest(computed, password_hash)
        except (ValueError, AttributeError):
            return False

    def register_user(self, username: str, password: str) -> User:
        """Register a new user account if username is available and password satisfies policy."""
        clean_username = username.strip()
        if not clean_username or not password:
            raise ValueError("Username and password must not be empty.")

        if len(clean_username) < 3 or len(clean_username) > 64:
            raise ValueError("Username must be between 3 and 64 characters.")

        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

        if len(password) > MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password cannot exceed {MAX_PASSWORD_LENGTH} characters.")

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

    @classmethod
    def create_access_token(cls, user_id: int, username: str) -> str:
        """Generate a cryptographically signed, tamper-proof session token."""
        from itsdangerous import URLSafeTimedSerializer
        from backend.config import get_settings

        settings = get_settings()
        serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="code-lore-session")
        return serializer.dumps({"user_id": user_id, "username": username})

    @classmethod
    def verify_access_token(cls, token: str, max_age: int = 86400 * 30) -> dict | None:
        """Verify session token signature and expiration. Returns payload dict or None."""
        if not token or not isinstance(token, str):
            return None
        from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
        from backend.config import get_settings

        settings = get_settings()
        serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="code-lore-session")
        try:
            payload = serializer.loads(token, max_age=max_age)
            if isinstance(payload, dict) and "user_id" in payload:
                return payload
            return None
        except (BadSignature, SignatureExpired, Exception):
            return None

