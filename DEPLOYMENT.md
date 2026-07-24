# TrevVote Engine — GitHub Deployment Guide

This repository contains a multi-page MVP website and Python backend for a manual bank-transfer paid voting platform.

## Important

GitHub Pages can host the HTML/CSS/JS pages, but it **cannot run the Python backend**. The backend is required for:

- Transfer registration submission
- Admin/client login
- Manual transfer verification
- Vote crediting
- Photo uploads
- Poll logo/banner upload
- CSV/report exports

Best setup:

1. Push this folder to GitHub.
2. Deploy the repo on Render, Railway, DigitalOcean, Fly.io, or a VPS.
3. Use that backend domain as your live site.

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
PAYMENT_GATEWAY=manual_transfer
BANK_NAME=OPAY
BANK_ACCOUNT_NAME=DANIEL GBENGA OLUTIMEHIN
BANK_ACCOUNT_NUMBER=6109478874
PAYMENT_INSTRUCTIONS=Transfer the exact package amount. Keep your receipt or transaction reference until your votes are verified.
ADMIN_EMAIL=your-admin-email@example.com
ADMIN_PASSWORD=use-a-strong-password
ADMIN_ROLE=super_admin
TREVVOTE_DB=/var/data/trevvote.sqlite3
```

## MVP endpoints

```txt
GET  /api/health
GET  /api/contest
POST /api/payments/manual-submit
GET  /api/payments/verify/:reference
POST /api/admin/login
POST /api/admin/logout
GET  /api/admin/me
POST /api/admin/payments/:reference/verify
POST /api/admin/payments/:reference/reject
POST /api/admin/contestants
DELETE /api/admin/contestants/:id
POST /api/admin/contestants/:id/photo
POST /api/admin/settings
POST /api/client/poll/details
POST /api/client/poll/image
GET  /api/admin/reports/summary
GET  /api/admin/reports/payments.csv
GET  /api/admin/reports/contestants.csv
GET  /api/admin/reports/daily.txt
```

## Production checklist

- Change default admin password.
- Set real bank details.
- Use HTTPS.
- Set `FRONTEND_URL` to your deployed domain.
- Use PostgreSQL for serious production campaigns.
- Configure backups.
- Consider restricting admin/client routes by IP or adding 2FA later.
