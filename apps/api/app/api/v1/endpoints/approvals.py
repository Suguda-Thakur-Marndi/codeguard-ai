"""Approval request REST API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.approval_request import ApprovalStatus
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovePayload(BaseModel):
    comment: str | None = None


class RejectPayload(BaseModel):
    reason: str


@router.get("", response_model=dict[str, Any])
def list_approvals(
    organization_id: str | None = Query(default=None),
    repository_id: str | None = Query(default=None),
    pull_request_id: str | None = Query(default=None),
    status_filter: ApprovalStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = ApprovalService(db)
    items = service.list_approval_requests(
        organization_id=organization_id,
        repository_id=repository_id,
        pull_request_id=pull_request_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": req.id,
                "organization_id": req.organization_id,
                "repository_id": req.repository_id,
                "pull_request_id": req.pull_request_id,
                "review_job_id": req.review_job_id,
                "finding_id": req.finding_id,
                "requested_action": req.requested_action,
                "risk_level": req.risk_level,
                "status": req.status.value,
                "requested_by": req.requested_by,
                "approved_by": req.approved_by,
                "head_sha": req.head_sha,
                "expires_at": req.expires_at.isoformat(),
                "resolved_at": req.resolved_at.isoformat() if req.resolved_at else None,
                "reason": req.reason,
                "created_at": req.created_at.isoformat(),
            }
            for req in items
        ],
        "total": len(items),
    }


@router.get("/{approval_id}", response_model=dict[str, Any])
def get_approval(
    approval_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = ApprovalService(db)
    req = service.get_approval_request(approval_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")

    return {
        "id": req.id,
        "organization_id": req.organization_id,
        "repository_id": req.repository_id,
        "pull_request_id": req.pull_request_id,
        "review_job_id": req.review_job_id,
        "finding_id": req.finding_id,
        "requested_action": req.requested_action,
        "risk_level": req.risk_level,
        "status": req.status.value,
        "requested_by": req.requested_by,
        "approved_by": req.approved_by,
        "head_sha": req.head_sha,
        "expires_at": req.expires_at.isoformat(),
        "resolved_at": req.resolved_at.isoformat() if req.resolved_at else None,
        "reason": req.reason,
        "created_at": req.created_at.isoformat(),
    }


@router.post("/{approval_id}/approve", response_model=dict[str, Any])
def approve_request(
    approval_id: str,
    payload: ApprovePayload,
    x_user_id: str = Header(default="human-reviewer-1"),
    x_user_role: str = Header(default="REVIEWER"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = ApprovalService(db)
    try:
        req = service.approve_request(
            approval_id=approval_id,
            approver_principal_id=x_user_id,
            approver_role=x_user_role,
            is_ai_agent=False,
            comment=payload.comment,
        )

        # Transition associated publication from APPROVAL_REQUIRED to PENDING and trigger publication
        from sqlalchemy import select

        from app.models.github_publication import GitHubReviewPublication, PublicationStatus

        pub = db.scalar(
            select(GitHubReviewPublication).where(
                GitHubReviewPublication.review_job_id == req.review_job_id,
                GitHubReviewPublication.head_sha == req.head_sha,
                GitHubReviewPublication.status == PublicationStatus.APPROVAL_REQUIRED,
            )
        )
        if pub:
            pub.status = PublicationStatus.PENDING
            db.commit()
            try:
                from app.workers.tasks import publish_review_sync
                publish_review_sync(publication_id=pub.id, db=db)
            except Exception:
                pass

        return {
            "status": "success",
            "approval_id": req.id,
            "approval_status": req.status.value,
            "approved_by": req.approved_by,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{approval_id}/reject", response_model=dict[str, Any])
def reject_request(
    approval_id: str,
    payload: RejectPayload,
    x_user_id: str = Header(default="human-reviewer-1"),
    x_user_role: str = Header(default="REVIEWER"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = ApprovalService(db)
    try:
        req = service.reject_request(
            approval_id=approval_id,
            approver_principal_id=x_user_id,
            approver_role=x_user_role,
            is_ai_agent=False,
            reason=payload.reason,
        )

        from sqlalchemy import select

        from app.models.github_publication import GitHubReviewPublication, PublicationStatus

        pub = db.scalar(
            select(GitHubReviewPublication).where(
                GitHubReviewPublication.review_job_id == req.review_job_id,
                GitHubReviewPublication.head_sha == req.head_sha,
                GitHubReviewPublication.status == PublicationStatus.APPROVAL_REQUIRED,
            )
        )
        if pub:
            pub.status = PublicationStatus.FAILED
            pub.error_message = f"Publication rejected by reviewer: {payload.reason}"
            db.commit()

        return {
            "status": "success",
            "approval_id": req.id,
            "approval_status": req.status.value,
            "reason": req.reason,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
