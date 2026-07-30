# Friend-Group Prediction Market we name it BullyMarket — Plan Index

This is a 6-document build plan intended to be handed to a coding agent as-is. Read in
this order:

1. **`01_overview_and_mechanism.md`** — what the app is, and the full specification of
   the betting math (why it's an AMM, not Polymarket's current order book, and the exact
   formulas plus required unit tests). Read this first and read it in full; almost every
   later document refers back to it.
2. **`02_data_model.md`** — Postgres schema, with the reasoning behind the append-only
   ledger design and the outcomes-as-a-table design.
3. **`03_backend_architecture.md`** — FastAPI modular monolith structure, module
   boundary rules, logging strategy.
4. **`04_frontend_architecture.md`** — Next.js structure mirroring the backend modules,
   and the rule against reimplementing AMM math client-side.
5. **`05_build_phases.md`** — the actual build order, with a testing gate at every phase.
   Start here once the design docs above are read; this is the "what do I do first"
   document.
6. **`06_open_questions_and_config.md`** — config values to externalize, the explicit
   v1/v2 feature boundary, and a short list of real product questions to confirm with
   the user rather than silently guess at.

## One thing to know about how this plan was written

While deriving the AMM formula in document 1, an early draft got the pool-update
direction backwards, and a first attempt at correcting it introduced a second, different
incorrect claim into the unit-test spec. Both were only caught by actually executing the
math and checking it against expected numbers — not by re-reading the reasoning more
carefully. Rather than smooth this over, document 1 keeps a visible trace of it, and
`05_build_phases.md`'s Phase 1 gate exists specifically because of it: **the betting math
must be built and property-tested in complete isolation, and proven correct, before
anything else in the system is built on top of it.** This is the single highest-leverage
practice in this whole plan — the rest of the app (auth, groups, CRUD) is comparatively
low-risk and forgiving of mistakes; the payout math is not.

## Stack summary

- Backend: Python, FastAPI, PostgreSQL (async SQLAlchemy + Alembic), pytest.
- Frontend: Next.js (App Router), TypeScript, Tailwind, React Query.
- No real money, ever. Points only.
