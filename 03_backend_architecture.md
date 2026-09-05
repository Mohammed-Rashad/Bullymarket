# 03. Backend Architecture

Stack: **Python, FastAPI, PostgreSQL (via async SQLAlchemy + Alembic), pytest.**

Structure: **modular monolith**, not microservices. One deployable app, but with strict
internal module boundaries so each piece is independently understandable, testable, and
(if it ever needed to) separable later. This was an explicit tradeoff discussed and
chosen over real microservices: microservices would genuinely give lower coupling, but
at a cost (network calls between services, distributed transactions for the ledger,
deployment complexity) that isn't justified at friend-group scale and directly conflicts
with the "keep everything simple" requirement. A modular monolith gets most of the
coupling benefit for a fraction of the complexity cost.

---

## 1. The module boundary rule

Every module below is a Python package under `app/modules/`. The rule that keeps
coupling low:

> **A module may import another module's public interface (its `service.py`), but never
> another module's internals (its `models.py` internals beyond what's exposed, its
> `repository.py`, its private helpers).** Cross-module calls go through function calls
> in the same process (not HTTP), but they go through a defined service function, not a
> raw DB query reaching into another module's tables.

Concretely: the `leaderboard` module needs data that lives in `ledger_entries` (owned by
the `ledger` module) and `group_members` (owned by the `groups` module). It does **not**
write raw SQL against those tables itself. It calls `ledger_service.get_entries_for_range
(...)`, `groups_service.get_group_member_ids(...)`, and the `bets` service's explicitly
scoped group/public bet selectors. The leaderboard service must always receive a
concrete scope; there is no "all bets everywhere" fallback. This is what "low coupling"
concretely means here — not zero dependencies (impossible in a real app), but
dependencies that go through a stable, intentional interface instead of reaching
through each other's internals. It also means each module's tests can mock the *service*
functions of modules it depends on, instead of needing a full DB with every other
module's tables populated just to test leaderboard math.

## 2. Module list

```
app/
  modules/
    auth/          # login, email-verified signup, password reset, JWT issuance
    users/          # user profile, points balance (reads the ledger)
    groups/          # groups, membership, admin roles, invites
    bets/          # bet creation, visibility rules, listing, status transitions
    amm/          # pure LMSR and historical CPMM math — NO db access
    trading/          # signed LMSR trades: AMM + balances + positions + audit
    house/          # market/group/global house accounting read models
    resolution/          # one-time final settlement and resolution_events
    ledger/          # the ledger_entries table: append entries, compute balances
    leaderboard/          # read-only aggregation queries over ledger + groups + bets
    refill/          # the scheduled job that adds the periodic points refill
    notifications/          # in-app events, preferences, email outbox + worker
    media/          # authenticated, signature-validated image uploads
  core/
    db.py          # async engine/session setup, shared by all modules
    config.py          # env-based settings (pydantic-settings)
    logging.py          # structured logging setup, see section 4
    security.py          # password hashing, JWT helpers shared by auth
  api/
    router.py          # mounts each module's router under a versioned prefix
  tests/
    (mirrors modules/ structure — see 05_build_phases.md)
  main.py
```

### 2.1 Why `amm` is its own module with zero DB access

This is the most important module boundary in the whole system, and it's worth being
explicit about why. `amm/` contains **only** the pure functions from
`01_overview_and_mechanism.md` §3 — stable `cost`, `prices`, `quote_trade`, and
`max_house_loss` functions over `Decimal` quantities. The old CPMM functions remain
isolated only so historical markets stay readable. There is no database session,
FastAPI dependency, or import from another application module: pure math in, pure math
out.

This isn't just tidiness. It's what makes the property-based tests in §3.8 possible to
run in milliseconds with no test database, no fixtures, no setup — which matters because
those tests are the ones that catch the exact class of bug demonstrated while writing
this plan (a backwards formula, a wrong test assertion — both were caught by running the
math standalone and checking outputs against hand-verified numbers, *before* any of it
touched a database or an API endpoint). If `amm` module code were tangled together with
DB writes, every test of the math would also be a test of the database layer, and a
failure could be either — which is exactly the ambiguity that makes bugs slow to find.
Keep this boundary strict.

