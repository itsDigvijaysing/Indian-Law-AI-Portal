"""
Shared API Dependencies

Common FastAPI dependencies used across routers.
"""

import hmac

from fastapi import Header, HTTPException, Request
from .core.ai_service import AIService
from .core.config import get_settings
from .core.rate_limiter import get_rate_limiter


def get_ai_service(request: Request) -> AIService:
    """Dependency to get AI service from app state"""
    if not hasattr(request.app.state, 'ai_service'):
        raise HTTPException(status_code=503, detail="AI service not available")
    return request.app.state.ai_service


async def require_admin(x_admin_key: str = Header(default="")) -> None:
    """Guard for sensitive /admin endpoints.

    - ADMIN_API_KEY set   -> the X-Admin-Key request header must match it.
    - ADMIN_API_KEY unset -> allowed only in DEBUG_MODE (local development);
      on a deployed instance (DEBUG_MODE=false) the endpoints are disabled.
    """
    settings = get_settings()
    if settings.ADMIN_API_KEY:
        if not hmac.compare_digest(x_admin_key.encode(), settings.ADMIN_API_KEY.encode()):
            raise HTTPException(status_code=403, detail="Invalid or missing admin key")
        return
    if settings.DEBUG_MODE:
        return
    raise HTTPException(status_code=403, detail="Admin endpoints are disabled on this deployment")


def safe_error_detail(public_message: str, exc: Exception) -> str:
    """Error detail for 500 responses: include the exception only in DEBUG_MODE.

    Deployed instances must not leak internals (filesystem paths, provider
    errors) to callers — the full exception is always in the server log.
    """
    if get_settings().DEBUG_MODE:
        return f"{public_message}: {exc}"
    return public_message


async def enforce_daily_limit() -> None:
    """Consume one unit of the global daily quota, or reject with 429.

    Applied to every endpoint that triggers an LLM answer generation. The 429
    `detail` is a structured object the frontend renders as its rate-limit
    modal (kind, message, limit, used, reset_at).
    """
    settings = get_settings()
    if not settings.RATE_LIMIT_ENABLED:
        return

    status = await get_rate_limiter().consume()
    if not status["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "kind": "daily_limit",
                "message": (
                    f"Today's free limit of {status['limit']} "
                    f"question{'' if status['limit'] == 1 else 's'} has been "
                    "reached. This is a free, open-source project running on a "
                    "personal budget, so daily use is capped to keep it online for "
                    "everyone. The quota resets at midnight UTC."
                ),
                "limit": status["limit"],
                "used": status["used"],
                "reset_at": status["reset_at"],
            },
        )
