# Database and cloud deployment

## Architecture

The application uses PostgreSQL through SQLAlchemy and Alembic. Supabase is a
supported managed PostgreSQL and authentication provider, not a dependency of
the parser layer.

```text
Supabase Auth → FastAPI JWT verification → Case owner ID
FastAPI → Supabase Postgres → cases / evidence / devices / recordings
Original .dd / DVR export → controlled local or Object-Lock evidence store
Working copy → parser → normalized ParseResult → persistence service
Extracted clips / thumbnails → private derived-media storage
```

`backend/db/services.py` is the boundary between parsers and persistence.
Parsers only return `ParseResult` and `NormalizedRecording` dataclasses.

## Setup

1. Copy `.env.example` to `.env` and set `DATABASE_URL` to the server-side
   Supabase Postgres connection string.
2. Install dependencies: `pip install -r requirements.txt`.
3. Apply the schema: `alembic upgrade head`.
4. Start the API: `uvicorn backend.api.main:app --reload`.

The migration upgrades the project’s prior SQLite development schema when it
finds existing `cases` and `evidence` tables. Back up real case data before any
production migration.

## Auth and authorization

The frontend signs users in with Supabase Auth and sends its access token as
`Authorization: Bearer <token>`. Set `AUTH_REQUIRED=true` and supply
`SUPABASE_JWT_SECRET` **only to the backend**. New cases record the authenticated
Supabase user ID as `owner_auth_id`. When authentication is enabled, the API
also prevents a user from reading or processing a case owned by another user.

Authentication is deliberately optional for local parser tests. Before a
multi-user release, add database Row Level Security policies and API-level role
checks for investigator, reviewer, and administrator roles.

## Evidence and media retention

Original evidence is copied to `ORIGINAL_EVIDENCE_ROOT`, made read-only, and
hashed. It must have a separate retention and backup policy (for example,
on-prem evidence storage or an Object-Lock-capable bucket). Do not use a normal
Supabase Storage bucket as the sole canonical evidence copy.

Supabase Storage is appropriate for private, replaceable derivatives such as
extracted MP4 files, thumbnails, and report assets. Store an object key—not a
public URL—in `recordings.extracted_path`; deliver it through short-lived signed
URLs from the API.
