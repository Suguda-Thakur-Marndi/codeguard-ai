"""ReviewJob Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.review_job import ReviewJobStatus


class ReviewJobBase(BaseModel):
    pull_request_id: str
    status: ReviewJobStatus = ReviewJobStatus.PENDING
    trigger: str = "webhook:opened"


class ReviewJobCreate(ReviewJobBase):
    pass


class ReviewJobRead(ReviewJobBase):
    id: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    total_tokens: int = 0
    estimated_cost: float = 0.0
    agents_executed: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
