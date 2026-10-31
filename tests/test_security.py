import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.auth_service import AuthService, PBKDF2_ITERATIONS, LEGACY_ITERATIONS
from backend.core.security import SlidingWindowRateLimiter, sanitize_internal_error
from backend.config import get_settings


client = TestClient(app)


def test_password_hashing_owasp_iterations():
    """Verify password hashing uses 600,000 PBKDF2 iterations and verifies correctly."""
    pwd = "superSecurePassword123!"
    hashed = AuthService.hash_password(pwd)
    
    assert hashed.startswith(f"pbkdf2:sha256:{PBKDF2_ITERATIONS}$")
    assert AuthService.verify_password(pwd, hashed) is True
    assert AuthService.verify_password("wrongPassword", hashed) is False


def test_password_hashing_legacy_backward_compatibility():
    """Verify backward compatibility with legacy 100,000 iteration hashes."""
    import hashlib
    salt = "deadbeef12345678"
    key = hashlib.pbkdf2_hmac("sha256", b"legacyPass123", salt.encode("utf-8"), LEGACY_ITERATIONS)
    legacy_hash = f"{salt}${key.hex()}"
    
    assert AuthService.verify_password("legacyPass123", legacy_hash) is True
    assert AuthService.verify_password("wrongPass", legacy_hash) is False


def test_password_policy_enforcement():
    """Verify short passwords (< 8 chars) are rejected."""
    class MockUserRepo:
        def get_by_username(self, u):
            return None
        def create(self, **kwargs):
            return None

    service = AuthService(MockUserRepo())
    
    with pytest.raises(ValueError, match="at least 8 characters"):
        service.register_user("validuser", "short")

    with pytest.raises(ValueError, match="between 3 and 64 characters"):
        service.register_user("ab", "validPassword123!")


def test_tracer_sandbox_blocks_dunder_reflection():
    """Verify sandbox AST blocks dunder exploration and reflection."""
    code = "classes = ().__class__.__subclasses__()"
    response = client.post("/api/v1/trace", json={"code": code, "language": "python"})
    assert response.status_code == 400
    assert "SecurityError" in response.json()["detail"] or "__subclasses__" in response.json()["detail"]


def test_request_size_limit_rejection():
    """Verify requests exceeding max_content_length are rejected with 413."""
    # Send a request with a header declaring > 2MB
    headers = {"Content-Length": "3000000"}
    response = client.post("/api/v1/ast/analyze", headers=headers, json={"code": "x = 1"})
    assert response.status_code == 413
    assert "Payload size exceeds" in response.json()["detail"]


def test_error_sanitization():
    """Verify error sanitization in production vs development."""
    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    orig_debug = settings.DEBUG
    try:
        settings.ENVIRONMENT = "production"
        settings.DEBUG = False
        safe_msg = sanitize_internal_error(ValueError("secret_internal_db_path_error"), "Test context")
        assert "secret_internal_db_path_error" not in safe_msg
        assert "internal server error occurred" in safe_msg.lower()

        settings.ENVIRONMENT = "development"
        settings.DEBUG = True
        dev_msg = sanitize_internal_error(ValueError("debug_visible_error"), "Test context")
        assert "debug_visible_error" in dev_msg
    finally:
        settings.ENVIRONMENT = orig_env
        settings.DEBUG = orig_debug


def test_sliding_window_rate_limiter():
    """Verify sliding window rate limiter blocks after reaching threshold."""
    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    orig_rate = settings.RATE_LIMITING_ENABLED
    try:
        settings.ENVIRONMENT = "production"
        settings.RATE_LIMITING_ENABLED = True
        limiter = SlidingWindowRateLimiter(times=3, seconds=10)
        ip = "203.0.113.195"
        
        limited1, _ = limiter.is_rate_limited(ip)
        assert limited1 is False
        limited2, _ = limiter.is_rate_limited(ip)
        assert limited2 is False
        limited3, _ = limiter.is_rate_limited(ip)
        assert limited3 is False
        
        # 4th call should be rate limited
        limited4, retry_after = limiter.is_rate_limited(ip)
        assert limited4 is True
        assert retry_after > 0
    finally:
        settings.ENVIRONMENT = orig_env
        settings.RATE_LIMITING_ENABLED = orig_rate
