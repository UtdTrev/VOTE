# TrevVote Engine MVP

A white-label paid voting platform for awards, pageants, contests, schools, creators, and events.

## What it does

- Public voting website
- Contestant catalogue/grid
- Vote packages and custom votes
- Paystack-ready payment initialization
- Paystack webhook verification
- Vote crediting with duplicate protection
- Admin login and roles
- Contestant photo uploads
- CSV reporting exports

## Quick start

```bash
python backend/server.py
```

Open:

```txt
http://127.0.0.1:8000
```

Default local admin:

```txt
admin@trevvote.local
admin12345
```

## Payment testing

Without `PAYSTACK_SECRET_KEY`, local dev simulation is enabled by default.

For Paystack test/live mode:

```bash
export PAYSTACK_SECRET_KEY=sk_test_xxx
export FRONTEND_URL=http://127.0.0.1:8000
export ALLOW_DEV_PAYMENTS=0
python backend/server.py
```

## Deployment

See `DEPLOYMENT.md`.
