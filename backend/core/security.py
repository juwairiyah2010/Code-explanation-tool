"""Security utilities including in-memory sliding-window rate limiting, request size protection, and error sanitization."""

import time
from collections import defaultdict
from collections.abc import Callable
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from backend.config import get_settings
from backend.core.logging import logger

settings = get_settings()


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter tracking request timestamps per client IP."""

    def __init__(self, times: int = 30, seconds: int = 60):
        self.times = times
        self.seconds = seconds
        self._history: dict[str, list[float]] = defaultdict(list)

    def is_rate_limited(self, key: str) -> tuple[bool, int]:
        """Check if key has exceeded the allowed rate. Returns (is_limited, retry_after_seconds)."""
        if not settings.RATE_LIMITING_ENABLED or settings.ENVIRONMENT == "testing" or key == "testclient":
            return False, 0

        now = time.monotonic()
        window_start = now - self.seconds

        # Clean timestamps older than window
        timestamps = [t for t in self._history[key] if t > window_start]
        self._history[key] = timestamps

        if len(timestamps) >= self.times:
            retry_after = max(1, int(timestamps[0] + self.seconds - now))
            return True, retry_after

        self._history[key].append(now)
        return False, 0

    def __call__(self, request: Request) -> None:
        """FastAPI dependency verifying client rate limit."""
        client_ip = request.client.host if request.client else "127.0.0.1"
        limited, retry_after = self.is_rate_limited(client_ip)
        if limited:
            logger.warning(f"Rate limit exceeded for client IP '{client_ip}' on endpoint '{request.url.path}'")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please retry in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )


# Pre-configured rate limiters for sensitive / expensive endpoints
rate_limit_auth = SlidingWindowRateLimiter(times=15, seconds=60)      # 15 auth attempts / minute
rate_limit_expensive = SlidingWindowRateLimiter(times=30, seconds=60) # 30 expensive calls / minute


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforce maximum HTTP request body size to protect against memory exhaustion DoS."""

    def __init__(self, app, max_content_length: int = 2 * 1024 * 1024):  # 2 MB limit
        super().__init__(app)
        self.max_content_length = max_content_length

    async def dispatch(self, request: Request, call_next: Callable):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_content_length:
                    logger.warning(f"Rejected payload exceeding size limit: {content_length} bytes from {request.client.host if request.client else 'unknown'}")
                    return JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={"detail": f"Payload size exceeds maximum allowed limit ({self.max_content_length} bytes)."},
                    )
            except ValueError:
                pass
        return await call_next(request)


def sanitize_internal_error(exc: Exception, context_msg: str = "Internal server error") -> str:
    """Format safe error detail: detailed in development, generic in production."""
    logger.error(f"{context_msg}: {exc}", exc_info=True)
    if settings.DEBUG and settings.ENVIRONMENT == "development":
        return f"{context_msg}: {str(exc)}"
    return "An internal server error occurred. Please contact the administrator or try again later."