The `trading` module uses those pure functions and then, in one transaction, updates
`q_yes`/`q_no`, the position and user ledger, inserts an immutable `trade`, and appends
the matching house-ledger event. `trading` is where math meets persistence; `amm` never
touches the database itself.

### 2.2 Why `ledger` is separate from `users`

`users` owns identity (email, display name, auth). `ledger` owns the append-only
financial history and balance computation (`02_data_model.md`). Keeping them separate
means: (a) any module that needs "what's this user's balance" calls
`ledger_service.get_balance(user_id)`, a single well-tested function, rather than each
module computing it slightly differently; (b) the ledger's correctness (§3.8 item 5's
conservation checks, the resolution-reversal exactness in §3.5) can be tested completely
in isolation from user-profile concerns like display names or password hashing, which
have nothing to do with money-math correctness and shouldn't share a test surface with
it.

### 2.3 Why `resolution` is separate from `bets`

`bets` owns bet creation, editing, visibility, and listing — normal CRUD. `resolution`
owns the specific, higher-stakes action of marking a winner and running payouts.
Settlement is immutable: a resolved bet rejects every later resolution request.
Splitting these means the
higher-risk code (money moves and the immutable audit trail) lives in a small, dedicated
module that's easy to review completely, instead of being one function buried inside a
much larger `bets` module alongside routine CRUD.

### 2.4 Leaderboard and bet-scope boundary

Group and public betting are two mutually exclusive scopes. Group-bet routes and service
methods require a `group_id`; public-bet routes and service methods do not accept one.
The database check in `02_data_model.md` is the final guard, but the service layer must
reject an invalid combination before attempting a write.

Expose two explicit leaderboard operations rather than one loosely filtered operation:

- `get_group_leaderboard(group_id, window)` computes realized net profit/loss only for
  resolved group bets belonging to that exact group.
- `get_public_leaderboard(window)` computes realized net profit/loss only for resolved
  standalone public bets whose `group_id` is null.

Both operations exclude refills, overall wallet balance, unresolved stakes, and
unrelated scopes. The exact ledger-entry and time-window rules are specified in
`02_data_model.md`. Authorization for creating and resolving public bets is a
platform-level policy and must never fall back to "admin of the group it came from,"
because a public bet has no group.

## 3. Module contents (each module's internal shape)

Every module follows the same internal shape, so the pattern only needs to be learned
once:

```
modules/<name>/
  router.py          # FastAPI routes — thin, calls service.py, does request/response shaping only
  service.py          # business logic — the module's public interface for other modules to call
  repository.py          # DB queries for this module's own tables only
  models.py          # SQLAlchemy models for this module's own tables
  schemas.py          # Pydantic request/response models
```

The media module accepts authenticated multipart uploads, reads no more than the
configured maximum plus one byte, validates the file signature instead of trusting its
name or browser content type, and generates an opaque filename. `/media` is a public
static mount because group and bet covers are presentation assets; access to the group
or bet data itself continues to be enforced by its API. The database stores only the
managed path, while Compose keeps the bytes in a persistent named volume.

`router.py` should contain almost no logic — its job is: parse request, call one or two
`service.py` functions, shape the response, done. All the actual decision-making (can
this user see this bet, does resolving this trigger payouts, is the balance sufficient)
lives in `service.py`, where it's unit-testable without spinning up an HTTP server. This
is the standard reason to keep routers thin, and it matters extra here because the
riskiest logic (payout correctness) benefits the most from being testable at the
function-call level rather than only through HTTP integration tests.

## 4. Logging strategy

The user asked for "informative logging to catch bugs" — here's what that means
concretely, not just "add print statements."

- **Structured (JSON) logging**, using Python's standard `logging` module configured to
  output JSON (via `python-json-logger` or similar — a small, well-known library, not a
  custom formatter). Structured logs are filterable/queryable later; plain text logs
  aren't.
