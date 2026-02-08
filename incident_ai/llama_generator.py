"""
Dynamic Incident Generator
Generates diverse incidents across ALL services - not just frontend.
Supports LLaMA via Ollama (local) or Groq (cloud) for truly dynamic generation.
"""

import os
import json
import random
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass
class DynamicIncident:
    """A dynamically generated incident."""
    service: str
    error_code: str
    error_message: str
    symptoms: list
    root_cause: str
    fix_description: str
    buggy_code: str
    fixed_code: str
    file_name: str
    agent_owner: str


# Comprehensive incidents across ALL services
FALLBACK_INCIDENTS = [
    # ========== BILLING SERVICE ==========
    {
        "service": "billing",
        "error_code": "BILLING_400",
        "error_message": "Missing required field: currency",
        "symptoms": ["POST /api/billing/charge 400", "Stripe: PaymentIntent requires currency"],
        "root_cause": "Billing service not receiving currency field after API contract change",
        "fix_description": "Add currency parameter to charge creation",
        "file_name": "services/billing.py",
        "agent_owner": "BillingAgent",
        "buggy_code": '''# services/billing.py
class BillingService:
    def create_charge(self, payment_id: str, amount: float):
        """Create a charge via Stripe."""
        # Bug: currency field missing
        return stripe.PaymentIntent.create(
            amount=int(amount * 100),
            payment_method=payment_id,
            confirm=True
        )''',
        "fixed_code": '''# services/billing.py
class BillingService:
    def create_charge(self, payment_id: str, amount: float, currency: str = "usd"):
        """Create a charge via Stripe."""
        return stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=currency,
            payment_method=payment_id,
            confirm=True
        )'''
    },
    {
        "service": "billing",
        "error_code": "BILLING_503",
        "error_message": "Payment gateway timeout - no retry logic",
        "symptoms": ["POST /api/billing/charge 503", "Stripe API timeout", "Intermittent payment failures"],
        "root_cause": "Billing service lacks retry logic for transient Stripe failures",
        "fix_description": "Add exponential backoff retry for API calls",
        "file_name": "services/billing.py",
        "agent_owner": "BillingAgent",
        "buggy_code": '''# services/billing.py
class BillingService:
    def charge_customer(self, customer_id: str, amount: int):
        # Bug: No retry on transient failure
        return stripe.Charge.create(
            customer=customer_id,
            amount=amount,
            currency="usd"
        )''',
        "fixed_code": '''# services/billing.py
import time

class BillingService:
    def charge_customer(self, customer_id: str, amount: int, retries: int = 3):
        for attempt in range(retries):
            try:
                return stripe.Charge.create(
                    customer=customer_id,
                    amount=amount,
                    currency="usd"
                )
            except stripe.error.APIConnectionError:
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)'''
    },

    # ========== ORDERING SERVICE ==========
    {
        "service": "ordering",
        "error_code": "ORDER_409",
        "error_message": "Duplicate order - idempotency key missing",
        "symptoms": ["POST /api/orders 409", "Duplicate orders in DB", "Customer charged twice"],
        "root_cause": "Order service lacks idempotency validation, retries create duplicates",
        "fix_description": "Add idempotency key check before order creation",
        "file_name": "services/ordering.py",
        "agent_owner": "OrderingAgent",
        "buggy_code": '''# services/ordering.py
class OrderService:
    def create_order(self, user_id: str, items: list, payment_id: str):
        # Bug: No idempotency - retries create duplicates
        order = Order(user_id=user_id, items=items, payment_id=payment_id)
        db.session.add(order)
        db.session.commit()
        return order''',
        "fixed_code": '''# services/ordering.py
class OrderService:
    def create_order(self, user_id: str, items: list, payment_id: str, idempotency_key: str):
        # Check for existing order
        existing = Order.query.filter_by(idempotency_key=idempotency_key).first()
        if existing:
            return existing
        
        order = Order(user_id=user_id, items=items, payment_id=payment_id,
                      idempotency_key=idempotency_key)
        db.session.add(order)
        db.session.commit()
        return order'''
    },
    {
        "service": "ordering",
        "error_code": "ORDER_500",
        "error_message": "Race condition in inventory reservation",
        "symptoms": ["Oversold items", "Negative inventory", "Fulfillment failures"],
        "root_cause": "Inventory check and decrement not atomic, race condition under load",
        "fix_description": "Use atomic database update with row locking",
        "file_name": "services/ordering.py",
        "agent_owner": "OrderingAgent",
        "buggy_code": '''# services/ordering.py
class OrderService:
    def reserve_inventory(self, product_id: str, qty: int):
        # Bug: Race condition - check and update not atomic
        product = Product.query.get(product_id)
        if product.stock >= qty:
            product.stock -= qty
            db.session.commit()
            return True
        return False''',
        "fixed_code": '''# services/ordering.py
class OrderService:
    def reserve_inventory(self, product_id: str, qty: int):
        # Atomic update with WHERE clause
        result = db.session.execute(
            text("UPDATE products SET stock = stock - :qty WHERE id = :pid AND stock >= :qty"),
            {"qty": qty, "pid": product_id}
        )
        db.session.commit()
        return result.rowcount > 0'''
    },

    # ========== DATABASE / SRE ==========
    {
        "service": "database",
        "error_code": "DB_POOL_EXHAUSTED",
        "error_message": "Connection pool exhausted",
        "symptoms": ["All services timing out", "QueuePool limit reached", "New connections failing"],
        "root_cause": "Database pool too small for traffic spike, connections not released",
        "fix_description": "Increase pool size and add connection timeout",
        "file_name": "config/database.py",
        "agent_owner": "SREAgent",
        "buggy_code": '''# config/database.py
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=5,      # Too small!
    max_overflow=0
)''',
        "fixed_code": '''# config/database.py
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True
)'''
    },
    {
        "service": "database",
        "error_code": "DB_DEADLOCK",
        "error_message": "Deadlock detected in transaction",
        "symptoms": ["Transaction aborted", "Lock wait timeout", "Intermittent 500s"],
        "root_cause": "Transactions acquiring locks in inconsistent order causing deadlock",
        "fix_description": "Ensure consistent lock ordering across transactions",
        "file_name": "services/inventory.py",
        "agent_owner": "SREAgent",
        "buggy_code": '''# services/inventory.py
def transfer_stock(from_wh: str, to_wh: str, qty: int):
    # Bug: Inconsistent lock order causes deadlock
    with db.session.begin():
        src = Warehouse.query.filter_by(id=from_wh).with_for_update().first()
        dst = Warehouse.query.filter_by(id=to_wh).with_for_update().first()
        src.stock -= qty
        dst.stock += qty''',
        "fixed_code": '''# services/inventory.py
def transfer_stock(from_wh: str, to_wh: str, qty: int):
    # Fix: Always lock in sorted order
    ids = sorted([from_wh, to_wh])
    with db.session.begin():
        warehouses = {w.id: w for w in 
            Warehouse.query.filter(Warehouse.id.in_(ids))
            .order_by(Warehouse.id).with_for_update().all()}
        warehouses[from_wh].stock -= qty
        warehouses[to_wh].stock += qty'''
    },

    # ========== AUTHENTICATION ==========
    {
        "service": "auth",
        "error_code": "AUTH_401",
        "error_message": "JWT validation failed after key rotation",
        "symptoms": ["Users logged out", "401 on all API calls", "Token refresh failing"],
        "root_cause": "JWT secret rotated but old tokens rejected instead of grace period",
        "fix_description": "Accept both old and new keys during rotation",
        "file_name": "middleware/auth.py",
        "agent_owner": "SREAgent",
        "buggy_code": '''# middleware/auth.py
import jwt

def verify_token(token: str) -> dict:
    # Bug: Only checks current secret
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid token")''',
        "fixed_code": '''# middleware/auth.py
import jwt

def verify_token(token: str) -> dict:
    # Try current key, then previous for grace period
    for secret in [SECRET_KEY, PREVIOUS_SECRET_KEY]:
        if not secret:
            continue
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            continue
    raise UnauthorizedError("Invalid token")'''
    },

    # ========== CACHE / REDIS ==========
    {
        "service": "cache",
        "error_code": "CACHE_STAMPEDE",
        "error_message": "Cache stampede causing database overload",
        "symptoms": ["Database CPU 100%", "Cache miss rate spike", "Latency spike after expiry"],
        "root_cause": "Popular cache key expires, all requests hit database simultaneously",
        "fix_description": "Add stampede protection with distributed lock",
        "file_name": "services/cache.py",
        "agent_owner": "SREAgent",
        "buggy_code": '''# services/cache.py
class CacheService:
    def get_or_set(self, key: str, fetch_fn, ttl: int = 300):
        # Bug: No stampede protection
        value = redis.get(key)
        if value is None:
            value = fetch_fn()  # All requests hit DB!
            redis.setex(key, ttl, json.dumps(value))
        return json.loads(value) if value else None''',
        "fixed_code": '''# services/cache.py
class CacheService:
    def get_or_set(self, key: str, fetch_fn, ttl: int = 300):
        value = redis.get(key)
        if value is None:
            # Use distributed lock to prevent stampede
            with redis.lock(f"lock:{key}", timeout=10):
                value = redis.get(key)  # Double-check after lock
                if value is None:
                    value = fetch_fn()
                    redis.setex(key, ttl, json.dumps(value))
        return json.loads(value) if value else None'''
    },

    # ========== KUBERNETES / INFRA ==========
    {
        "service": "kubernetes",
        "error_code": "K8S_OOM_KILLED",
        "error_message": "Pod OOMKilled - memory limit too low",
        "symptoms": ["Pods restarting", "Exit code 137", "Memory spike before crash"],
        "root_cause": "Memory limit too low for traffic spike, OOM killer terminates pod",
        "fix_description": "Increase memory limits and add proper requests",
        "file_name": "k8s/deployment.yaml",
        "agent_owner": "SREAgent",
        "buggy_code": '''# k8s/deployment.yaml
spec:
  containers:
  - name: api
    resources:
      limits:
        memory: "128Mi"  # Way too low!
        cpu: "100m"''',
        "fixed_code": '''# k8s/deployment.yaml
spec:
  containers:
  - name: api
    resources:
      requests:
        memory: "256Mi"
        cpu: "100m"
      limits:
        memory: "512Mi"
        cpu: "500m"'''
    },

    # ========== MESSAGE QUEUE ==========
    {
        "service": "queue",
        "error_code": "QUEUE_MSG_LOST",
        "error_message": "Messages lost during processing",
        "symptoms": ["Orders missing", "Events not processed", "State inconsistency"],
        "root_cause": "Message ACK'd before processing complete, lost on worker crash",
        "fix_description": "Only ACK after successful processing",
        "file_name": "workers/order_processor.py",
        "agent_owner": "OrderingAgent",
        "buggy_code": '''# workers/order_processor.py
def process_order(ch, method, props, body):
    # Bug: ACK before processing
    ch.basic_ack(delivery_tag=method.delivery_tag)
    order = json.loads(body)
    fulfill_order(order)  # If this fails, message is lost!''',
        "fixed_code": '''# workers/order_processor.py
def process_order(ch, method, props, body):
    try:
        order = json.loads(body)
        fulfill_order(order)
        # Only ACK after success
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        logger.error(f"Processing failed: {e}")'''
    },

    # ========== API GATEWAY ==========
    {
        "service": "gateway",
        "error_code": "GW_CIRCUIT_OPEN",
        "error_message": "Circuit breaker open - no fallback",
        "symptoms": ["503 Service Unavailable", "Cascading failures", "All requests failing"],
        "root_cause": "Circuit breaker opens but no fallback, blocking all traffic",
        "fix_description": "Add graceful fallback when circuit is open",
        "file_name": "gateway/circuit_breaker.py",
        "agent_owner": "SREAgent",
        "buggy_code": '''# gateway/circuit_breaker.py
class CircuitBreaker:
    def call(self, fn):
        if self.state == "open":
            raise ServiceUnavailable("Circuit open")  # No fallback!
        try:
            return fn()
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = "open"
            raise''',
        "fixed_code": '''# gateway/circuit_breaker.py
class CircuitBreaker:
    def call(self, fn, fallback=None):
        if self.state == "open":
            if time.time() - self.opened_at > self.reset_timeout:
                self.state = "half-open"
            elif fallback:
                return fallback()
            else:
                raise ServiceUnavailable("Circuit open")
        try:
            result = fn()
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            return result
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = "open"
                self.opened_at = time.time()
            raise'''
    },

    # ========== FRONTEND (keeping some) ==========
    {
        "service": "frontend",
        "error_code": "FE_MEMORY_LEAK",
        "error_message": "Memory leak in event listeners",
        "symptoms": ["Browser tab crashing", "Increasing memory usage", "Page becomes unresponsive"],
        "root_cause": "Event listeners not cleaned up on component unmount",
        "fix_description": "Add cleanup in useEffect return",
        "file_name": "frontend/Checkout.tsx",
        "agent_owner": "FrontendAgent",
        "buggy_code": '''// frontend/Checkout.tsx
function Checkout() {
  useEffect(() => {
    // Bug: No cleanup - listeners accumulate
    window.addEventListener('resize', handleResize);
    socket.on('update', handleUpdate);
  }, []);
  
  return <div>...</div>;
}''',
        "fixed_code": '''// frontend/Checkout.tsx
function Checkout() {
  useEffect(() => {
    window.addEventListener('resize', handleResize);
    socket.on('update', handleUpdate);
    
    // Cleanup on unmount
    return () => {
      window.removeEventListener('resize', handleResize);
      socket.off('update', handleUpdate);
    };
  }, []);
  
  return <div>...</div>;
}'''
    },
]


class IncidentGenerator:
    """Generates dynamic incidents using LLaMA or fallback scenarios."""
    
    def __init__(self):
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
    
    def generate_incident(self) -> DynamicIncident:
        """Generate a random incident from our diverse pool."""
        incident_data = random.choice(FALLBACK_INCIDENTS)
        
        return DynamicIncident(
            service=incident_data["service"],
            error_code=incident_data["error_code"],
            error_message=incident_data["error_message"],
            symptoms=incident_data["symptoms"],
            root_cause=incident_data["root_cause"],
            fix_description=incident_data["fix_description"],
            buggy_code=incident_data["buggy_code"],
            fixed_code=incident_data["fixed_code"],
            file_name=incident_data["file_name"],
            agent_owner=incident_data["agent_owner"]
        )


_generator = None

def get_incident_generator() -> IncidentGenerator:
    global _generator
    if _generator is None:
        _generator = IncidentGenerator()
    return _generator
