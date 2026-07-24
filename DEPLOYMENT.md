# TrevVote Engine — GitHub Deployment Guide

This repository contains the MVP website and backend for the paid voting platform.

## Important

GitHub Pages can host static HTML/CSS/JS only. It **cannot run the Python backend**, so Paystack initialization, webhooks, admin login, photo uploads, and CSV exports will not work on GitHub Pages alone.

Recommended deployment flow:

1. Push this folder to GitHub.
2. Connect the GitHub repo to Render, Railway, Fly.io, DigitalOcean App Platform, or a VPS.
3. Deploy the Python backend from the repo.
4. Set your Paystack webhook URL to:

```txt
https://your-domain.com/api/payments/webhook/paystack
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

Default local admin:

```txt
admin@trevvote.local
admin12345
```

Change this in production with environment variables.

## Render deployment

This repo includes `render.yaml`.

Steps:

1. Create a GitHub repo and upload these files.
2. Go to Render.
3. Choose **New > Blueprint** or **New > Web Service**.
4. Connect the GitHub repo.
5. Set environment variables:

```txt
HOST=0.0.0.0
FRONTEND_URL=https://your-render-url.onrender.com
PAYSTACK_SECRET_KEY=sk_live_or_test_xxx
ALLOW_DEV_PAYMENTS=0
ADMIN_EMAIL=your-admin-email@example.com
ADMIN_PASSWORD=use-a-strong-password
ADMIN_ROLE=super_admin
TREVVOTE_DB=/var/data/trevvote.sqlite3
```

6. Deploy.
7. In Paystack dashboard, set webhook URL:

```txt
https://your-render-url.onrender.com/api/payments/webhook/paystack
```

## Railway deployment

1. Push to GitHub.
2. Create a Railway project from the repo.
3. Set start command:

```bash
python backend/server.py
```

4. Add environment variables:

```txt
HOST=0.0.0.0
FRONTEND_URL=https://your-railway-domain
PAYSTACK_SECRET_KEY=sk_live_or_test_xxx
ALLOW_DEV_PAYMENTS=0
ADMIN_EMAIL=your-admin-email@example.com
ADMIN_PASSWORD=use-a-strong-password
ADMIN_ROLE=super_admin
```

5. Add a persistent volume if using SQLite, or migrate to PostgreSQL for production.

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
```

## Production checklist

- Set `ALLOW_DEV_PAYMENTS=0`.
- Never expose `PAYSTACK_SECRET_KEY` in frontend code.
- Use HTTPS.
- Set `FRONTEND_URL` to your real deployed domain.
- Change default admin password.
- Use PostgreSQL for serious production campaigns.
- Configure database backups.
- Configure Paystack webhook.
