"""
Billing Service Simulator
Simulates a real billing service with Stripe-like operations.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from .failure_injector import get_injector
from .logger import log, LogLevel


@dataclass
class PaymentIntent:
    id: str
    amount: int
    currency: Optional[str]
    status: str  # requires_payment_method, succeeded, failed
    created_at: datetime = field(default_factory=datetime.now)


class BillingService:
    def __init__(self):
        self.payment_intents: Dict[str, PaymentIntent] = {}

    def create_payment_intent(
        self,
        amount: int,
        currency: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        trace_id = trace_id or str(uuid.uuid4())[:8]
        injector = get_injector()

        # Check for failure injection
        failure = injector.trigger_failure("billing", trace_id)
        if failure:
            log(
                service="billing",
                level=LogLevel.ERROR,
                message=failure.failure.message,
                error_code=failure.failure.error_code,
                trace_id=trace_id
            )
            return {
                "success": False,
                "error_code": failure.failure.error_code,
                "message": failure.failure.message,
                "trace_id": trace_id
            }

        # Validate required fields
        if not currency:
            log(
                service="billing",
                level=LogLevel.ERROR,
                message="Missing required field: currency",
                error_code="BILLING_400",
                trace_id=trace_id
            )
            return {
                "success": False,
                "error_code": "BILLING_400",
                "message": "Missing required field: currency",
                "trace_id": trace_id
            }

        # Create payment intent
        intent_id = f"pi_{uuid.uuid4().hex[:16]}"
        intent = PaymentIntent(
            id=intent_id,
            amount=amount,
            currency=currency,
            status="requires_payment_method"
        )
        self.payment_intents[intent_id] = intent

        log(
            service="billing",
            level=LogLevel.INFO,
            message=f"PaymentIntent created: {intent_id}",
            trace_id=trace_id
        )

        return {
            "success": True,
            "payment_intent_id": intent_id,
            "amount": amount,
            "currency": currency,
            "status": "requires_payment_method",
            "trace_id": trace_id
        }

    def confirm_payment(self, payment_intent_id: str, trace_id: Optional[str] = None) -> Dict[str, Any]:
        trace_id = trace_id or str(uuid.uuid4())[:8]

        if payment_intent_id not in self.payment_intents:
            log(
                service="billing",
                level=LogLevel.ERROR,
                message=f"PaymentIntent not found: {payment_intent_id}",
                error_code="BILLING_404",
                trace_id=trace_id
            )
            return {
                "success": False,
                "error_code": "BILLING_404",
                "message": "PaymentIntent not found",
                "trace_id": trace_id
            }

        intent = self.payment_intents[payment_intent_id]
        intent.status = "succeeded"

        log(
            service="billing",
            level=LogLevel.INFO,
            message=f"PaymentIntent confirmed: {payment_intent_id}",
            trace_id=trace_id
        )

        return {
            "success": True,
            "payment_intent_id": payment_intent_id,
            "status": "succeeded",
            "trace_id": trace_id
        }


# Singleton
_billing_service: Optional[BillingService] = None


def get_billing_service() -> BillingService:
    global _billing_service
    if _billing_service is None:
        _billing_service = BillingService()
    return _billing_service
