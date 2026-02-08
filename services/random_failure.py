"""
Random Failure Injection System
Each demo session picks a random failure mode — not hardcoded.
"""

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class FailureMode:
    """A specific failure that can be injected."""
    id: str
    service: str
    error_type: str
    error_code: str
    message: str
    symptoms: List[str]
    root_cause: str
    fix_description: str
    fix_code: Dict[str, str]  # filename -> fixed code
    buggy_code: Dict[str, str]  # filename -> buggy code


# Define multiple failure modes
FAILURE_MODES = [
    FailureMode(
        id="billing_currency_missing",
        service="billing",
        error_type="schema_mismatch",
        error_code="BILLING_400",
        message="Missing required field: currency",
        symptoms=[
            "POST /api/create-order 400 - validation failed: missing field 'currency'",
            "Stripe: PaymentIntent requires currency - received null",
            "High 400 error rate on /api/create-order"
        ],
        root_cause="Backend added mandatory currency validation. Frontend was deployed earlier and did not include currency in the request payload.",
        fix_description="Add currency: 'INR' to frontend checkout.ts request body",
        buggy_code={
            "checkout.ts": '''// checkout.ts - Next.js client snippet

async function createOrder(paymentIntentId: string, amount: number) {
  const res = await fetch("/api/create-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paymentIntentId,
      amount
    })
  });

  if (!res.ok) {
    throw new Error("Order failed");
  }

  return await res.json();
}

export default createOrder;
'''
        },
        fix_code={
            "checkout.ts": '''// checkout.ts - Next.js client snippet

async function createOrder(paymentIntentId: string, amount: number) {
  const res = await fetch("/api/create-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paymentIntentId,
      amount,
      currency: "INR"
    })
  });

  if (!res.ok) {
    throw new Error("Order failed");
  }

  return await res.json();
}

export default createOrder;
'''
        }
    ),
    FailureMode(
        id="ordering_idempotency_missing",
        service="ordering",
        error_type="duplicate_request",
        error_code="ORDER_409",
        message="Duplicate order detected - idempotency key missing",
        symptoms=[
            "POST /api/create-order 409 - Duplicate order",
            "OrderService: Idempotency violation - same order created twice",
            "Multiple charges for single checkout"
        ],
        root_cause="Frontend not sending idempotency key, causing duplicate orders on retry.",
        fix_description="Add idempotencyKey to frontend checkout.ts request body",
        buggy_code={
            "checkout.ts": '''// checkout.ts - Next.js client snippet

async function createOrder(paymentIntentId: string, amount: number) {
  const res = await fetch("/api/create-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paymentIntentId,
      amount,
      currency: "INR"
    })
  });

  if (!res.ok) {
    throw new Error("Order failed");
  }

  return await res.json();
}

export default createOrder;
'''
        },
        fix_code={
            "checkout.ts": '''// checkout.ts - Next.js client snippet
import { v4 as uuidv4 } from 'uuid';

async function createOrder(paymentIntentId: string, amount: number) {
  const idempotencyKey = uuidv4();
  
  const res = await fetch("/api/create-order", {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({
      paymentIntentId,
      amount,
      currency: "INR"
    })
  });

  if (!res.ok) {
    throw new Error("Order failed");
  }

  return await res.json();
}

export default createOrder;
'''
        }
    ),
    FailureMode(
        id="frontend_timeout_missing",
        service="frontend",
        error_type="timeout_handling",
        error_code="FE_TIMEOUT",
        message="Request timeout - no timeout configured",
        symptoms=[
            "Frontend hanging on slow network",
            "User clicking checkout multiple times",
            "AbortController not configured"
        ],
        root_cause="Frontend fetch has no timeout, causing UI to hang indefinitely on slow connections.",
        fix_description="Add AbortController with 30s timeout to checkout.ts",
        buggy_code={
            "checkout.ts": '''// checkout.ts - Next.js client snippet

async function createOrder(paymentIntentId: string, amount: number) {
  const res = await fetch("/api/create-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paymentIntentId,
      amount,
      currency: "INR"
    })
  });

  if (!res.ok) {
    throw new Error("Order failed");
  }

  return await res.json();
}

export default createOrder;
'''
        },
        fix_code={
            "checkout.ts": '''// checkout.ts - Next.js client snippet

async function createOrder(paymentIntentId: string, amount: number) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);
  
  try {
    const res = await fetch("/api/create-order", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        paymentIntentId,
        amount,
        currency: "INR"
      }),
      signal: controller.signal
    });

    if (!res.ok) {
      throw new Error("Order failed");
    }

    return await res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export default createOrder;
'''
        }
    ),
    FailureMode(
        id="billing_amount_type",
        service="billing",
        error_type="type_mismatch",
        error_code="BILLING_422",
        message="Invalid amount type - expected integer (cents), received float",
        symptoms=[
            "POST /api/create-order 422 - Invalid amount format",
            "Stripe: Amount must be an integer in smallest currency unit",
            "Payment processing failed: type error"
        ],
        root_cause="Frontend sending amount as float (dollars) instead of integer (cents/paise).",
        fix_description="Convert amount to integer cents before sending",
        buggy_code={
            "checkout.ts": '''// checkout.ts - Next.js client snippet

async function createOrder(paymentIntentId: string, amount: number) {
  const res = await fetch("/api/create-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paymentIntentId,
      amount,  // BUG: sending as float
      currency: "INR"
    })
  });

  if (!res.ok) {
    throw new Error("Order failed");
  }

  return await res.json();
}

export default createOrder;
'''
        },
        fix_code={
            "checkout.ts": '''// checkout.ts - Next.js client snippet

async function createOrder(paymentIntentId: string, amount: number) {
  // Convert to smallest currency unit (paise for INR)
  const amountInPaise = Math.round(amount * 100);
  
  const res = await fetch("/api/create-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paymentIntentId,
      amount: amountInPaise,
      currency: "INR"
    })
  });

  if (!res.ok) {
    throw new Error("Order failed");
  }

  return await res.json();
}

export default createOrder;
'''
        }
    ),
]


