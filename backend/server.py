#!/usr/bin/env python3
"""
TrevVote Engine MVP backend.

A dependency-free Python backend that serves the prototype frontend and exposes
real payment endpoints for a paid voting MVP.

Run:
    cd /home/user/vote-engine-prototype
    PAYSTACK_SECRET_KEY=sk_test_xxx python3 backend/server.py

If PAYSTACK_SECRET_KEY is not set, the server runs in safe local dev mode and
returns a simulation URL instead of contacting Paystack. Disable this in
production by setting ALLOW_DEV_PAYMENTS=0.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("TREVVOTE_DB", ROOT / "trevvote.sqlite3"))
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "").strip()
PAYSTACK_BASE_URL = os.getenv("PAYSTACK_BASE_URL", "https://api.paystack.co").rstrip("/")
GATEWAY = os.getenv("PAYMENT_GATEWAY", "paystack")
ALLOW_DEV_PAYMENTS = os.getenv("ALLOW_DEV_PAYMENTS", "1") == "1"
FRONTEND_URL = os.getenv("FRONTEND_URL", f"http://{HOST}:{PORT}").rstrip("/")
MEDIA_DIR = ROOT / "media"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@trevvote.local").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin12345").strip()
ADMIN_ROLE = os.getenv("ADMIN_ROLE", "super_admin").strip()
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(60 * 60 * 24 * 7)))
MAX_PHOTO_BYTES = int(os.getenv("MAX_PHOTO_BYTES", str(4 * 1024 * 1024)))

CONTEST_ID = "campus-icons-2026"

CONTESTANTS = [
    ("c001", "Adaeze Nwosu", "CI-001", "Fashion", "University of Abuja", "Style creator, campus ambassador, and student entrepreneur.", 7420, "linear-gradient(135deg, #ff7a90, #8b5cf6)", 1),
    ("c002", "Tobi Akinwale", "CI-002", "Music", "Baze University", "Afro-fusion vocalist building a loyal student fan base.", 8950, "linear-gradient(135deg, #22d3ee, #2563eb)", 2),
    ("c003", "Zainab Bello", "CI-003", "Leadership", "Nile University", "Volunteer coordinator and award-winning debate captain.", 6410, "linear-gradient(135deg, #f59e0b, #ef4444)", 3),
    ("c004", "Chidera Okeke", "CI-004", "Tech", "Veritas University", "Frontend developer and founder of a campus coding circle.", 5125, "linear-gradient(135deg, #2ee59d, #0ea5e9)", 4),
    ("c005", "Musa Danladi", "CI-005", "Sports", "UniAbuja Sports Club", "Team captain, fitness coach, and community mentor.", 3860, "linear-gradient(135deg, #a3e635, #16a34a)", 5),
    ("c006", "Ifeoma Eze", "CI-006", "Media", "National Open University", "Content producer and host of a student culture podcast.", 4680, "linear-gradient(135deg, #ec4899, #f97316)", 6),
]

PACKAGES = [
    ("basic", "Starter", 5, 50000, "Entry", "Quick support for any contestant.", 0),
    ("bronze", "Bronze", 10, 100000, "Popular", "Simple ₦100-per-vote bundle.", 0),
    ("silver", "Silver", 55, 500000, "Bonus", "Get 5 extra votes on this package.", 1),
    ("gold", "Gold", 120, 1000000, "Best value", "High-impact voting for loyal supporters.", 0),
]

DEMO_PAYMENTS = [
    ("TVE-DEMO-001", "Sandra U.", "sandra@example.com", "08030000001", "c002", 120, 1000000),
    ("TVE-DEMO-002", "Michael O.", "michael@example.com", "08030000002", "c001", 55, 500000),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(
            """
            create table if not exists contests (
              id text primary key,
              title text not null,
              slug text not null unique,
              status text not null default 'open',
              vote_price_kobo integer not null default 10000,
              gateway text not null default 'paystack',
              ends_at text,
              show_live_results integer not null default 1,
              created_at text not null
            );

            create table if not exists contestants (
              id text primary key,
              contest_id text not null references contests(id) on delete cascade,
              name text not null,
              code text not null,
              category text,
              region text,
              bio text,
              vote_count integer not null default 0,
              gradient text,
              created_at integer not null,
              is_active integer not null default 1
            );

            create table if not exists vote_packages (
              id text primary key,
              contest_id text not null references contests(id) on delete cascade,
              name text not null,
              votes integer not null,
              amount_kobo integer not null,
              tag text,
              description text,
              is_featured integer not null default 0,
              is_active integer not null default 1
            );

            create table if not exists payments (
              reference text primary key,
              contest_id text not null references contests(id),
              contestant_id text not null references contestants(id),
              package_id text references vote_packages(id),
              voter_name text not null,
              voter_email text,
              voter_phone text,
              amount_kobo integer not null,
              votes_purchased integer not null,
              gateway text not null default 'paystack',
              status text not null default 'pending',
              authorization_url text,
              raw_gateway_payload text,
              created_at text not null,
              processed_at text
            );

            create table if not exists vote_transactions (
              id integer primary key autoincrement,
              reference text not null unique references payments(reference),
              contest_id text not null,
              contestant_id text not null,
              votes_added integer not null,
              created_at text not null
            );

            create table if not exists admins (
              id text primary key,
              email text not null unique,
              name text not null,
              password_hash text not null,
              role text not null check (role in ('super_admin', 'client_admin', 'viewer')),
              is_active integer not null default 1,
              created_at text not null
            );

            create table if not exists admin_sessions (
              token_hash text primary key,
              admin_id text not null references admins(id) on delete cascade,
              created_at text not null,
              expires_at integer not null
            );

            create table if not exists audit_logs (
              id integer primary key autoincrement,
              admin_id text,
              action text not null,
              details text,
              created_at text not null
            );
            """
        )

        ensure_column(conn, "contestants", "photo_url", "text")
        existing = conn.execute("select count(*) from contests").fetchone()[0]
        if existing == 0:
            seed(conn)
        seed_default_admin(conn)


def seed(conn: sqlite3.Connection) -> None:
    conn.execute(
        "insert into contests (id, title, slug, status, vote_price_kobo, gateway, ends_at, show_live_results, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (CONTEST_ID, "Campus Icons Awards 2026", "campus-icons-awards-2026", "open", 10000, GATEWAY, "2026-08-31T22:59:00+01:00", 1, now_iso()),
    )
    for row in CONTESTANTS:
        conn.execute(
            "insert into contestants (id, contest_id, name, code, category, region, bio, vote_count, gradient, created_at, is_active, photo_url) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, null)",
            (row[0], CONTEST_ID, row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]),
        )
    for row in PACKAGES:
        conn.execute(
            "insert into vote_packages (id, contest_id, name, votes, amount_kobo, tag, description, is_featured, is_active) values (?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (row[0], CONTEST_ID, row[1], row[2], row[3], row[4], row[5], row[6]),
        )
    created = now_iso()
    for ref, voter, email, phone, contestant_id, votes, amount_kobo in DEMO_PAYMENTS:
        conn.execute(
            "insert into payments (reference, contest_id, contestant_id, package_id, voter_name, voter_email, voter_phone, amount_kobo, votes_purchased, gateway, status, authorization_url, raw_gateway_payload, created_at, processed_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, 'paystack', 'successful', '', '{}', ?, ?)",
            (ref, CONTEST_ID, contestant_id, None, voter, email, phone, amount_kobo, votes, created, created),
        )
        conn.execute(
            "insert into vote_transactions (reference, contest_id, contestant_id, votes_added, created_at) values (?, ?, ?, ?, ?)",
            (ref, CONTEST_ID, contestant_id, votes, created),
        )


def ngn_from_kobo(kobo: int) -> int:
    return int(kobo // 100)


def make_reference() -> str:
    return f"TVE-{int(time.time())}-{secrets.token_hex(4).upper()}"


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def contest_payload() -> dict[str, Any]:
    with connect() as conn:
        contest = conn.execute("select * from contests where id = ?", (CONTEST_ID,)).fetchone()
        contestants = conn.execute("select * from contestants where contest_id = ? and is_active = 1 order by created_at", (CONTEST_ID,)).fetchall()
        packages = conn.execute("select * from vote_packages where contest_id = ? and is_active = 1 order by amount_kobo", (CONTEST_ID,)).fetchall()
        payments = conn.execute("select * from payments where contest_id = ? order by created_at desc limit 50", (CONTEST_ID,)).fetchall()

    return {
        "settings": {
            "title": contest["title"],
            "votePrice": ngn_from_kobo(contest["vote_price_kobo"]),
            "gateway": contest["gateway"].capitalize(),
            "status": contest["status"],
            "endsAt": contest["ends_at"],
            "showLiveResults": bool(contest["show_live_results"]),
        },
        "contestants": [
            {
                "id": c["id"],
                "name": c["name"],
                "code": c["code"],
                "category": c["category"],
                "region": c["region"],
                "bio": c["bio"],
                "votes": c["vote_count"],
                "gradient": c["gradient"],
                "photoUrl": c["photo_url"] if "photo_url" in c.keys() else None,
                "createdAt": c["created_at"],
            }
            for c in contestants
        ],
        "packages": [
            {
                "id": p["id"],
                "name": p["name"],
                "votes": p["votes"],
                "amount": ngn_from_kobo(p["amount_kobo"]),
                "tag": p["tag"],
                "description": p["description"],
                "featured": bool(p["is_featured"]),
            }
            for p in packages
        ],
        "payments": [
            {
                "reference": p["reference"],
                "voter": p["voter_name"],
                "email": p["voter_email"],
                "phone": p["voter_phone"],
                "contestantId": p["contestant_id"],
                "votes": p["votes_purchased"],
                "amount": ngn_from_kobo(p["amount_kobo"]),
                "status": "verified" if p["status"] == "successful" else p["status"],
                "createdAt": p["created_at"],
            }
            for p in payments
        ],
    }


def json_response(handler: BaseHTTPRequestHandler, status: int, data: Any) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "content-type, authorization, x-admin-token, x-paystack-signature")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


def redirect(handler: BaseHTTPRequestHandler, url: str) -> None:
    handler.send_response(302)
    handler.send_header("Location", url)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()


def read_json(handler: BaseHTTPRequestHandler) -> tuple[dict[str, Any], bytes]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    body = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(body.decode("utf-8") or "{}"), body
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON body")


def paystack_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not PAYSTACK_SECRET_KEY:
        raise RuntimeError("PAYSTACK_SECRET_KEY is not configured")
    url = f"{PAYSTACK_BASE_URL}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            response_body = resp.read().decode("utf-8")
            result = json.loads(response_body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")
        raise RuntimeError(f"Paystack error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Paystack: {exc.reason}") from exc
    if not result.get("status"):
        raise RuntimeError(result.get("message", "Paystack request failed"))
    return result


def verify_paystack_transaction(reference: str) -> dict[str, Any]:
    result = paystack_request("GET", f"/transaction/verify/{urllib.parse.quote(reference)}")
    return result["data"]


def process_successful_payment(reference: str, gateway_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    gateway_payload = gateway_payload or {}
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        payment = conn.execute("select * from payments where reference = ?", (reference,)).fetchone()
        if not payment:
            raise ValueError("Payment reference not found")

        if payment["status"] == "successful":
            contestant = conn.execute("select * from contestants where id = ?", (payment["contestant_id"],)).fetchone()
            conn.commit()
            return {
                "reference": reference,
                "status": "successful",
                "alreadyProcessed": True,
                "contestant": contestant["name"] if contestant else None,
                "votes": payment["votes_purchased"],
                "amount": ngn_from_kobo(payment["amount_kobo"]),
                "createdAt": payment["created_at"],
                "processedAt": payment["processed_at"],
                "voter": payment["voter_name"],
                "email": payment["voter_email"],
                "phone": payment["voter_phone"],
                "gateway": payment["gateway"],
            }

        gateway_amount = int(gateway_payload.get("amount") or payment["amount_kobo"])
        if gateway_amount != int(payment["amount_kobo"]):
            conn.execute("update payments set status = 'failed', raw_gateway_payload = ? where reference = ?", (json.dumps(gateway_payload), reference))
            conn.commit()
            raise ValueError("Gateway amount does not match pending payment")

        processed_at = now_iso()
        conn.execute(
            "update payments set status = 'successful', raw_gateway_payload = ?, processed_at = ? where reference = ?",
            (json.dumps(gateway_payload), processed_at, reference),
        )
        conn.execute(
            "update contestants set vote_count = vote_count + ? where id = ?",
            (payment["votes_purchased"], payment["contestant_id"]),
        )
        conn.execute(
            "insert or ignore into vote_transactions (reference, contest_id, contestant_id, votes_added, created_at) values (?, ?, ?, ?, ?)",
            (reference, payment["contest_id"], payment["contestant_id"], payment["votes_purchased"], processed_at),
        )
        contestant = conn.execute("select * from contestants where id = ?", (payment["contestant_id"],)).fetchone()
        conn.commit()
        return {
            "reference": reference,
            "status": "successful",
            "alreadyProcessed": False,
            "contestant": contestant["name"] if contestant else None,
            "votes": payment["votes_purchased"],
            "amount": ngn_from_kobo(payment["amount_kobo"]),
            "createdAt": payment["created_at"],
            "processedAt": processed_at,
            "voter": payment["voter_name"],
            "email": payment["voter_email"],
            "phone": payment["voter_phone"],
            "gateway": payment["gateway"],
        }


def initialize_payment(data: dict[str, Any]) -> dict[str, Any]:
    contestant_id = str(data.get("contestant_id") or "").strip()
    package_id = data.get("package_id")
    package_id = str(package_id).strip() if package_id else None
    voter_name = str(data.get("voter_name") or "").strip()
    voter_email = str(data.get("voter_email") or "").strip() or None
    voter_phone = str(data.get("voter_phone") or "").strip() or None
    requested_votes = int(data.get("votes") or 0)

    if not contestant_id:
        raise ValueError("contestant_id is required")
    if not voter_name:
        raise ValueError("voter_name is required")
    if not voter_email and not voter_phone:
        raise ValueError("voter_email or voter_phone is required")
    if requested_votes < 1:
        raise ValueError("votes must be greater than zero")

    with connect() as conn:
        contest = conn.execute("select * from contests where id = ?", (CONTEST_ID,)).fetchone()
        if not contest or contest["status"] != "open":
            raise ValueError("Voting is not open for this contest")
        contestant = conn.execute("select * from contestants where id = ? and contest_id = ? and is_active = 1", (contestant_id, CONTEST_ID)).fetchone()
        if not contestant:
            raise ValueError("Contestant not found or inactive")

        package = None
        if package_id:
            package = conn.execute("select * from vote_packages where id = ? and contest_id = ? and is_active = 1", (package_id, CONTEST_ID)).fetchone()
            if not package:
                raise ValueError("Vote package not found")
            votes = int(package["votes"])
            amount_kobo = int(package["amount_kobo"])
        else:
            votes = requested_votes
            amount_kobo = votes * int(contest["vote_price_kobo"])

        reference = make_reference()
        created_at = now_iso()
        callback_url = f"{FRONTEND_URL}/payment-success.html?reference={urllib.parse.quote(reference)}"
        conn.execute(
            "insert into payments (reference, contest_id, contestant_id, package_id, voter_name, voter_email, voter_phone, amount_kobo, votes_purchased, gateway, status, authorization_url, raw_gateway_payload, created_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', '', '{}', ?)",
            (reference, CONTEST_ID, contestant_id, package_id, voter_name, voter_email, voter_phone, amount_kobo, votes, contest["gateway"], created_at),
        )

    metadata = {
        "contest_id": CONTEST_ID,
        "contestant_id": contestant_id,
        "package_id": package_id,
        "votes": votes,
        "voter_name": voter_name,
        "voter_phone": voter_phone,
    }

    if not PAYSTACK_SECRET_KEY:
        if not ALLOW_DEV_PAYMENTS:
            raise RuntimeError("PAYSTACK_SECRET_KEY is not configured")
        simulation_url = f"{FRONTEND_URL}/api/dev/payments/simulate-success?reference={urllib.parse.quote(reference)}"
        with connect() as conn:
            conn.execute("update payments set authorization_url = ? where reference = ?", (simulation_url, reference))
        return {
            "reference": reference,
            "authorization_url": simulation_url,
            "dev_mode": True,
            "message": "PAYSTACK_SECRET_KEY is not configured, so this local MVP returned a dev simulation URL.",
        }

    payload = {
        "email": voter_email or f"{reference.lower()}@no-email.trevvote.local",
        "amount": amount_kobo,
        "reference": reference,
        "callback_url": callback_url,
        "metadata": metadata,
    }
    result = paystack_request("POST", "/transaction/initialize", payload)
    authorization_url = result["data"]["authorization_url"]
    access_code = result["data"].get("access_code")
    with connect() as conn:
        conn.execute("update payments set authorization_url = ? where reference = ?", (authorization_url, reference))
    return {"reference": reference, "authorization_url": authorization_url, "access_code": access_code, "dev_mode": False}


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = [row[1] for row in conn.execute(f"pragma table_info({table})").fetchall()]
    if column not in columns:
        conn.execute(f"alter table {table} add column {column} {definition}")


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 210_000)
    return f"pbkdf2_sha256$210000${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, rounds, salt, digest = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(rounds)).hex()
        return hmac.compare_digest(candidate, digest)
    except Exception:
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def seed_default_admin(conn: sqlite3.Connection) -> None:
    count = conn.execute("select count(*) from admins").fetchone()[0]
    if count:
        return
    admin_id = f"adm_{secrets.token_hex(8)}"
    conn.execute(
        "insert into admins (id, email, name, password_hash, role, is_active, created_at) values (?, ?, ?, ?, ?, 1, ?)",
        (admin_id, ADMIN_EMAIL, "Platform Admin", hash_password(ADMIN_PASSWORD), ADMIN_ROLE, now_iso()),
    )


def audit(conn: sqlite3.Connection, admin_id: str | None, action: str, details: dict[str, Any] | None = None) -> None:
    conn.execute(
        "insert into audit_logs (admin_id, action, details, created_at) values (?, ?, ?, ?)",
        (admin_id, action, json.dumps(details or {}, ensure_ascii=False), now_iso()),
    )


def get_auth_token(handler: BaseHTTPRequestHandler) -> str | None:
    auth = handler.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    token = handler.headers.get("X-Admin-Token")
    return token.strip() if token else None


def require_admin(handler: BaseHTTPRequestHandler, roles: set[str] | None = None) -> sqlite3.Row:
    token = get_auth_token(handler)
    if not token:
        raise PermissionError("Admin login required")
    hashed = token_hash(token)
    now_ts = int(time.time())
    with connect() as conn:
        row = conn.execute(
            "select admins.* from admin_sessions join admins on admins.id = admin_sessions.admin_id where admin_sessions.token_hash = ? and admin_sessions.expires_at > ? and admins.is_active = 1",
            (hashed, now_ts),
        ).fetchone()
    if not row:
        raise PermissionError("Invalid or expired admin session")
    if roles and row["role"] not in roles:
        raise PermissionError("Your role does not allow this action")
    return row


def csv_response(handler: BaseHTTPRequestHandler, filename: str, rows: list[dict[str, Any]], headers: list[str]) -> None:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in headers})
    body = output.getvalue().encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/csv; charset=utf-8")
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def text_response(handler: BaseHTTPRequestHandler, filename: str, content: str) -> None:
    body = content.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def admin_login(data: dict[str, Any]) -> dict[str, Any]:
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    if not email or not password:
        raise ValueError("Email and password are required")
    with connect() as conn:
        admin = conn.execute("select * from admins where email = ? and is_active = 1", (email,)).fetchone()
        if not admin or not verify_password(password, admin["password_hash"]):
            raise ValueError("Invalid admin credentials")
        token = secrets.token_urlsafe(40)
        expires_at = int(time.time()) + SESSION_TTL_SECONDS
        conn.execute(
            "insert into admin_sessions (token_hash, admin_id, created_at, expires_at) values (?, ?, ?, ?)",
            (token_hash(token), admin["id"], now_iso(), expires_at),
        )
        audit(conn, admin["id"], "admin.login", {"email": email})
    return {
        "token": token,
        "admin": {"id": admin["id"], "email": admin["email"], "name": admin["name"], "role": admin["role"]},
        "expiresAt": expires_at,
    }


def create_contestant(data: dict[str, Any], admin: sqlite3.Row) -> dict[str, Any]:
    name = str(data.get("name") or "").strip()
    code = str(data.get("code") or "").strip()
    category = str(data.get("category") or "General").strip() or "General"
    region = str(data.get("region") or "Client campaign").strip() or "Client campaign"
    bio = str(data.get("bio") or "New contestant added from admin dashboard.").strip()
    if not name:
        raise ValueError("Contestant name is required")
    with connect() as conn:
        count = conn.execute("select count(*) from contestants where contest_id = ?", (CONTEST_ID,)).fetchone()[0]
        contestant_id = f"c{int(time.time() * 1000)}"
        code = code or f"CI-{count + 1:03d}"
        gradients = [
            "linear-gradient(135deg, #8b5cf6, #22d3ee)",
            "linear-gradient(135deg, #ff7a90, #f59e0b)",
            "linear-gradient(135deg, #2ee59d, #16a34a)",
            "linear-gradient(135deg, #ec4899, #6366f1)",
        ]
        gradient = gradients[count % len(gradients)]
        conn.execute(
            "insert into contestants (id, contest_id, name, code, category, region, bio, vote_count, gradient, created_at, is_active, photo_url) values (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 1, null)",
            (contestant_id, CONTEST_ID, name, code, category, region, bio, gradient, int(time.time())),
        )
        audit(conn, admin["id"], "contestant.create", {"contestant_id": contestant_id, "name": name})
    return {"ok": True, "contestantId": contestant_id, "contest": contest_payload()}


def delete_contestant(contestant_id: str, admin: sqlite3.Row) -> dict[str, Any]:
    with connect() as conn:
        contestant = conn.execute("select * from contestants where id = ? and contest_id = ?", (contestant_id, CONTEST_ID)).fetchone()
        if not contestant:
            raise ValueError("Contestant not found")
        conn.execute("update contestants set is_active = 0 where id = ?", (contestant_id,))
        audit(conn, admin["id"], "contestant.delete", {"contestant_id": contestant_id, "name": contestant["name"]})
    return {"ok": True, "contest": contest_payload()}


def update_settings(data: dict[str, Any], admin: sqlite3.Row) -> dict[str, Any]:
    title = str(data.get("title") or "").strip() or "Campus Icons Awards 2026"
    vote_price = int(data.get("votePrice") or data.get("vote_price") or 100)
    gateway = str(data.get("gateway") or "paystack").strip().lower()
    status = str(data.get("status") or "open").strip().lower()
    show_live_results = data.get("showLiveResults", data.get("show_live_results", True))
    show_live_results = 0 if show_live_results in (False, "false", "False", "0", 0) else 1
    if vote_price < 50:
        raise ValueError("Vote price must be at least ₦50")
    if status not in {"draft", "open", "paused", "closed"}:
        raise ValueError("Invalid contest status")
    with connect() as conn:
        conn.execute(
            "update contests set title = ?, vote_price_kobo = ?, gateway = ?, status = ?, show_live_results = ? where id = ?",
            (title, vote_price * 100, gateway, status, show_live_results, CONTEST_ID),
        )
        audit(conn, admin["id"], "contest.settings.update", {"title": title, "votePrice": vote_price, "gateway": gateway, "status": status, "showLiveResults": bool(show_live_results)})
    return {"ok": True, "contest": contest_payload()}


def save_contestant_photo(contestant_id: str, data: dict[str, Any], admin: sqlite3.Row) -> dict[str, Any]:
    filename = str(data.get("filename") or "photo.jpg").strip().lower()
    content_type = str(data.get("content_type") or "").strip().lower()
    raw = str(data.get("data") or "")
    if raw.startswith("data:"):
        header, raw = raw.split(",", 1)
        if not content_type and ";" in header:
            content_type = header.split(":", 1)[1].split(";", 1)[0]
    allowed = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    ext = allowed.get(content_type)
    if not ext:
        suffix = Path(filename).suffix.lower()
        ext = suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else None
    if not ext:
        raise ValueError("Only JPG, PNG and WebP photos are allowed")
    if ext == ".jpeg":
        ext = ".jpg"
    try:
        blob = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise ValueError("Invalid base64 image data") from exc
    if len(blob) > MAX_PHOTO_BYTES:
        raise ValueError("Photo is too large")
    with connect() as conn:
        contestant = conn.execute("select * from contestants where id = ? and contest_id = ? and is_active = 1", (contestant_id, CONTEST_ID)).fetchone()
        if not contestant:
            raise ValueError("Contestant not found")
        photo_dir = MEDIA_DIR / "contestants"
        photo_dir.mkdir(parents=True, exist_ok=True)
        photo_name = f"{contestant_id}_{int(time.time())}{ext}"
        photo_path = photo_dir / photo_name
        photo_path.write_bytes(blob)
        photo_url = f"/media/contestants/{photo_name}"
        conn.execute("update contestants set photo_url = ? where id = ?", (photo_url, contestant_id))
        audit(conn, admin["id"], "contestant.photo.upload", {"contestant_id": contestant_id, "photo_url": photo_url})
    return {"ok": True, "photoUrl": photo_url, "contest": contest_payload()}


def report_summary() -> dict[str, Any]:
    with connect() as conn:
        total_revenue = conn.execute("select coalesce(sum(amount_kobo),0) from payments where contest_id = ? and status = 'successful'", (CONTEST_ID,)).fetchone()[0]
        tx_count = conn.execute("select count(*) from payments where contest_id = ? and status = 'successful'", (CONTEST_ID,)).fetchone()[0]
        total_votes = conn.execute("select coalesce(sum(votes_purchased),0) from payments where contest_id = ? and status = 'successful'", (CONTEST_ID,)).fetchone()[0]
        top = conn.execute("select name, vote_count from contestants where contest_id = ? and is_active = 1 order by vote_count desc limit 1", (CONTEST_ID,)).fetchone()
    return {
        "totalRevenue": ngn_from_kobo(total_revenue),
        "transactions": tx_count,
        "votesSold": total_votes,
        "topContestant": {"name": top["name"], "votes": top["vote_count"]} if top else None,
    }

def daily_report_text() -> str:
    with connect() as conn:
        contest = conn.execute("select * from contests where id = ?", (CONTEST_ID,)).fetchone()
        successful = conn.execute("select coalesce(sum(amount_kobo),0), coalesce(sum(votes_purchased),0), count(*) from payments where contest_id = ? and status = 'successful'", (CONTEST_ID,)).fetchone()
        failed = conn.execute("select count(*) from payments where contest_id = ? and status in ('failed', 'abandoned')", (CONTEST_ID,)).fetchone()[0]
        top = conn.execute("select name, code, vote_count from contestants where contest_id = ? and is_active = 1 order by vote_count desc limit 5", (CONTEST_ID,)).fetchall()
    lines = [
        f"{contest['title']} - Daily Voting Report",
        f"Date: {now_iso()}",
        f"Total revenue: NGN {ngn_from_kobo(successful[0]):,}",
        f"Total votes: {successful[1]:,}",
        f"Successful transactions: {successful[2]:,}",
        f"Failed payments: {failed:,}",
        "",
        "Top contestants:",
    ]
    lines.extend([f"{idx}. {row['name']} ({row['code']}) - {row['vote_count']:,} votes" for idx, row in enumerate(top, start=1)])
    return "\n".join(lines) + "\n"


def export_payments_rows() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            select payments.reference, payments.created_at, payments.status, payments.voter_name, payments.voter_email,
                   payments.voter_phone, contestants.name as contestant, payments.votes_purchased,
                   payments.amount_kobo, payments.gateway
            from payments
            left join contestants on contestants.id = payments.contestant_id
            where payments.contest_id = ?
            order by payments.created_at desc
            """,
            (CONTEST_ID,),
        ).fetchall()
    return [
        {
            "reference": r["reference"],
            "created_at": r["created_at"],
            "status": r["status"],
            "voter_name": r["voter_name"],
            "voter_email": r["voter_email"],
            "voter_phone": r["voter_phone"],
            "contestant": r["contestant"],
            "votes": r["votes_purchased"],
            "amount_ngn": ngn_from_kobo(r["amount_kobo"]),
            "gateway": r["gateway"],
        }
        for r in rows
    ]


