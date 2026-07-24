# TrevVote Engine Prototype

This is a clickable prototype of a white-label paid voting platform like the Trev AI payment flow, adapted for contestant voting.

## What is included

- Public landing page
- Contestant listing and search/filter
- Vote packages in Nigerian Naira
- Demo checkout modal
- Simulated payment gateway + webhook verification steps
- Instant vote tally update
- Live leaderboard
- Admin dashboard for overview, contestants, payments, and settings
- PostgreSQL schema sketch in `backend/schema.sql`
- Paystack FastAPI payment example in `backend/paystack_fastapi_example.py`

## MVP payment backend added

The website now connects to a backend payment initialization endpoint:

```txt
POST /api/payments/initialize
```

The backend creates a pending payment, initializes Paystack when `PAYSTACK_SECRET_KEY` is configured, and exposes a webhook endpoint:

```txt
POST /api/payments/webhook/paystack
```

The webhook validates the Paystack signature, verifies the transaction, and credits votes exactly once. Admin login, roles, contestant photo upload, and CSV reporting exports are also included. See `MVP_RUNBOOK.md` for setup and testing instructions.

## What I need from you to make it real

1. Brand name, logo, and preferred colors.
2. Contest name and voting deadline.
3. Contestants: names, photos, categories, bios, voting codes.
4. Payment gateway choice: Paystack, Flutterwave, or Monnify.
5. Gateway keys: test keys first, then live keys.
6. Payout model: all money to your account, client subaccount split, or manual settlement.
7. Admin users and reporting preferences.

## Recommended production stack

- Frontend: Next.js + Tailwind CSS
- Backend: Django or FastAPI
- Database: PostgreSQL
- Payments: Paystack first, Flutterwave/Monnify later
- Image storage: Cloudinary or S3
- Hosting: Render, Railway, DigitalOcean, or VPS
