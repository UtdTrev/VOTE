# TrevVote Engine MVP Runbook

This prototype now has a real backend payment flow shape:

1. Frontend vote modal calls `POST /api/payments/initialize`.
2. Backend creates a pending payment with a unique reference.
3. Backend initializes Paystack and returns an `authorization_url`.
4. User is redirected to Paystack checkout.
5. Paystack sends `charge.success` to `POST /api/payments/webhook/paystack`.
6. Backend verifies the webhook signature and then verifies the transaction against Paystack.
7. Backend credits the contestant votes exactly once.
8. Success page calls `GET /api/payments/verify/:reference` to display the final status.

## Files added/changed

```txt
backend/server.py              # Runnable MVP backend, SQLite + Paystack endpoints
backend/.env.example           # Environment variables
payment-success.html           # Gateway callback/success page
app.js                         # Frontend now calls backend payment initialization
styles.css                     # Current visual design
```

## Run locally without Paystack keys

This uses backend dev simulation mode.

```bash
cd /home/user/vote-engine-prototype
python3 backend/server.py
```

Open:

```txt
http://127.0.0.1:8000
```

When you click Pay, the backend creates a pending payment and redirects to a dev simulation URL. That simulation marks the payment successful and credits votes.

## Run with Paystack test keys

```bash
cd /home/user/vote-engine-prototype
export PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxx
export FRONTEND_URL=http://127.0.0.1:8000
export ALLOW_DEV_PAYMENTS=0
python3 backend/server.py
```

Then set your Paystack webhook URL to:

```txt
https://your-domain.com/api/payments/webhook/paystack
```

For local webhook testing, expose your localhost with a tunnel like ngrok or Cloudflare Tunnel:

```txt
https://your-tunnel-url/api/payments/webhook/paystack
```

## Production notes

Before live deployment:

- Set `ALLOW_DEV_PAYMENTS=0`.
- Use `sk_live_...` only on the server, never in frontend code.
- Use HTTPS.
- Set `FRONTEND_URL` to your real domain.
- Use PostgreSQL for production instead of SQLite.
- Add admin authentication before giving clients dashboard access.
- Add backups and transaction exports.

## Current endpoints

```txt
GET  /api/health
GET  /api/contest
POST /api/payments/initialize
GET  /api/payments/verify/:reference
POST /api/payments/webhook/paystack
GET  /api/dev/payments/simulate-success?reference=...
```

## Request example

```json
POST /api/payments/initialize
{
  "contest_id": "campus-icons-2026",
  "contestant_id": "c002",
  "package_id": "gold",
  "votes": 120,
  "voter_name": "Ada Okafor",
  "voter_email": "ada@example.com",
  "voter_phone": "08012345678"
}
```

## Admin login and roles

Added endpoints:

```txt
POST /api/admin/login
POST /api/admin/logout
GET  /api/admin/me
```

Default local credentials are:

```txt
admin@trevvote.local / admin12345
```

For production, set these before first run:

```bash
export ADMIN_EMAIL=you@yourdomain.com
export ADMIN_PASSWORD='use-a-strong-password'
export ADMIN_ROLE=super_admin
```

Roles supported by the backend:

```txt
super_admin  # full access
client_admin # manage contest data, uploads and settings
viewer       # reports only
```

## Contestant photo upload

Added endpoint:

```txt
POST /api/admin/contestants/:id/photo
```

The frontend admin table now has an Upload button per contestant. Images are saved under:

```txt
media/contestants/
```

Allowed image types: JPG, PNG and WebP. Default max size: 4MB.

## Reporting exports

Added endpoints:

```txt
GET /api/admin/reports/summary
GET /api/admin/reports/payments.csv
GET /api/admin/reports/contestants.csv
```

The frontend admin panel now has export buttons after login.

## What comes next

1. Deploy to a real server.
2. Switch SQLite to PostgreSQL for production.
3. Add multi-client/multi-contest super-admin screens.
4. Add automated daily reports by email or WhatsApp.

## Shareable contestant profile pages

Added page:

```txt
contestant.html?id=c001
```

Each profile shows:

- Larger contestant visual/photo
- Bio
- Current rank
- Voting code
- Total votes
- Vote button
- WhatsApp share button
- Copy profile link button

## WhatsApp share links

Contestant cards and profile pages now generate share links like:

```txt
Vote for Adaeze Nwosu (CI-001) here: https://yourdomain.com/contestant.html?id=c001
```

## Hidden leaderboard option

Admin settings now include:

```txt
Show live results: Yes/No
```

If hidden, the public leaderboard shows a message instead of rankings:

```txt
Your vote has been counted. The organiser has chosen to hide public rankings until results are announced.
```

The backend stores this as `show_live_results` on the contest.

## Payment receipt improvements

`payment-success.html` now displays:

```txt
Reference
Status
Contestant
Votes purchased
Amount paid
Date/time
Voter
Gateway
```

## Daily report text

Added endpoint:

```txt
GET /api/admin/reports/daily.txt
```

The admin payments tab also shows a daily report preview that can be copied or opened in WhatsApp.
