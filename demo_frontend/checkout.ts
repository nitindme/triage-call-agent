// checkout.ts - FIXED
async function createOrder(paymentIntentId: string, amount: number) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);
  
  try {
    const res = await fetch("/api/create-order", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paymentIntentId, amount, currency: "INR" }),
      signal: controller.signal
    });
    if (!res.ok) throw new Error("Order failed");
    return await res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}