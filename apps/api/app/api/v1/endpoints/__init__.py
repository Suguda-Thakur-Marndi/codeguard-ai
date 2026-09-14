"""API v1 endpoints export."""

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.organizations import router as organizations_router
from app.api.v1.endpoints.pull_requests import router as pull_requests_router
from app.api.v1.endpoints.repositories import router as repositories_router
from app.api.v1.endpoints.review_jobs import router as review_jobs_router
from app.api.v1.endpoints.webhooks import router as webhooks_router

__all__ = [
    "health_router",
    "webhooks_router",
    "organizations_router",
    "repositories_router",
    "pull_requests_router",
    "review_jobs_router",
]
