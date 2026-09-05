# 05. Build Phases

Every phase ends in a verified Git commit. A later phase may refine an earlier
integration boundary, but it may not bypass an earlier correctness gate.

## Phase 1 — isolated CPMM engine

- Implement decimal-only `buy_shares` and `get_prices` functions with no framework or
  database imports.
- Property-test constant-product preservation, price direction, inventory bounds, path
  independence, and monotonic slippage.
- Gate: pytest, Ruff, and strict mypy pass for the AMM module.

Commit: `phase 1: implement and verify CPMM engine`

## Phase 2 — persistence, identity, and groups

- Add SQLAlchemy models and a reversible Alembic initial revision.
- Add authentication, user balances derived from the ledger, groups, invites, roles,
  and retained membership-removal state.
- Test Alembic upgrade, model/schema drift check, database scope constraints, API auth,
  group membership, and downgrade to base.
- Gate: full backend pytest, Ruff, strict mypy, and migration checks pass.

Commit: `phase 2: add persistence auth and groups`

## Phase 3 — transactional market core

- Add mutually exclusive group/public bet APIs, visibility allow-lists, trade preview,
  atomic purchases, positions, cancellation refunds, audited end-time edits, resolution
  resolution audit events, refills, and realized-P/L leaderboards.
- Prove group/public leaderboard isolation with integration tests.
- Prove a removed member sees only markets where they already hold a position until
  those markets settle.
- Gate: full backend suite, lint, types, Alembic drift check, and PostgreSQL offline DDL
  compilation pass.

Commit: `phase 3: implement markets trading and leaderboards`

## Phase 4 — frontend and cross-stack handoff

- Add Next.js authentication, group/public feeds, creation flows, API-driven preview and
  trade ticket, settlement controls, audit history, removed-member messaging, and
  clearly scoped leaderboards.
- Add environment templates and exact local run instructions.
- Gate: backend suite plus frontend TypeScript, ESLint, Vitest, production build, and
  production-dependency audit pass.

Commit: `phase 4: add complete Next.js client`

## Phase 5 — local deployment

- Add a backend-owned Compose stack for PostgreSQL, migrations, and the API only; run
  the Next.js client separately.
- Gate: Compose configuration validates and the API waits for a successful migration.

Commit: `phase 5: dockerize API and PostgreSQL`

## Phase 6 — isolated LMSR engine

- Add numerically stable binary LMSR cost, price, signed quote, and maximum-loss
  functions without framework or database access.
- Property-test reversibility, bounded loss, price conservation, and extreme ratios.
- Retain CPMM math solely for historical markets.

Commit: `phase 6: add verified LMSR pricing engine`

## Phase 7 — transactional LMSR and house persistence

- Add reversible ORM/migration changes for LMSR state, positions, immutable trades,
  and the append-only house ledger.
- Make every new market LMSR, reserve `b * ln(2)`, execute signed trades atomically,
  pay resolution shares, support cancellation, and expose market/group/
  global house summaries.
- Gate: concurrency, migration, resolution-bound, accounting, backend lint, and type
  checks pass.

Commit: `phase 7: persist LMSR trades and house accounting`

## Phase 8 — LMSR client and documentation

- Add live price polling, debounced signed quotes, buy/sell controls, trade audit, market
  house figures, and per-market liquidity creation input.
- Replace the retired CPMM plan with the implemented LMSR mechanism, lifecycle, schema,
  API contract, and house-accounting semantics.
- Gate: full backend and frontend suites, migration checks, production build, and audit.

Commit: `phase 8: ship LMSR trading UI and documentation`

## Phase 15 — paginated, filterable market feeds

- Add a shared paginated response contract to group and public bet APIs with optional
  `open`, `closed`, and `resolved` filtering.
- Apply group visibility before totals/page slicing and refresh time-closed status before
  filtering.
- Add shared frontend status and Previous/Next controls to both feeds.
- Gate: full backend/frontend tests, lint, types, and production build.

Commit: `phase 15: paginate and filter market feeds`

## Phase 18 — verified email auth and group notifications

- Add short-lived, HMAC-hashed registration and password-reset challenges; issue auth
  tokens only after backend verification and keep OTPs out of every API response.
- Add in-app notification persistence, read state, email preferences, a durable SMTP
  outbox, and a retrying background worker.
- Emit group bet created/closed/resolution-reminder/resolved/refunded events while hard
  excluding public bets from both in-app and email delivery.
- Add signup verification, forgot-password, alerts, unread badge, preferences, Compose
  worker, and Cloudflare Email Sending setup documentation.
- Gate: migration upgrade/downgrade and offline DDL, auth abuse cases, lifecycle/public
  exclusion integration tests, backend lint/types/tests, frontend lint/types/tests/build,
  and Compose validation.

Commits: `phase 18: add secure email auth and notifications` and
`phase 18: add notification and recovery UI`

## Phase 24 — durable group and bet images

- Add authenticated multipart image upload with size and file-signature validation.
- Add optional managed image paths to groups and bets through Alembic revision `0004`.
- Persist uploaded media in a Docker named volume and serve it from `/media`.
- Add reusable image selection/preview UI and responsive covers to group and bet cards
  and detail pages.
- Gate: migration checks, backend lint/types/tests, frontend lint/types/tests/build, and
  Compose validation.

Commit: `phase 24: add group and bet cover images`
