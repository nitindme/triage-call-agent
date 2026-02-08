# AI Incident Triage Demo - Checkout App

This is a **intentionally buggy** Next.js checkout app that demonstrates the AI Incident Triage Platform.

## The Bug

The frontend is missing the `currency` field in the payment request:

```typescript
// ❌ BUGGY - Missing currency
body: JSON.stringify({
  paymentIntentId,
  amount
})

// ✅ FIXED - With currency
body: JSON.stringify({
  paymentIntentId,
  amount,
  currency: "INR"
})
```

## Deploy to Vercel

1. Push this folder to GitHub
2. Connect to Vercel
3. Deploy

Or use the Vercel CLI:

```bash
cd vercel_demo
npx vercel
```

## Local Development

```bash
npm install
npm run dev
```

Open http://localhost:3000 and click "Pay" to see the error.

## How It Works

1. User clicks checkout → Frontend sends request WITHOUT currency
2. Backend validates and returns 400 error
3. AI Incident Triage Platform detects the error pattern
4. AI agents analyze logs and propose fix
5. Fix is applied and deployed
6. Order succeeds!
