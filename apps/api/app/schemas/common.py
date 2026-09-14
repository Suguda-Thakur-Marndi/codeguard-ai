"""Common API schemas for pagination and system status."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    page: int = Field(default=1, ge=1, description="Page number starting at 1")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated collection response."""
    items: list[T]
    total: int = Field(description="Total count of matching items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """Liveness check response."""
    status: str = "ok"
    app: str = "codeguard-ai"
    version: str = "1.0.0"
    environment: str = "development"
    git_revision: str | None = None


class ReadinessCheckItem(BaseModel):
    status: str
    message: str | None = None


class ReadinessResponse(BaseModel):
    """Readiness check response verifying database and Redis."""
    status: str  # "ready" or "degraded"
    postgres: str  # "connected" or "disconnected"
    redis: str     # "connected" or "disconnected"
