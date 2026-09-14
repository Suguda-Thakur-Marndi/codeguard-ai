"""Payment domain model."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


@dataclass
class Payment:
    """Core payment entity representing customer transaction."""

    id: str
    amount: float
    currency: str
    customer_id: str
    status: PaymentStatus
    created_at: datetime
    refund_id: Optional[str] = None
    reason: Optional[str] = None