- **Every request gets a `request_id`** (generate a UUID in FastAPI middleware, attach
  to the logging context for that request's lifetime). Every log line emitted while
  handling that request includes it. This is what makes "find every log line related to
  this one bug report" possible.
- **Every `trading` and `resolution` action logs a structured event with full context**
  — not just "trade executed" but `{"event": "lmsr_trade", "user_id": ..., "bet_id":
  ..., "side": ..., "delta_shares": ..., "cost": ..., "q_before": {...}, "q_after":
  {...}}`. This is the highest-value logging in the whole system: if a
  balance ever looks wrong, these log lines plus the `ledger_entries` table are what let
  you reconstruct exactly what happened, in order, without guessing. Apply the same
  principle to `resolution` events (log final outcome, affected user count, total
  payout) and to `refill` job runs (log how many users were refilled and by how much,
  each run).
- **Log at module boundaries.** When `trading.service` calls `amm.quote_trade(...)`, log
  the inputs and outputs of that call. This directly supports the module-boundary
  principle from Section 1 — if a bug is on the math side vs. the persistence side, the
  boundary log line tells you which, because you can see exactly what came out of the
  pure function before anything touched the database.
- **Never log secrets** (passwords, tokens) — obvious, but worth stating explicitly
  since it's an easy mistake in a "log everything" mindset. Add a pytest test that scans
  log output from an auth-flow integration test for the raw password string, to catch
  this by accident, not just by code review.
- **Log levels, kept simple:** `INFO` for the structured business events described
  above (bet placed, resolved, refilled — the events you'd want to replay in a bug
  investigation); `WARNING` for handled-but-notable situations (a refill job found zero
  eligible users); `ERROR` for anything caught by an
  exception handler that represents a real bug or failure. Resist the urge to add more
  granular levels — more categories is more decisions to get right and more noise, not
  more signal, for a project this size.

## 5. API layer conventions

- Versioned prefix, e.g. `/api/v1/...`, even though there's only one version now — costs
  nothing today and avoids a painful migration later if the API shape ever needs to
  change while an old frontend build is still in use.
- Every mutating endpoint (`POST`, `PATCH`, `DELETE`) that touches money/points must run
  inside a single DB transaction covering user and house writes. Production PostgreSQL
  takes a row lock on the market before recomputing the quote. The request-scoped DB
  dependency commits or rolls back. SQLite development mode is the deliberate exception:
  it uses a process-local market lock and commits before releasing that lock because
  SQLite ignores `SELECT FOR UPDATE`.
- LMSR routes are explicit: unauthenticated `GET /markets/{id}/price`, read-only
  `GET /markets/{id}/quote`, atomic `POST /markets/{id}/trade`, and ordered
  `GET /markets/{id}/trades`. House routes expose a single market, exact group, or all
  LMSR markets. Historical CPMM endpoints reject LMSR markets rather than mixing math.
- Keep group and public APIs structurally separate:
  `/api/v1/groups/{group_id}/bets` and
  `/api/v1/groups/{group_id}/leaderboard` are group-scoped, while
  `/api/v1/public-bets` and `/api/v1/leaderboards/public` are platform-scoped. A public
  request body must not accept `group_id`, and a group bet must not accept
  `visibility='public'`. This makes accidental cross-scope queries difficult before the
  database constraint is even reached.
- Group and public bet-list operations return the same pagination envelope and accept
  optional status filtering. Group visibility/removal rules are applied before totals
  and page slices, so inaccessible markets never affect a user's pagination metadata.
- Auth: JWT bearer tokens and Argon2 password hashes. Signup first queues a six-digit
  email code; only backend verification creates the user and issues a JWT. Forgot
  password uses the same short-lived, attempt-limited challenge design and does not
  reveal whether an address exists. Codes are never returned to the frontend.
- Notification APIs expose a paginated in-app feed, unread state, and email preferences.
  Lifecycle writes and outbox inserts occur in the same database transaction as the
  group-bet action. The worker closes time-expired group markets, emits idempotent member
  alerts (with a creator-specific resolution reminder), and delivers queued SMTP mail.
  Public-bet paths are hard-excluded before recipient lookup or outbox creation.

## 6. Refill job

The periodic points refill (weekly/monthly, adds to balance per `02_data_model.md`'s
design decision log) is a scheduled job, not something triggered by user requests. For
v1, keep this simple: an APScheduler (or even a basic cron-triggered script) job that
runs daily, checks each user's `last_refill_at` against their configured refill
interval, and inserts a `refill` ledger entry (plus updates `last_refill_at`) for anyone
due. This keeps refill logic in one place, testable independently (call the job function
directly in a test with a fake "now," assert the right ledger entries appear), rather
than trying to compute "is a refill due" inline on every request, which would be both
slower and harder to reason about.
