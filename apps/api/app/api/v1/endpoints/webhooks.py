"""GitHub Webhook ingestion endpoint."""

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.exceptions import WebhookVerificationError
from app.db.session import get_db
from app.schemas.webhook import WebhookResponse
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post(
    "/github",
    response_model=WebhookResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest GitHub Webhook",
    description="Validates HMAC-SHA256 signature, parses event, registers PR and queues review job asynchronously.",
)
async def handle_github_webhook(
    request: Request,
    response: Response,
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
    db: Session = Depends(get_db),
) -> WebhookResponse:
    """Fast-path webhook handler with signature verification."""
    # 1. Read raw body for exact HMAC signature validation
    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty webhook request body",
        )

    webhook_service = WebhookService(db)

    # 2. Enforce cryptographic signature verification
    try:
        webhook_service.verify_payload(raw_body, x_hub_signature_256)
    except WebhookVerificationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    # 3. Parse JSON payload
    try:
        payload_data = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON in webhook body: {str(err)}",
        ) from err

    event_type = x_github_event or "unknown"
    delivery_id = x_github_delivery or "unknown"

    # 4. Ingest event and dispatch background job
    result = webhook_service.process_webhook(event_type, delivery_id, payload_data)

    # Adjust HTTP status code based on result: 200 for ignored/ping, 202 for queued
    if result.status == "accepted":
        response.status_code = status.HTTP_202_ACCEPTED
    else:
        response.status_code = status.HTTP_200_OK

    return result
