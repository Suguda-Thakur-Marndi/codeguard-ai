"""Persistence repository for payments."""

from typing import Dict, Optional
from models.payment import Payment, PaymentStatus


class PaymentRepository:
    """Database adapter for payments storage."""

    def __init__(self):
        self._storage: Dict[str, Payment] = {}

    def find_by_id(self, payment_id: str) -> Optional[Payment]:
        """Fetch payment by unique transaction ID."""
        return self._storage.get(payment_id)

    def save(self, payment: Payment) -> Payment:
        """Persist or update payment entity."""
        self._storage[payment.id] = payment
        return payment

    def update_status(self, payment_id: str, status: PaymentStatus) -> bool:
        """Mutate payment state transition."""
        payment = self.find_by_id(payment_id)
        if not payment:
            return False
        payment.status = status
        return True
