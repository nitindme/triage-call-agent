"""
Ordering Service Simulator
Simulates order creation, inventory locking, and order state management.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from .failure_injector import get_injector
from .logger import log, LogLevel


@dataclass
class OrderItem:
    sku: str
    quantity: int
    price: int


@dataclass
class Order:
    id: str
    payment_intent_id: str
    items: List[OrderItem]
    status: str  # pending, confirmed, failed, cancelled
    created_at: datetime = field(default_factory=datetime.now)


class OrderingService:
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.inventory_locks: Dict[str, str] = {}  # sku -> order_id

    def create_order(
        self,
        payment_intent_id: str,
        items: List[Dict[str, Any]],
        currency: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        trace_id = trace_id or str(uuid.uuid4())[:8]
        injector = get_injector()

        # Check for failure injection
        failure = injector.trigger_failure("ordering", trace_id)
        if failure:
            log(
                service="ordering",
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
        if not payment_intent_id:
            log(
                service="ordering",
                level=LogLevel.ERROR,
                message="Missing required field: payment_intent_id",
                error_code="ORDER_400",
                trace_id=trace_id
            )
            return {
                "success": False,
                "error_code": "ORDER_400",
                "message": "Missing required field: payment_intent_id",
                "trace_id": trace_id
            }

        # Simulate inventory lock
        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        order_items = []
        for item in items:
            sku = item.get("sku", f"SKU{uuid.uuid4().hex[:4].upper()}")
            # Check inventory lock
            if sku in self.inventory_locks:
                log(
                    service="ordering",
                    level=LogLevel.WARN,
                    message=f"Inventory lock contention for {sku}",
                    trace_id=trace_id
                )
            self.inventory_locks[sku] = order_id
            order_items.append(OrderItem(
                sku=sku,
                quantity=item.get("quantity", 1),
                price=item.get("price", 0)
            ))

        order = Order(
            id=order_id,
            payment_intent_id=payment_intent_id,
            items=order_items,
            status="pending"
        )
        self.orders[order_id] = order

        log(
            service="ordering",
            level=LogLevel.INFO,
            message=f"Order created: {order_id}",
            trace_id=trace_id
        )

        return {
            "success": True,
            "order_id": order_id,
            "status": "pending",
            "trace_id": trace_id
        }

    def confirm_order(self, order_id: str, trace_id: Optional[str] = None) -> Dict[str, Any]:
        trace_id = trace_id or str(uuid.uuid4())[:8]

        if order_id not in self.orders:
            log(
                service="ordering",
                level=LogLevel.ERROR,
                message=f"Order not found: {order_id}",
                error_code="ORDER_404",
                trace_id=trace_id
            )
            return {
                "success": False,
                "error_code": "ORDER_404",
                "message": "Order not found",
                "trace_id": trace_id
            }

        order = self.orders[order_id]
        order.status = "confirmed"

        log(
            service="ordering",
            level=LogLevel.INFO,
            message=f"Order confirmed: {order_id}",
            trace_id=trace_id
        )

        return {
            "success": True,
            "order_id": order_id,
            "status": "confirmed",
            "trace_id": trace_id
        }


# Singleton
_ordering_service: Optional[OrderingService] = None


def get_ordering_service() -> OrderingService:
    global _ordering_service
    if _ordering_service is None:
        _ordering_service = OrderingService()
    return _ordering_service
