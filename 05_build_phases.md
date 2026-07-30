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
  corrections, refills, and realized-P/L leaderboards.
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

