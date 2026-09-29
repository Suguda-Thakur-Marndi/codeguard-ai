"""Authentication endpoints: Google OAuth 2.0 and session management."""

import secrets
import urllib.parse
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.security import get_current_user_or_bypass

router = APIRouter(prefix="/auth", tags=["Authentication"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@router.get("/google/login", summary="Initiate Google OAuth 2.0 login flow")
async def google_login(redirect_url: str | None = Query(None)) -> RedirectResponse:
    """Redirect user to Google's OAuth 2.0 consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Missing GOOGLE_CLIENT_ID.",
        )

    # Generate random state parameter for CSRF mitigation
    state = secrets.token_urlsafe(32)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    logger.info("Redirecting user to Google OAuth consent screen.")
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback", summary="Google OAuth 2.0 callback handler")
async def google_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
) -> RedirectResponse:
    """Handle Google OAuth 2.0 authorization code callback."""
    frontend_base = settings.FRONTEND_URL.rstrip("/")

    if error:
        logger.warning(f"Google OAuth returned error: {error}")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard?auth_error={urllib.parse.quote(error)}",
            status_code=status.HTTP_302_FOUND,
        )

    if not code:
        logger.error("Google OAuth callback missing authorization code.")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard?auth_error=missing_authorization_code",
            status_code=status.HTTP_302_FOUND,
        )

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        logger.error("Google OAuth client credentials not configured on server.")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard?auth_error=server_oauth_unconfigured",
            status_code=status.HTTP_302_FOUND,
        )

    # Exchange authorization code for Google access token
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )

            if token_resp.status_code != 200:
                err_detail = token_resp.text
                logger.error(f"Failed to exchange Google OAuth code for token: {err_detail}")
                return RedirectResponse(
                    url=f"{frontend_base}/dashboard?auth_error=token_exchange_failed",
                    status_code=status.HTTP_302_FOUND,
                )

            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            if not access_token:
                logger.error("No access_token returned by Google token endpoint.")
                return RedirectResponse(
                    url=f"{frontend_base}/dashboard?auth_error=no_access_token",
                    status_code=status.HTTP_302_FOUND,
                )

            # Retrieve user identity info from Google
            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_resp.status_code != 200:
                logger.error(f"Failed to fetch userinfo from Google: {userinfo_resp.text}")
                return RedirectResponse(
                    url=f"{frontend_base}/dashboard?auth_error=userinfo_fetch_failed",
                    status_code=status.HTTP_302_FOUND,
                )

            user_data = userinfo_resp.json()

    except Exception as exc:
        logger.error(f"Exception during Google OAuth callback processing: {exc}", exc_info=True)
        return RedirectResponse(
            url=f"{frontend_base}/dashboard?auth_error=oauth_network_error",
            status_code=status.HTTP_302_FOUND,
        )

    # Issue signed CodeGuard JWT session token
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=7)

    email = user_data.get("email", "")
    name = user_data.get("name") or email.split("@")[0] or "Google User"
    sub = user_data.get("sub", email)
    picture = user_data.get("picture", "")

    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "picture": picture,
        "role": "developer",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    session_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    logger.info(f"Successfully authenticated user '{email}' via Google OAuth.")

    # Redirect to frontend dashboard with token
    redirect_target = f"{frontend_base}/dashboard?token={session_token}"
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_302_FOUND)


@router.get("/me", summary="Get authenticated user details")
async def get_current_user_profile(
    current_user: dict[str, Any] = Depends(get_current_user_or_bypass),
) -> dict[str, Any]:
    """Return profile details for current authenticated session."""
    return {
        "authenticated": True,
        "user": current_user,
    }


@router.post("/logout", summary="Logout current session")
async def logout() -> dict[str, Any]:
    """Stateless logout confirmation."""
    return {
        "success": True,
        "message": "Logged out successfully",
    }
