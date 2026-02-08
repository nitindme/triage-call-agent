// checkout.ts - Next.js client snippet
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
