"""Organization Review Policy ORM model for configurable governance rules."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class OrganizationReviewPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Organization-level policy settings controlling AI review publishing and human approval gates."""

    __tablename__ = "organization_review_policies"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    auto_publish_advisory: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    auto_publish_low: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    require_approval_for_high: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    require_approval_for_critical: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    allow_request_changes: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    allow_ai_github_comments: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    approval_expiry_minutes: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
