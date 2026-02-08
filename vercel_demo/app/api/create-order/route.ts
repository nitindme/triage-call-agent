import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const body = await request.json();
  
  // Simulate backend validation that requires 'currency'
  if (!body.currency) {
    return NextResponse.json(
      { 
        error: "BILLING_400",
        message: "Missing required field: currency. Backend validation requires 'currency' field in payment request.",
        details: {
          received_fields: Object.keys(body),
          required_fields: ["paymentIntentId", "amount", "currency"],
          missing_fields: ["currency"]
        }
      },
      { status: 400 }
    );
  }
  
  // Success case (after fix is applied)
  return NextResponse.json({
    success: true,
    order_id: "ORD-" + Math.random().toString(36).substr(2, 9).toUpperCase(),
    message: "Order created successfully"
  });
}
