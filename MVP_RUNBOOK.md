# TrevVote Engine MVP Runbook

## Current payment mode

Paystack has been discarded for now. The active payment mode is manual bank transfer, matching the Trev AI-style payment option.

## User flow

1. Voter opens `contestants.html` or a shared `contestant.html?id=c001` link.
2. Voter clicks vote and is sent to `payment.html`.
3. Voter sees selected package and bank-transfer details.
4. Voter transfers the exact amount.
5. Voter submits name, email/WhatsApp, contestant, package and transfer reference/sender name.
6. Backend records a pending manual payment.
7. Admin verifies or rejects the payment in `admin.html`.
8. Votes are credited only after verification.

## Bank details

Configure using environment variables:

```txt
BANK_NAME=OPAY
BANK_ACCOUNT_NAME=DANIEL GBENGA OLUTIMEHIN
BANK_ACCOUNT_NUMBER=6109478874
PAYMENT_INSTRUCTIONS=Transfer the exact package amount. Keep your receipt or transaction reference until your votes are verified.
```

## Pages

```txt
index.html
contestants.html
contestant.html?id=c001
packages.html
payment.html
leaderboard.html
client-portal.html
admin.html
payment-success.html
```

## Client portal

`client-portal.html` lets clients upload and edit:

- Poll title
- Poll description
- Organiser/client name
- Deadline
- Vote price
- Voting status
- Show/hide live results
- Poll logo
- Poll banner
- Contestant photos
- Public poll link

## Admin portal

`admin.html` supports:

- Login and roles
- Overview metrics
- Add/remove contestants
- Upload contestant photos
- View pending manual transfers
- Verify or reject transfers
- Save settings
- Export payments CSV
- Export contestants CSV
- Copy/send daily report text

Default local login:

```txt
admin@trevvote.local / admin12345
```

Roles:

```txt
super_admin  # full access
client_admin # manage poll data, contestants, uploads and verification
viewer       # reports only
```

## Main endpoints

```txt
GET  /api/contest
POST /api/payments/manual-submit
GET  /api/payments/verify/:reference
POST /api/admin/payments/:reference/verify
POST /api/admin/payments/:reference/reject
POST /api/client/poll/details
POST /api/client/poll/image
GET  /api/admin/reports/payments.csv
GET  /api/admin/reports/contestants.csv
GET  /api/admin/reports/daily.txt
```

## Run locally

```bash
python backend/server.py
```

Open:

```txt
http://127.0.0.1:8000
```

## Production notes

- Use a strong admin password.
- Use HTTPS.
- Use PostgreSQL for real campaigns.
- Configure backups.
- Keep bank details accurate.
- Keep all transfer verification actions in the admin audit log.
