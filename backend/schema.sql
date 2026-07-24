-- PostgreSQL schema for the paid voting engine.
-- This is the production shape behind the prototype UI.

create extension if not exists pgcrypto;

create table clients (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  brand_name text not null,
  logo_url text,
  primary_color text default '#8b5cf6',
  domain text unique,
  created_at timestamptz not null default now()
);

create table contests (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id) on delete cascade,
  title text not null,
  slug text not null unique,
  description text,
  organizer_name text,
  logo_url text,
  banner_url text,
  vote_price_kobo integer not null default 10000,
  gateway text not null default 'paystack',
  status text not null default 'draft' check (status in ('draft', 'open', 'paused', 'closed')),
  starts_at timestamptz,
  ends_at timestamptz,
  show_live_results boolean not null default true,
  created_at timestamptz not null default now()
);

create table contestants (
  id uuid primary key default gen_random_uuid(),
  contest_id uuid not null references contests(id) on delete cascade,
  name text not null,
  voting_code text not null,
  category text,
  bio text,
  photo_url text,
  vote_count bigint not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (contest_id, voting_code)
);

create table vote_packages (
  id uuid primary key default gen_random_uuid(),
  contest_id uuid not null references contests(id) on delete cascade,
  name text not null,
  votes integer not null check (votes > 0),
  amount_kobo integer not null check (amount_kobo > 0),
  is_featured boolean not null default false,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table payments (
  id uuid primary key default gen_random_uuid(),
  contest_id uuid not null references contests(id) on delete restrict,
  contestant_id uuid not null references contestants(id) on delete restrict,
  package_id uuid references vote_packages(id) on delete set null,
  voter_name text not null,
  voter_email text,
  voter_phone text,
  gateway text not null default 'paystack',
  gateway_reference text not null unique,
  gateway_access_code text,
  amount_kobo integer not null check (amount_kobo > 0),
  votes_purchased integer not null check (votes_purchased > 0),
  status text not null default 'pending' check (status in ('pending', 'successful', 'failed', 'abandoned', 'refunded')),
  processed_at timestamptz,
  raw_gateway_payload jsonb,
  created_at timestamptz not null default now()
);

create table vote_transactions (
  id uuid primary key default gen_random_uuid(),
  payment_id uuid not null unique references payments(id) on delete restrict,
  contest_id uuid not null references contests(id) on delete restrict,
  contestant_id uuid not null references contestants(id) on delete restrict,
  votes_added integer not null check (votes_added > 0),
  created_at timestamptz not null default now()
);

create index contestants_contest_votes_idx on contestants(contest_id, vote_count desc);
create index payments_contest_created_idx on payments(contest_id, created_at desc);
create index payments_status_idx on payments(status);

create table admins (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  name text not null,
  password_hash text not null,
  role text not null default 'client_admin' check (role in ('super_admin', 'client_admin', 'viewer')),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table admin_sessions (
  token_hash text primary key,
  admin_id uuid not null references admins(id) on delete cascade,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);

create table audit_logs (
  id bigserial primary key,
  admin_id uuid references admins(id) on delete set null,
  action text not null,
  details jsonb,
  created_at timestamptz not null default now()
);