def export_contestants_rows() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "select code, name, category, region, vote_count, photo_url, is_active from contestants where contest_id = ? order by vote_count desc",
            (CONTEST_ID,),
        ).fetchall()
    return [dict(r) for r in rows]


class Handler(BaseHTTPRequestHandler):
    server_version = "TrevVoteMVP/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type, authorization, x-admin-token, x-paystack-signature")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/health":
                return json_response(self, 200, {"ok": True, "gatewayConfigured": bool(PAYSTACK_SECRET_KEY), "devPayments": ALLOW_DEV_PAYMENTS})
            if path == "/api/contest":
                return json_response(self, 200, contest_payload())
            if path == "/api/admin/me":
                admin = require_admin(self)
                return json_response(self, 200, {"admin": {"id": admin["id"], "email": admin["email"], "name": admin["name"], "role": admin["role"]}})
            if path == "/api/admin/reports/summary":
                require_admin(self, {"super_admin", "client_admin", "viewer"})
                return json_response(self, 200, report_summary())
            if path == "/api/admin/reports/payments.csv":
                require_admin(self, {"super_admin", "client_admin", "viewer"})
                rows = export_payments_rows()
                return csv_response(self, "trevvote-payments.csv", rows, ["reference", "created_at", "status", "voter_name", "voter_email", "voter_phone", "contestant", "votes", "amount_ngn", "gateway"])
            if path == "/api/admin/reports/contestants.csv":
                require_admin(self, {"super_admin", "client_admin", "viewer"})
                rows = export_contestants_rows()
                return csv_response(self, "trevvote-contestants.csv", rows, ["code", "name", "category", "region", "vote_count", "photo_url", "is_active"])
            if path == "/api/admin/reports/daily.txt":
                require_admin(self, {"super_admin", "client_admin", "viewer"})
                return text_response(self, "trevvote-daily-report.txt", daily_report_text())
            if path.startswith("/api/payments/verify/"):
                reference = urllib.parse.unquote(path.rsplit("/", 1)[-1])
                return self.handle_verify(reference)
            if path == "/api/dev/payments/simulate-success":
                return self.handle_dev_simulate(parsed)
            return self.serve_static(path)
        except Exception as exc:  # noqa: BLE001
            return json_response(self, 500, {"error": str(exc)})

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/payments/initialize":
                data, _body = read_json(self)
                result = initialize_payment(data)
                return json_response(self, 200, result)
            if path == "/api/payments/webhook/paystack":
                return self.handle_paystack_webhook()
            if path == "/api/admin/login":
                data, _body = read_json(self)
                return json_response(self, 200, admin_login(data))
            if path == "/api/admin/logout":
                return self.handle_admin_logout()
            if path == "/api/admin/contestants":
                admin = require_admin(self, {"super_admin", "client_admin"})
                data, _body = read_json(self)
                return json_response(self, 200, create_contestant(data, admin))
            if path == "/api/admin/settings":
                admin = require_admin(self, {"super_admin", "client_admin"})
                data, _body = read_json(self)
                return json_response(self, 200, update_settings(data, admin))
            if path.startswith("/api/admin/contestants/") and path.endswith("/photo"):
                admin = require_admin(self, {"super_admin", "client_admin"})
                contestant_id = urllib.parse.unquote(path.split("/")[4])
                data, _body = read_json(self)
                return json_response(self, 200, save_contestant_photo(contestant_id, data, admin))
            return json_response(self, 404, {"error": "Not found"})
        except PermissionError as exc:
            return json_response(self, 403, {"error": str(exc)})
        except ValueError as exc:
            return json_response(self, 400, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            return json_response(self, 500, {"error": str(exc)})

    def do_DELETE(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            if path.startswith("/api/admin/contestants/"):
                admin = require_admin(self, {"super_admin", "client_admin"})
                contestant_id = urllib.parse.unquote(path.rsplit("/", 1)[-1])
                return json_response(self, 200, delete_contestant(contestant_id, admin))
            return json_response(self, 404, {"error": "Not found"})
        except PermissionError as exc:
            return json_response(self, 403, {"error": str(exc)})
        except ValueError as exc:
            return json_response(self, 400, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            return json_response(self, 500, {"error": str(exc)})

    def handle_admin_logout(self) -> None:
        token = get_auth_token(self)
        if token:
            with connect() as conn:
                conn.execute("delete from admin_sessions where token_hash = ?", (token_hash(token),))
        return json_response(self, 200, {"ok": True})

    def handle_verify(self, reference: str) -> None:
        with connect() as conn:
            payment = conn.execute("select * from payments where reference = ?", (reference,)).fetchone()
        if not payment:
            return json_response(self, 404, {"error": "Payment not found"})

        if payment["status"] == "successful":
            result = process_successful_payment(reference)
            return json_response(self, 200, {**result, "contest": contest_payload()})

        if not PAYSTACK_SECRET_KEY:
            return json_response(self, 200, {
                "reference": reference,
                "status": payment["status"],
                "dev_mode": True,
                "votes": payment["votes_purchased"],
                "amount": ngn_from_kobo(payment["amount_kobo"]),
                "createdAt": payment["created_at"],
                "processedAt": payment["processed_at"],
                "voter": payment["voter_name"],
                "gateway": payment["gateway"],
            })

        tx = verify_paystack_transaction(reference)
        if tx.get("status") == "success":
            result = process_successful_payment(reference, tx)
            return json_response(self, 200, {**result, "contest": contest_payload()})
        return json_response(self, 200, {"reference": reference, "status": tx.get("status", "pending")})

    def handle_dev_simulate(self, parsed: urllib.parse.ParseResult) -> None:
        if not ALLOW_DEV_PAYMENTS:
            return json_response(self, 403, {"error": "Dev payments are disabled"})
        query = urllib.parse.parse_qs(parsed.query)
        reference = (query.get("reference") or [""])[0]
        if not reference:
            return json_response(self, 400, {"error": "Missing reference"})
        with connect() as conn:
            payment = conn.execute("select * from payments where reference = ?", (reference,)).fetchone()
        if not payment:
            return json_response(self, 404, {"error": "Payment not found"})
        fake_payload = {"status": "success", "reference": reference, "amount": payment["amount_kobo"], "metadata": {"dev": True}}
        process_successful_payment(reference, fake_payload)
        redirect(self, f"{FRONTEND_URL}/payment-success.html?reference={urllib.parse.quote(reference)}&dev=1")

    def handle_paystack_webhook(self) -> None:
        data, body = read_json(self)
        signature = self.headers.get("x-paystack-signature")
        if not PAYSTACK_SECRET_KEY:
            return json_response(self, 500, {"error": "PAYSTACK_SECRET_KEY is not configured"})
        expected = hmac.new(PAYSTACK_SECRET_KEY.encode("utf-8"), body, hashlib.sha512).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
            return json_response(self, 401, {"error": "Invalid Paystack signature"})

        event = data.get("event")
        if event != "charge.success":
            return json_response(self, 200, {"ok": True, "ignored": event})

        reference = data.get("data", {}).get("reference")
        if not reference:
            return json_response(self, 400, {"error": "Missing transaction reference"})

        tx = verify_paystack_transaction(reference)
        if tx.get("status") != "success":
            return json_response(self, 200, {"ok": True, "ignored": "transaction_not_successful", "status": tx.get("status")})
        result = process_successful_payment(reference, tx)
        return json_response(self, 200, {"ok": True, **result})

    def serve_static(self, path: str) -> None:
        if path == "/":
            path = "/index.html"
        safe_path = Path(urllib.parse.unquote(path.lstrip("/"))).as_posix()
        if safe_path.startswith("../") or "/../" in safe_path:
            self.send_error(403)
            return
        file_path = ROOT / safe_path
        if file_path.is_dir():
            file_path = file_path / "index.html"
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        content_type = "text/plain; charset=utf-8"
        if file_path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif file_path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif file_path.suffix == ".pdf":
            content_type = "application/pdf"
        elif file_path.suffix.lower() in {".jpg", ".jpeg"}:
            content_type = "image/jpeg"
        elif file_path.suffix.lower() == ".png":
            content_type = "image/png"
        elif file_path.suffix.lower() == ".webp":
            content_type = "image/webp"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    init_db()
    print(f"TrevVote MVP backend running at http://{HOST}:{PORT}")
    if PAYSTACK_SECRET_KEY:
        print("Paystack: configured")
    else:
        print("Paystack: not configured; dev payment simulation is", "enabled" if ALLOW_DEV_PAYMENTS else "disabled")
    print(f"Database: {DB_PATH}")
    print(f"Default admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD if ADMIN_PASSWORD == 'admin12345' else '[from ADMIN_PASSWORD env]'}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
