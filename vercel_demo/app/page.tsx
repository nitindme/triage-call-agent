'use client';

import { useState } from 'react';

// 🐛 BUGGY CODE - This is intentionally broken for demo purposes
// The bug: We're NOT sending 'currency' in the request body
// Backend now requires it after a recent deploy
async function createOrder(paymentIntentId: string, amount: number) {
  const res = await fetch("/api/create-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paymentIntentId,
      amount
      // 🐛 BUG: Missing 'currency: "INR"' here!
    })
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.message || "Order failed");
  }

  return await res.json();
}

export default function CheckoutPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [showCode, setShowCode] = useState(true);

  const handleCheckout = async () => {
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      // Simulate a payment intent ID
      const paymentIntentId = "pi_" + Math.random().toString(36).substr(2, 9);
      const amount = 2499.00;

      await createOrder(paymentIntentId, amount);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="demo-badge">🐛 DEMO - Intentionally Buggy</div>
      
      <div className="checkout-container">
        <div className="checkout-header">
          <h1>🛒 Checkout</h1>
          <p>Complete your order</p>
        </div>

        <div className="checkout-body">
          <div className="order-summary">
            <div className="order-item">
              <span>Premium Plan (1 year)</span>
              <span>₹1,999.00</span>
            </div>
            <div className="order-item">
              <span>Setup Fee</span>
              <span>₹500.00</span>
            </div>
            <div className="order-total">
              <span>Total</span>
              <span>₹2,499.00</span>
            </div>
          </div>

          <button 
            className="code-toggle"
            onClick={() => setShowCode(!showCode)}
          >
            {showCode ? '🔽 Hide' : '🔼 Show'} Frontend Code
          </button>

          {showCode && (
            <div className="code-viewer">
              <span className="comment">// checkout.ts - The buggy code</span>{'\n'}
              <span className="keyword">async function</span> createOrder(paymentIntentId, amount) {'{'}{'\n'}
              {'  '}<span className="keyword">const</span> res = <span className="keyword">await</span> fetch(<span className="string">"/api/create-order"</span>, {'{'}{'\n'}
              {'    '}method: <span className="string">"POST"</span>,{'\n'}
              {'    '}body: JSON.stringify({'{'}{'\n'}
              {'      '}paymentIntentId,{'\n'}
              <span className="bug">{'      '}amount  <span className="comment">// ❌ BUG: Missing 'currency' field!</span></span>
              {'    '}{'}'}{'\n'}
              {'  '}{'}'});{'\n'}
              {'}'}{'\n'}
            </div>
          )}

          <div className="payment-form">
            <div className="form-group">
              <label>Card Number</label>
              <input type="text" placeholder="4242 4242 4242 4242" defaultValue="4242 4242 4242 4242" />
            </div>
            <div className="form-group">
              <label>Expiry</label>
              <input type="text" placeholder="12/28" defaultValue="12/28" />
            </div>
          </div>

          <button 
            className="checkout-btn" 
            onClick={handleCheckout}
            disabled={loading}
          >
            {loading ? '⏳ Processing...' : '💳 Pay ₹2,499.00'}
          </button>

          {error && (
            <div className="error-panel">
              <h3>❌ Payment Failed</h3>
              <pre>{error}</pre>
              <p style={{ marginTop: '12px', fontSize: '14px', color: '#991b1b' }}>
                This error is intentional! The AI Incident Triage system will detect and fix this.
              </p>
            </div>
          )}

          {success && (
            <div className="success-panel">
              <h3>✅ Order Complete!</h3>
              <p>Thank you for your purchase.</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
