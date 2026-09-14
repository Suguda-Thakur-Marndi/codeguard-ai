"""Domain service handling payment processing and refunds."""

from typing import Optional
from auth.auth_service import AuthService, SecurityContext
from models.payment import Payment, PaymentStatus
from repositories.payment_repository import PaymentRepository


class PaymentService:
    """Core domain service for executing payments and customer refunds."""

    def __init__(
        self,
        repository: PaymentRepository,
        auth_service: AuthService,
    ):
        self.repository = repository
        self.auth_service = auth_service

    def process_payment(self, payment: Payment) -> bool:
        """Process an incoming customer charge."""
        payment.status = PaymentStatus.SETTLED
        self.repository.save(payment)
        return True

    def refund(
        self,
        payment_id: str,
        amount: float,
        context: SecurityContext,
        reason: Optional[str] = None,
    ) -> bool:
        """Issue full or partial refund on settled transaction."""
        # Check operator authorization
        is_authorized = self.auth_service.verify_refund_permission(context)
        if not is_authorized:
            raise PermissionError("Operator unauthorized to issue refund")

        payment = self.repository.find_by_id(payment_id)
        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found")

        if payment.status != PaymentStatus.SETTLED:
            raise ValueError(f"Cannot refund payment in state: {payment.status}")

        if amount > payment.amount:
            raise ValueError("Refund amount exceeds original transaction total")

        payment.status = PaymentStatus.REFUNDED
        payment.reason = reason
        self.repository.save(payment)
        self.auth_service.audit_action("refund_issued", context.user_id, payment_id)
        return True
