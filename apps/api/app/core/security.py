"""Security utilities: HMAC webhook verification and authentication."""

import hashlib
import hmac

from fastapi import Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security_bearer = HTTPBearer(auto_error=False)


def verify_github_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Verify GitHub webhook signature using HMAC-SHA256 in constant time.

    Args:
        raw_body: Exact raw bytes of the request body.
        signature_header: The value of the X-Hub-Signature-256 header.

    Returns:
        bool: True if signature is valid, False otherwise.
    """
    if not signature_header:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[len("sha256=") :]
    secret_bytes = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")

    mac = hmac.new(secret_bytes, msg=raw_body, digestmod=hashlib.sha256)
    computed_signature = mac.hexdigest()

    return hmac.compare_digest(computed_signature, expected_signature)


async def get_current_user_or_bypass(
    request: Request,
    auth_header: HTTPAuthorizationCredentials | None = None,
    x_dev_token: str | None = Header(None, alias="X-Dev-Token"),
) -> dict:
    """
    Authenticate request or grant development session when DEV_AUTH_BYPASS is active.

    Production must use verified JWT tokens or session cookies.
    """
    # 1. Dev auth bypass if explicitly enabled and not in production
    if settings.DEV_AUTH_BYPASS and settings.APP_ENV != "production":
        return {
            "id": "dev-user-001",
            "login": "developer",
            "email": "dev@codeguard.local",
            "role": "admin",
            "is_dev": True,
        }

    # 2. Token / Session authentication check
    token = None
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    elif x_dev_token:
        token = x_dev_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In Phase 1 foundation, validate token against SECRET_KEY or dev token
    if token == settings.DEV_AUTH_TOKEN:
        return {
            "id": "dev-token-user",
            "login": "dev-token-user",
            "email": "dev-token@codeguard.local",
            "role": "developer",
        }

    # If an actual JWT is supplied, decode it safely
    try:
        import jwt
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return {
            "id": payload.get("sub"),
            "login": payload.get("login", "unknown"),
            "email": payload.get("email"),
            "role": payload.get("role", "user"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
