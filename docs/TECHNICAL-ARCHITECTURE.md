# Technical Architecture

## Overview

A modular monolith hosted on Google Cloud Run, backed by a Neon serverless
Postgres database. The app is a server-rendered FastAPI application using
Jinja2 templates and HTMX for partial updates — no separate SPA frontend.
The single architectural twist is natural-language search, powered by an
embeddings model and `pgvector` running inside the same Neon database.
Listing photos are stored in Google Cloud Storage and served via signed
URLs (or a CDN once traffic warrants it).

A monolith is the right call here: one team's worth of contributors, a
single bounded context (a stuffie marketplace), and a 2-3 month launch
target. Microservices would be premature.

## Technology Stack

### Frontend

- **Framework**: Server-rendered Jinja2 templates + HTMX 2.x (no build step)
- **Styling**: Pico.css via CDN initially; revisit if it gets in the way
- **Interactivity**: HTMX for AJAX, form submission, and fragment swaps
- **Image handling**: Native `<input type="file">` with client-side preview;
  `loading="lazy"` for listing thumbnails

### Backend

- **Runtime**: Python 3.12
- **Framework**: FastAPI + Uvicorn
- **DB layer**: SQLModel + Alembic for migrations
- **Package manager**: uv
- **Testing**: pytest + httpx, with the in-memory SQLite fixture pattern
  documented in `CLAUDE.md`

### Database

- **Primary**: Neon (serverless Postgres) — per-PR branches for ephemeral
  preview environments
- **Vector index**: `pgvector` extension on the same Neon database
  (avoids a second data store; transactional with listings)
- **Cache**: None in v1. Add a small in-process cache (e.g. `cachetools`)
  only if a specific hot path measurably needs it.
- **Search**: Hybrid — `pgvector` similarity over a description embedding +
  Postgres full-text search on title/description, combined at the
  application layer. No Elasticsearch / OpenSearch in v1.

### Storage

- **Listing photos**: Google Cloud Storage bucket. Direct-to-GCS upload via
  V4 signed URLs (server mints the signed URL; browser PUTs the file).
  Avoids streaming uploaded bytes through Cloud Run.
- **Image processing**: A single resize on first read into a `thumbs/`
  prefix is enough for v1. Skip a separate image pipeline.

### Auth

- **MVP**: Email + password with `passlib[bcrypt]`, sessions backed by
  signed cookies (`itsdangerous`). Email verification via a magic-link
  token mailed through SendGrid (or Resend).
- **Out of v1**: Social login, MFA, Google Identity Platform. They're
  one Phase 2 ticket away if needed.

### Infrastructure

- **Hosting**: Cloud Run (single service, scale-to-zero)
- **Container registry**: Artifact Registry
- **Secrets**: Secret Manager (DB URL, embedding API key, mail provider key)
- **CI/CD**: GitHub Actions (already wired in this template)
- **Observability**: Cloud Logging + Error Reporting (option 1 from
  `CLAUDE.md`). Add Sentry only if Cloud-native tooling proves insufficient.

### Background work

- **MVP**: FastAPI `BackgroundTasks` for in-request follow-ups (e.g.
  embedding a listing description after creation). Acceptable because
  these tasks are short and idempotent.
- **Phase 2**: If embedding latency or volume grows, move to Cloud Tasks +
  a dedicated worker Cloud Run service. Don't pre-build it.

## System Design

### Component Diagram

```text
                   +----------------------------+
   Browser  <----> |  Cloud Run: stuffies-app   |
   (HTMX)          |  FastAPI + Jinja2          |
                   |   ├── routes/auth          |
                   |   ├── routes/listings      |
                   |   ├── routes/search        |
                   |   ├── routes/bids          |
                   |   ├── routes/favorites     |
                   |   └── services/embeddings  |
                   +-------------+--------------+
                                 |
                +----------------+----------------+
                |                |                |
                v                v                v
        +---------------+  +-----------+   +-----------------+
        | Neon Postgres |  | GCS bucket|   | Embeddings API  |
        | + pgvector    |  | listings/ |   | (e.g. Voyage,   |
        +---------------+  +-----------+   |  Cohere, OpenAI)|
                                           +-----------------+
                                                    ^
                                                    |
                                           +-----------------+
                                           | Mail provider   |
                                           | (Resend /       |
                                           |  SendGrid)      |
                                           +-----------------+
```

### Data Flow: creating a listing

1. Seller submits the listing form via HTMX `POST /listings`.
2. Server validates, persists the row to Postgres in a transaction, and
   returns a signed GCS URL fragment for the photo upload.
3. Browser PUTs the photo directly to GCS using the signed URL.
4. After commit, FastAPI `BackgroundTasks` requests an embedding for the
   listing's `title + description`, then writes the vector to the
   `listing_embedding` column.
5. The listing is searchable as soon as the embedding lands (typically
   sub-second). Until then it's findable via full-text search only.

### Data Flow: natural-language search

1. Buyer submits a query via HTMX `GET /search?q=...`.
2. Server embeds the query (cached on `q` for 5 minutes to absorb retries).
3. Server runs two queries in parallel:
   - Vector ANN: `ORDER BY listing_embedding <=> :q_vec LIMIT 50`
   - Full-text: `WHERE search_tsv @@ plainto_tsquery(:q)`
