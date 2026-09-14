"""Publication REST API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user_or_bypass
from app.db.session import get_db
from app.models.github_publication import GitHubReviewPublication, PublicationStatus
from app.services.publication_service import PublicationService
from app.workers.tasks import publish_review_sync

router = APIRouter(tags=["publications"])


class PublishRequestPayload(BaseModel):
    action: str = "COMMENT"


@router.get("/review-jobs/{review_job_id}/publication", response_model=dict[str, Any])
def get_job_publication(
    review_job_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_or_bypass),
) -> dict[str, Any]:
    pub = db.scalar(
        select(GitHubReviewPublication)
        .where(GitHubReviewPublication.review_job_id == review_job_id)
        .order_by(GitHubReviewPublication.created_at.desc())
    )
    if not pub:
        return {"publication": None}

    comments = [
        {
            "id": c.id,
            "github_comment_id": c.github_comment_id,
            "file_path": c.file_path,
            "line_number": c.line_number,
            "side": c.side,
            "status": c.status,
        }
        for c in pub.comments
    ]

    return {
        "publication": {
            "id": pub.id,
            "review_job_id": pub.review_job_id,
            "repository_id": pub.repository_id,
            "pull_request_id": pub.pull_request_id,
            "head_sha": pub.head_sha,
            "github_review_id": pub.github_review_id,
            "event": pub.event,
            "status": pub.status.value,
            "comment_count": pub.comment_count,
            "published_at": pub.published_at.isoformat() if pub.published_at else None,
            "error_message": pub.error_message,
            "comments": comments,
        }
    }


@router.post("/review-jobs/{review_job_id}/publish", response_model=dict[str, Any])
def publish_job_review(
    review_job_id: str,
    payload: PublishRequestPayload = PublishRequestPayload(),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_or_bypass),
) -> dict[str, Any]:
    service = PublicationService(db)
    try:
        pub, approval_req = service.prepare_publication(
            review_job_id=review_job_id,
            action=payload.action,
        )

        if pub.status == PublicationStatus.APPROVAL_REQUIRED:
            return {
                "status": "APPROVAL_REQUIRED",
                "publication_id": pub.id,
                "approval_id": approval_req.id if approval_req else None,
                "message": "Action requires human approval before publishing.",
            }

        if pub.status == PublicationStatus.PUBLISHED:
            return {
                "status": "ALREADY_PUBLISHED",
                "publication_id": pub.id,
                "github_review_id": pub.github_review_id,
                "message": "Review is already published (idempotent).",
            }

        # Ready to publish: run sync or dispatch worker
        res = publish_review_sync(publication_id=pub.id, db=db)
        return {
            "status": res["publication_status"],
            "publication_id": pub.id,
            "github_review_id": res.get("github_review_id"),
        }

    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
