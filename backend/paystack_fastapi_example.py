"""
Paystack-ready FastAPI example for the TrevVote paid voting engine.

This is intentionally compact so the payment flow is clear. In production,
connect these handlers to SQLAlchemy/Django ORM models that match schema.sql.

Required environment variables:
- PAYSTACK_SECRET_KEY=sk_live_xxx or sk_test_xxx
- PAYSTACK_WEBHOOK_SECRET=same secret used to validate x-paystack-signature
- FRONTEND_SUCCESS_URL=https://yourdomain.com/payment/success
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
PAYSTACK_WEBHOOK_SECRET = os.getenv("PAYSTACK_WEBHOOK_SECRET", PAYSTACK_SECRET_KEY)
FRONTEND_SUCCESS_URL = os.getenv("FRONTEND_SUCCESS_URL", "https://example.com/payment/success")
PAYSTACK_BASE_URL = "https://api.paystack.co"

app = FastAPI(title="TrevVote Payment API")


class InitializePaymentIn(BaseModel):
    contest_id: str
    contestant_id: str
    package_id: str | None = None
    votes: int = Field(gt=0)
    voter_name: str = Field(min_length=2)
    voter_email: EmailStr | None = None
    voter_phone: str | None = None


@dataclass
class Contest:
    id: str
    title: str
    vote_price_kobo: int
    status: str


@dataclass
class Contestant:
    id: str
    contest_id: str
    name: str
    is_active: bool


# Replace this fake repository with your database/ORM.
class Repo:
    async def get_contest(self, contest_id: str) -> Contest | None:
        return Contest(id=contest_id, title="Campus Icons Awards", vote_price_kobo=10000, status="open")

    async def get_contestant(self, contestant_id: str) -> Contestant | None:
        return Contestant(id=contestant_id, contest_id="demo-contest", name="Demo Contestant", is_active=True)

    async def create_pending_payment(self, **kwargs) -> None:
        # Insert into payments table with status='pending'.
        print("create payment", kwargs)

    async def mark_payment_success_and_credit_votes(self, reference: str, gateway_payload: dict) -> None:
        """
        Production logic inside one DB transaction:
        1. Lock payment by gateway_reference using SELECT ... FOR UPDATE.
        2. If status is already successful, return without adding votes again.
        3. Confirm amount, contest_id, contestant_id, and votes match your pending record.
        4. Update payments.status='successful', processed_at=now().
        5. Increment contestants.vote_count by payments.votes_purchased.
        6. Insert vote_transactions with unique payment_id.
        """
        print("credit votes once", reference, gateway_payload.get("status"))


repo = Repo()


def require_paystack_key() -> None:
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="PAYSTACK_SECRET_KEY is not configured")


def build_reference() -> str:
    return f"TVE-{secrets.token_hex(8).upper()}"


async def verify_transaction(reference: str) -> dict:
    require_paystack_key()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"},
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="Could not verify Paystack transaction")
    payload = response.json()
    if not payload.get("status"):
        raise HTTPException(status_code=400, detail=payload.get("message", "Paystack verification failed"))
    return payload["data"]


@app.post("/payments/initialize")
async def initialize_payment(data: InitializePaymentIn):
    """Create a pending payment and return Paystack checkout URL."""

    require_paystack_key()
    contest = await repo.get_contest(data.contest_id)
    if not contest or contest.status != "open":
        raise HTTPException(status_code=400, detail="Voting is not open for this contest")

    contestant = await repo.get_contestant(data.contestant_id)
    if not contestant or not contestant.is_active:
        raise HTTPException(status_code=404, detail="Contestant not found or inactive")

    # In production, never trust frontend amount. Calculate it server-side.
    amount_kobo = data.votes * contest.vote_price_kobo
    reference = build_reference()

    await repo.create_pending_payment(
        contest_id=data.contest_id,
        contestant_id=data.contestant_id,
        package_id=data.package_id,
        voter_name=data.voter_name,
        voter_email=data.voter_email,
        voter_phone=data.voter_phone,
        amount_kobo=amount_kobo,
        votes_purchased=data.votes,
        gateway="paystack",
        gateway_reference=reference,
        status="pending",
    )

    payload = {
        "email": data.voter_email or "no-email@example.com",
        "amount": amount_kobo,
        "reference": reference,
        "callback_url": f"{FRONTEND_SUCCESS_URL}?reference={reference}",
        "metadata": {
            "contest_id": data.contest_id,
            "contestant_id": data.contestant_id,
            "package_id": data.package_id,
            "votes": data.votes,
            "voter_name": data.voter_name,
            "voter_phone": data.voter_phone,
        },
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"},
        )

    result = response.json()
    if response.status_code >= 400 or not result.get("status"):
        raise HTTPException(status_code=400, detail=result.get("message", "Payment initialization failed"))

    return {
        "reference": reference,
        "authorization_url": result["data"]["authorization_url"],
        "access_code": result["data"].get("access_code"),
    }


@app.get("/payments/verify/{reference}")
async def verify_payment_from_success_page(reference: str):
    """
    Frontend success page can call this for display.
    The webhook is still the primary vote-crediting mechanism.
    """

    tx = await verify_transaction(reference)
    return {
        "reference": reference,
        "status": tx.get("status"),
        "amount": tx.get("amount"),
        "metadata": tx.get("metadata"),
    }


@app.post("/payments/webhook/paystack")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: Annotated[str | None, Header()] = None,
):
    """Verify Paystack webhook signature, verify transaction, then credit votes exactly once."""

    body = await request.body()
    expected = hmac.new(
        PAYSTACK_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha512,
    ).hexdigest()

    if not x_paystack_signature or not hmac.compare_digest(expected, x_paystack_signature):
        raise HTTPException(status_code=401, detail="Invalid Paystack signature")

    event = await request.json()
    if event.get("event") != "charge.success":
        return {"ok": True, "ignored": event.get("event")}

    reference = event.get("data", {}).get("reference")
    if not reference:
        raise HTTPException(status_code=400, detail="Missing transaction reference")

    tx = await verify_transaction(reference)
    if tx.get("status") != "success":
        return {"ok": True, "ignored": "transaction_not_successful"}

    # Idempotent transaction: a repeated webhook must not add votes twice.
    await repo.mark_payment_success_and_credit_votes(reference, gateway_payload=tx)
    return {"ok": True}