4. Application-layer reciprocal-rank fusion merges the two result sets.
5. Server returns an HTMX fragment with the merged results; the page
   shell stays put.

### API Design

REST + HTML fragments. No JSON API for v1 — endpoints return HTML for
HTMX. Internal naming follows resource conventions:

| Method | Path                          | Returns         |
|--------|-------------------------------|-----------------|
| POST   | `/auth/signup`                | redirect + session cookie |
| POST   | `/auth/login`                 | redirect + session cookie |
| POST   | `/auth/logout`                | redirect |
| GET    | `/listings`                   | HTML page (browse) |
| GET    | `/listings/{id}`              | HTML page (detail) |
| POST   | `/listings`                   | HTML fragment (new card) |
| POST   | `/listings/{id}/photo-url`    | JSON (signed upload URL) |
| GET    | `/search?q=...`               | HTML fragment (results) |
| POST   | `/listings/{id}/favorite`     | HTML fragment (heart toggle) |
| DELETE | `/listings/{id}/favorite`     | HTML fragment |
| POST   | `/listings/{id}/bids`         | HTML fragment (bid row) |

## Data Models

### Core Entities

- **User** — email, hashed password, created_at, is_verified.
- **Listing** — owned by a User (seller), has many photos, has many bids,
  has many favorites; stored fields include title, description, era,
  manufacturer, condition, status (`active` / `sold` / `withdrawn`).
- **Photo** — belongs to a Listing; stores the GCS object key, sort order,
  and (after first thumbnail generation) a thumb key.
- **Favorite** — join row between User and Listing.
- **Bid** — belongs to a User and a Listing; amount in cents, currency,
  placed_at, status (`active` / `withdrawn` / `accepted`).
- **ListingEmbedding** — 1:1 with Listing; `pgvector` column + a hash of
  the embedded text so we can detect drift and re-embed only when needed.

### Database Schema (illustrative)

```sql
CREATE TABLE app_user (
    id              BIGSERIAL PRIMARY KEY,
    email           CITEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE listing (
    id              BIGSERIAL PRIMARY KEY,
    seller_id       BIGINT NOT NULL REFERENCES app_user(id),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    era             TEXT,
    manufacturer    TEXT,
    condition       TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    search_tsv      TSVECTOR GENERATED ALWAYS AS (
                       to_tsvector('english',
                           coalesce(title,'') || ' ' || coalesce(description,''))
                    ) STORED
);
CREATE INDEX listing_search_tsv_idx ON listing USING GIN (search_tsv);

CREATE TABLE listing_embedding (
    listing_id      BIGINT PRIMARY KEY REFERENCES listing(id) ON DELETE CASCADE,
    embedding       VECTOR(1024) NOT NULL,
    text_hash       TEXT NOT NULL,
    embedded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX listing_embedding_ann_idx
  ON listing_embedding USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE TABLE photo (
    id              BIGSERIAL PRIMARY KEY,
    listing_id      BIGINT NOT NULL REFERENCES listing(id) ON DELETE CASCADE,
    gcs_key         TEXT NOT NULL,
    thumb_key       TEXT,
    sort_order      INT NOT NULL DEFAULT 0
);

CREATE TABLE favorite (
    user_id         BIGINT NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    listing_id      BIGINT NOT NULL REFERENCES listing(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, listing_id)
);

CREATE TABLE bid (
    id              BIGSERIAL PRIMARY KEY,
    listing_id      BIGINT NOT NULL REFERENCES listing(id) ON DELETE CASCADE,
    bidder_id       BIGINT NOT NULL REFERENCES app_user(id),
    amount_cents    BIGINT NOT NULL CHECK (amount_cents > 0),
    currency        CHAR(3) NOT NULL DEFAULT 'USD',
    status          TEXT NOT NULL DEFAULT 'active',
    placed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX bid_listing_idx ON bid (listing_id, placed_at DESC);
```

Embedding dimension is illustrative (1024). Pin to whatever the chosen
provider returns; locking it down is an ADR.

## Development Standards

### Code Style

- `ruff check .` and `ruff format .` enforced in CI and the pre-push hook.
- `mypy app/` runs in CI; new code should type-check cleanly.
- File / module layout follows the FastAPI starter: `app/api/` for route
  modules, `app/models/` for SQLModel definitions, `app/services/` for
  cross-cutting concerns (embeddings, mail, GCS).
- Naming: `snake_case` for functions and modules, `PascalCase` for models.

### Testing Requirements

- HTTP tests use `TestClient` with the in-memory SQLite session fixture
  pattern from `CLAUDE.md`.
- HTMX endpoints assert on HTML substrings AND
  `assert "<html" not in response.text` to catch the full-page-template
  mistake.
- Search ranking has its own eval: a hand-built set of
  `(query, expected listing IDs)` pairs that must keep passing.
  This guards the differentiator.
- Coverage target: 80% on `app/`, but treat the eval set as the more
  important gate.
