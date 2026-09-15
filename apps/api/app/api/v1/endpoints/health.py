"""Health and readiness check endpoints."""

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.db.session import check_db_connectivity
from app.schemas.common import HealthResponse, ReadinessResponse

router = APIRouter(tags=["Health"])


def check_redis_connectivity() -> bool:
    """Verify Redis connection for the readiness probe."""
    try:
        import redis
        client = redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        return client.ping()
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    General health probe exposing application name, version, and environment.
    """
    return HealthResponse(
        status="ok",
        app="codeguard-ai",
        version="0.1.0",
        environment=settings.APP_ENV,
        git_revision=settings.GIT_REVISION,
    )


@router.get("/live", response_model=HealthResponse)
def liveness_check() -> HealthResponse:
    """
    Liveness probe: Confirms that the API process is alive and responsive.
    Does not verify external backing services.
    """
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        git_revision=settings.GIT_REVISION,
    )


@router.get("/ready", response_model=ReadinessResponse)
def readiness_check(response: Response) -> ReadinessResponse:
    """
    Readiness probe: Validates PostgreSQL and Redis connectivity.
    Returns HTTP 200 if all services are operational, or 503 if any dependency is unavailable.
    """
    postgres_ok = check_db_connectivity()
    redis_ok = check_redis_connectivity()

    all_ready = postgres_ok and redis_ok

    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if all_ready else "degraded",
        postgres="connected" if postgres_ok else "disconnected",
        redis="connected" if redis_ok else "disconnected",
    )
