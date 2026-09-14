"""GitHub App JWT generation and Installation token provider."""

import time
from datetime import datetime

import httpx
import jwt

from app.core.config import settings
from app.core.exceptions import GitHubAuthError
from app.core.logging import TimingLogger, logger


class GitHubAppAuth:
    """Handles GitHub App authentication using RS256 JWTs and installation access tokens."""

    def __init__(
        self,
        app_id: str | None = None,
        private_key: str | None = None,
    ):
        self.app_id = app_id or settings.GITHUB_APP_ID
        self.private_key = private_key or settings.GITHUB_PRIVATE_KEY
        # In-memory cache for installation tokens: {installation_id: (token, expiry_timestamp)}
        self._token_cache: dict[int, tuple[str, float]] = {}

    def generate_app_jwt(self) -> str:
        """Generate RS256 JWT valid for 10 minutes to authenticate as the GitHub App."""
        if not self.private_key or self.app_id in ("dev-app-id", ""):
            # When running without private key in dev/testing, raise or handle mock
            if settings.APP_ENV in ("development", "test"):
                return "mock-github-app-jwt"
            raise GitHubAuthError("Missing GITHUB_PRIVATE_KEY or GITHUB_APP_ID")

        now = int(time.time())
        payload = {
            "iat": now - 60,  # 60 seconds in the past for clock drift
            "exp": now + (10 * 60),  # 10 minutes expiry
            "iss": self.app_id,
        }

        try:
            private_key = self.private_key.replace("\\n", "\n")
            return jwt.encode(payload, private_key, algorithm="RS256")
        except Exception as e:
            logger.error("Failed to sign GitHub App JWT", exc_info=True)
            raise GitHubAuthError(f"Failed to generate GitHub App JWT: {str(e)}") from e

    async def get_installation_access_token(
        self,
        installation_id: int,
        client: httpx.AsyncClient | None = None,
    ) -> str:
        """Fetch or return cached installation access token from GitHub."""
        now = time.time()
        if installation_id in self._token_cache:
            cached_token, expires_at = self._token_cache[installation_id]
            # Reuse token if it has at least 60 seconds before expiring
            if expires_at - now > 60:
                return cached_token

        # In dev/test environment without credentials, return mock token
        if not self.private_key and settings.APP_ENV in ("development", "test"):
            mock_token = f"ghs_mock_token_for_{installation_id}"
            self._token_cache[installation_id] = (mock_token, now + 3600)
            return mock_token

        app_jwt = self.generate_app_jwt()
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        with TimingLogger("github_api_installation_token", {"installation_id": installation_id}):
            if client is not None:
                resp = await client.post(url, headers=headers, timeout=15.0)
            else:
                async with httpx.AsyncClient() as c:
                    resp = await c.post(url, headers=headers, timeout=15.0)

            if resp.status_code != 201:
                raise GitHubAuthError(
                    f"Failed to obtain installation token for {installation_id}: {resp.text}",
                    details={"status_code": resp.status_code},
                )

            data = resp.json()
            token = data["token"]
            # Expiration time parsing
            expires_at_str = data.get("expires_at")
            expires_at_ts = now + 3600
            if expires_at_str:
                try:
                    dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                    expires_at_ts = dt.timestamp()
                except Exception:
                    pass

            self._token_cache[installation_id] = (token, expires_at_ts)
            return token
