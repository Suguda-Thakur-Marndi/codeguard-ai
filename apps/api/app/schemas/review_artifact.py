"""ReviewArtifact Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.review_artifact import ArtifactType


class ReviewArtifactBase(BaseModel):
    review_job_id: str
    artifact_type: ArtifactType
    content: str
    metadata_json: dict[str, Any] = {}


class ReviewArtifactCreate(ReviewArtifactBase):
    pass


class ReviewArtifactRead(ReviewArtifactBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
