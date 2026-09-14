"""API HTTP Controller handling refund requests."""

from typing import Any, Dict
from auth.auth_service import SecurityContext
from services.payment_service import PaymentService


class RefundController:
    """REST endpoint handler for issuing refunds."""

    def __init__(self, payment_service: PaymentService):
        self.payment_service = payment_service

    def handle_refund(self, payload: Dict[str, Any], operator_context: SecurityContext) -> Dict[str, Any]:
        """Dispatch refund request to payment service."""
        payment_id = payload.get("payment_id", "")
        amount = float(payload.get("amount", 0.0))
        reason = payload.get("reason", "Customer requested refund")

        success = self.payment_service.refund(
            payment_id=payment_id,
            amount=amount,
            context=operator_context,
            reason=reason,
        )

        return {
            "status": "success" if success else "failed",
            "payment_id": payment_id,
            "refunded_amount": amount,
        }