- Migrations: every model change ships with an Alembic revision; CI
  runs `alembic upgrade head` against an ephemeral Neon branch.

### Documentation

- ADRs (this file's "Architecture Decision Records" section) for
  decisions that future contributors would otherwise re-litigate.
- Docstrings on public functions in `app/services/`. Routes don't need
  docstrings — the function name + decorator path are enough.

### Code Review

- All PRs reviewed via `pr-reviewer` agent + human merge per `CLAUDE.md`.
- Reviewer checks: tests pass, no `--no-verify`, conventional commit,
  Alembic revision present if models changed, search eval still green.

## Security

### Authentication

Email + password with bcrypt, signed-cookie sessions, magic-link email
verification. Passwords minimum 10 chars; rate-limit login attempts at
the route level (10/min/IP for v1; revisit if attacked).

### Authorization

A listing belongs to its seller. Edit/withdraw is seller-only; bid and
favorite are buyer-only (any authenticated user). No role system in v1
beyond "is the request user the seller of this listing."

### Data Protection

- Secrets via Google Secret Manager, mounted as env vars.
- TLS terminated at Cloud Run (free, automatic).
- No PII beyond email and bcrypt-hashed passwords.
- GCS bucket is private; reads use signed URLs (or eventually a CDN
  with signed URLs).

## Scalability

### Current Targets

- 100 MAU within 3 months. Order-of-magnitude bump (~1k MAU) is still
  trivially served by a single Cloud Run service + Neon free/launch tier.
- Listing volume estimate: low thousands at the 3-month mark.

### Scaling Strategy

- Cloud Run autoscales horizontally; Neon scales vertically and supports
  read replicas if needed.
- `pgvector` with `ivfflat` is fine to roughly 100k listings. Above
  that, switch to `hnsw` (also in `pgvector`) before reaching for an
  external vector DB.
- Move embedding generation off the request path (Cloud Tasks + worker
  Cloud Run service) when (a) embedding latency exceeds ~500ms or
  (b) signups outpace per-request budgets.

## Architecture Decision Records

### ADR-001: Modular monolith on Cloud Run

- **Status**: Accepted (2026-05-01)
- **Context**: Single bounded context, small team, 2-3 month launch
  target, scale-to-zero hosting available.
- **Decision**: One FastAPI service. Internal modules
  (`auth`, `listings`, `search`, `bids`, `favorites`) maintain clean
  boundaries but ship together.
- **Consequences**: Fast iteration, simple deploy, single DB transaction
  surface. Refactor cost rises if the product later grows distinct
  domains; we'll address that when it happens, not before.

### ADR-002: pgvector in Neon for natural-language search

- **Status**: Accepted (2026-05-01)
- **Context**: Natural-language search is the differentiator; we need
  vector similarity. Neon supports `pgvector`. Standing up a separate
  vector DB (Pinecone, Weaviate) adds infra and a second consistency
  story.
- **Decision**: Use `pgvector` on the same Neon database. Store the
  embedding 1:1 with the listing. Combine vector similarity with
  Postgres full-text search at the application layer (reciprocal-rank
  fusion).
- **Consequences**: One data store, transactional consistency between
  listing and embedding, lower ops burden. Trade-off: ANN performance
  caps lower than a dedicated vector DB; mitigated by `hnsw` upgrade
  path. Embedding API outage leaves new listings searchable via
  full-text only — acceptable degradation.

### ADR-003: Signed-URL direct uploads to GCS

- **Status**: Accepted (2026-05-01)
- **Context**: Listings have photos. Streaming bytes through Cloud Run
  burns request CPU and bumps memory ceilings.
- **Decision**: Server mints a V4 signed PUT URL per upload; browser
  uploads directly to GCS. App stores the resulting object key.
- **Consequences**: Cheap, fast uploads. Need a small reconciliation
  step to mark listings without a successfully-uploaded photo as
  draft / hidden until photo lands.

### ADR-004: Email + password auth, defer Identity Platform

- **Status**: Accepted (2026-05-01)
- **Context**: PRD calls for "email login." Identity Platform / social
  login add setup overhead and a dependency we don't yet need.
- **Decision**: Bcrypt + signed-cookie sessions + magic-link email
  verification.
- **Consequences**: Minimal surface, no third-party identity dependency.
  Trade-off: we own password reset and abuse handling. Revisit once
  signups exceed ~1k or a real abuser shows up.

### ADR-005: BackgroundTasks now, Cloud Tasks later

- **Status**: Accepted (2026-05-01)
- **Context**: Embedding generation should not block the seller's
  "create listing" request, but introducing Cloud Tasks on day one
  is over-engineered for a 100-MAU target.
- **Decision**: Use FastAPI `BackgroundTasks` for embedding-on-create
  in v1. Migrate to Cloud Tasks + a worker Cloud Run service when
  embedding latency or volume justifies it.
- **Consequences**: Simple v1; a known migration point in Phase 2.
  Risk: a Cloud Run instance terminating mid-task drops the embedding;
  acceptable because the listing remains searchable via full-text and
  a nightly job can re-embed any listing whose `text_hash` doesn't
  match its current text.
