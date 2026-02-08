import random
import time
from datetime import datetime


def generate_logs(ticket_id: str, lines: int = 40):
    """Yield simulated logs (timestamped) relevant to an ordering checkout issue."""
    now = int(time.time())
    for i in range(lines):
        ts = datetime.fromtimestamp(now - (lines - i)).isoformat()
        level = random.choices(["INFO", "WARN", "ERROR"], [0.6, 0.25, 0.15])[0]
        if i % 7 == 0:
            msg = f"POST /api/create-order 400 - validation failed: missing field 'currency'"
        elif i % 11 == 0:
            msg = "Stripe: PaymentIntent requires currency - received null"
        elif i % 13 == 0:
            msg = "OrderService: inventory lock failed for sku=SKU1234"
        else:
            msg = random.choice([
                "GET /api/catalog 200",
                "Worker: reconciler ran successfully",
                "Auth: token validated",
            ])
        yield f"{ts} {level} [{ticket_id}] {msg}\n"
