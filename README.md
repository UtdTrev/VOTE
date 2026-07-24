# TrevVote Engine MVP

A multi-page, white-label paid voting platform for awards, pageants, contests, schools, creators, and events.

## Pages

```txt
index.html           # Landing page
contestants.html     # Public contestant catalogue and vote modal
contestant.html?id=  # Shareable contestant profile page
packages.html        # Vote packages and payment explanation
leaderboard.html     # Live results / hidden-results message
admin.html           # Admin login, roles, dashboard, uploads and exports
payment-success.html # Payment receipt / verification page
```

## Features

- Multi-page public website
- Shareable contestant profile pages
- WhatsApp share links for contestants
- Contestant catalogue/grid
- Vote packages and custom votes
- Same Paystack-style payment flow as Trev AI
- Backend payment initialization
- Paystack webhook verification
- Vote crediting with duplicate protection
- Hidden/show leaderboard option
- Polished payment receipt page
- Admin login and role display
- Contestant photo uploads
- CSV reporting exports
- Daily report text for email/WhatsApp

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

## Paystack test/live mode

```bash
export PAYSTACK_SECRET_KEY=sk_test_xxx
export FRONTEND_URL=http://127.0.0.1:8000
export ALLOW_DEV_PAYMENTS=0
python backend/server.py
```

## Deploy

See `DEPLOYMENT.md`.
