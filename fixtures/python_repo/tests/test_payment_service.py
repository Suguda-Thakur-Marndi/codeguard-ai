"""Unit tests for payment and refund functionality."""

from datetime import datetime
from auth.auth_service import AuthService, SecurityContext
from models.payment import Payment, PaymentStatus
from repositories.payment_repository import PaymentRepository
from services.payment_service import PaymentService


def test_payment_service_refund_success():
    repo = PaymentRepository()
    auth = AuthService()
    service = PaymentService(repo, auth)

    payment = Payment(
        id="pay_100",
        amount=50.0,
        currency="USD",
        customer_id="cust_abc",
        status=PaymentStatus.SETTLED,
        created_at=datetime.utcnow(),
    )
    repo.save(payment)

    ctx = SecurityContext("admin_user", ["finance:refund"])
    res = service.refund("pay_100", 25.0, ctx, reason="Partial chargeback")
    assert res is True
    assert payment.status == PaymentStatus.REFUNDED