class FailureInjector:
    """Manages random failure injection for demos."""
    
    def __init__(self):
        self.current_failure: Optional[FailureMode] = None
    
    def select_random_failure(self) -> FailureMode:
        """Select a random failure mode for this demo session."""
        self.current_failure = random.choice(FAILURE_MODES)
        return self.current_failure
    
    def get_current_failure(self) -> Optional[FailureMode]:
        """Get the currently active failure."""
        return self.current_failure
    
    def inject_buggy_code(self, demo_frontend_path: str = "demo_frontend"):
        """Write the buggy code to the demo frontend."""
        if not self.current_failure:
            self.select_random_failure()
        
        path = Path(demo_frontend_path)
        path.mkdir(exist_ok=True)
        
        for filename, content in self.current_failure.buggy_code.items():
            with open(path / filename, "w") as f:
                f.write(content)
    
    def get_fixed_code(self) -> Dict[str, str]:
        """Get the fixed code for current failure."""
        if self.current_failure:
            return self.current_failure.fix_code
        return {}
    
    def generate_logs(self, count: int = 40) -> List[str]:
        """Generate realistic logs for the current failure."""
        if not self.current_failure:
            self.select_random_failure()
        
        logs = []
        failure = self.current_failure
        
        for i in range(count):
            ts = f"2026-02-08T14:{i % 60:02d}:{random.randint(0, 59):02d}"
            
            # Mix in failure symptoms
            if i % 4 == 0 and failure.symptoms:
                symptom = random.choice(failure.symptoms)
                logs.append(f"{ts} ERROR [{failure.service}] {symptom}")
            elif i % 7 == 0:
                logs.append(f"{ts} WARN [ordering] High latency detected: 850ms")
            elif i % 11 == 0:
                logs.append(f"{ts} WARN [database] Connection pool at 80% capacity")
            else:
                service = random.choice(["frontend", "gateway", "auth", "cache"])
                logs.append(f"{ts} INFO [{service}] Request processed successfully")
        
        return logs


# Singleton instance
_injector: Optional[FailureInjector] = None

def get_failure_injector() -> FailureInjector:
    global _injector
    if _injector is None:
        _injector = FailureInjector()
    return _injector

def reset_failure_injector():
    """Reset the injector for a new demo session."""
    global _injector
    _injector = FailureInjector()
    return _injector
