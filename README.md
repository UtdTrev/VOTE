# TrevVote Engine MVP

A multi-page, white-label paid voting platform using the same **manual bank-transfer payment option** as the Trev AI screenshot.

## Pages

```txt
index.html             # Landing page
contestants.html       # Public contestant catalogue
contestant.html?id=    # Shareable contestant profile page
packages.html          # Vote packages
payment.html           # Manual bank-transfer registration page
leaderboard.html       # Live/hidden results
client-portal.html     # Client portal for poll details and images
admin.html             # Admin verification, roles, reports and uploads
payment-success.html   # Transfer submission receipt / verification status
```

## Payment flow

1. Voter chooses contestant/package.
2. Voter goes to `payment.html`.
3. Voter transfers exact amount to the displayed bank account.
4. Voter submits full name, email/WhatsApp, and transfer reference/sender name.
5. Admin verifies the transfer in `admin.html`.
6. Votes are credited only after admin approval.

## Default bank details

Configured in `backend/.env.example`:

```txt
BANK_NAME=OPAY
BANK_ACCOUNT_NAME=DANIEL GBENGA OLUTIMEHIN
BANK_ACCOUNT_NUMBER=6109478874
```

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

Change admin and bank details with environment variables before deployment.
