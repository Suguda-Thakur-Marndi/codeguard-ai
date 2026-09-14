"""Organizations API endpoints."""

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user_or_bypass
from app.db.repositories.organization_repo import OrganizationRepository
from app.db.session import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.organization import OrganizationRead

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("", response_model=PaginatedResponse[OrganizationRead])
def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_or_bypass),
) -> PaginatedResponse[OrganizationRead]:
    """List installed organizations with pagination."""
    repo = OrganizationRepository(db)
    items, total = repo.get_all(page=page, page_size=page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse[OrganizationRead](
        items=[OrganizationRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
