# TrevVote Engine — GitHub Deployment Guide

This repository contains a multi-page MVP website and Python backend for the paid voting platform.

## Important

GitHub Pages can host the HTML/CSS/JS pages, but it **cannot run the Python backend**. Paystack initialization, webhooks, admin login, photo upload, and exports require the backend.

Best setup:

1. Push this folder to GitHub.
2. Deploy the repo on Render, Railway, DigitalOcean, Fly.io, or a VPS.
3. Use that backend domain as your live site.
4. Set Paystack webhook URL to:

```txt
https://your-domain.com/api/payments/webhook/paystack
```

## If you still want GitHub Pages for the frontend

Deploy the static pages to GitHub Pages and deploy `backend/server.py` separately on Render/Railway. Then edit `config.js`:

```js
window.TREV_VOTE_API_BASE = "https://your-backend-domain.com";
```

## Local test

```bash
cd trevvote-engine-github
python backend/server.py
```

Open:

```txt
http://127.0.0.1:8000
```

## Environment variables for production

```txt
HOST=0.0.0.0
FRONTEND_URL=https://your-domain.com
PAYSTACK_SECRET_KEY=sk_live_or_test_xxx
ALLOW_DEV_PAYMENTS=0
ADMIN_EMAIL=your-admin-email@example.com
ADMIN_PASSWORD=use-a-strong-password
ADMIN_ROLE=super_admin
TREVVOTE_DB=/var/data/trevvote.sqlite3
```

## MVP endpoints

```txt
GET  /api/health
GET  /api/contest
POST /api/payments/initialize
GET  /api/payments/verify/:reference
POST /api/payments/webhook/paystack
POST /api/admin/login
POST /api/admin/logout
GET  /api/admin/me
POST /api/admin/contestants
DELETE /api/admin/contestants/:id
POST /api/admin/contestants/:id/photo
POST /api/admin/settings
GET  /api/admin/reports/summary
GET  /api/admin/reports/payments.csv
GET  /api/admin/reports/contestants.csv
GET  /api/admin/reports/daily.txt
```

## Production checklist

- Set `ALLOW_DEV_PAYMENTS=0`.
- Never expose `PAYSTACK_SECRET_KEY` in frontend code.
- Use HTTPS.
- Set `FRONTEND_URL` to your deployed domain.
- Change the default admin password.
- Configure Paystack webhook.
- Use PostgreSQL for serious production campaigns.
- Configure backups.
