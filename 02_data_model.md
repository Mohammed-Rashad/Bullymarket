# 02. Data Model

Database: **PostgreSQL**. Chosen over MongoDB because the core of this app is a points
ledger with strict consistency requirements (a user's balance must never be corrupted by
two simultaneous bets, a resolution must never partially apply). Postgres gives us real
transactions and foreign-key integrity for free; with MongoDB we'd have to hand-build
those guarantees ourselves, which is exactly the kind of avoidable complexity this
project is trying to stay away from. Relational tables also fit this domain naturally —
users, groups, bets, and positions all have clear relationships to each other.

Use **SQLAlchemy** (async) as the ORM and **Alembic** for migrations. Every table below
should be a real Alembic migration, not just a SQLAlchemy model with `create_all()` — we
want a migration history from day one so schema changes are reviewable and reversible.

The ORM and the migrations are both required deliverables, not alternatives. SQLAlchemy
models describe the runtime mapping; Alembic revisions are the only mechanism allowed
to create or change the database schema in every environment, including local
development and tests.

---

## Design principle for this schema

Two things drove every choice below:

1. **The ledger must be append-only and auditable.** We never overwrite a balance in
   place with no record of why it changed. Every points movement (bet placed, payout
   received, refill applied, resolution corrected) is its own row in
   `ledger_entries`. A user's current balance is a *derived* value (sum of their ledger
   entries), not a mutable field that things silently write to. This is the single most
   important decision in this document: it's what makes bugs debuggable ("why does Ahmed
   have 340 points" has a real answer you can query) and what makes the "corrected
   resolution reverses cleanly" requirement from `01_overview_and_mechanism.md` §3.5
   actually implementable without special-casing.

2. **Outcomes are a table, not two hardcoded columns.** Even though v1 is 2-outcome-only
   (§3.7), we don't hardcode `pool_yes`/`pool_no` as literal column names on the `bets`
   table. Instead there's an `outcomes` table with a foreign key to `bets`, and v1 simply
   enforces "exactly 2 rows" at the application layer. This is cheap to do now and saves
   a full data migration if multi-outcome bets ever become a real feature — but we are
   **not** building the N-outcome math or UI in v1, only leaving the schema not actively
   hostile to it later.

---

## Tables

### `users`
| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| email | text, unique | |
| display_name | text | |
| password_hash | text | see `03_backend_architecture.md` for auth approach |
| created_at | timestamptz | |
| last_refill_at | timestamptz, nullable | drives the weekly/monthly points refill job, see below |

Balance is **not** a column here. It's derived (see `ledger_entries` below and the
`user_balances` view).

### `groups`
| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| name | text | |
| description | text, nullable | |
| created_by | uuid, fk → users.id | the original creator; always an admin, see `group_members` |
| invite_code | text, unique | short random code for "join a group" flow |
| created_at | timestamptz | |

### `group_members`
| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| group_id | uuid, fk → groups.id | |
| user_id | uuid, fk → users.id | |
| role | enum: `member`, `admin` | the creator's row is `admin` by default; creator can promote others |
| joined_at | timestamptz | |

Unique constraint on `(group_id, user_id)` — can't join the same group twice.

**Why `role` lives on the membership row, not a separate `group_admins` table:** an
admin's admin-ness is inherently scoped to one group (someone can be admin of Group A and
a regular member of Group B), so it belongs on the join table, not as a global flag on
`users`. This is exactly the "who can resolve this bet" check needed for §3.4/3.5.

### `bets`
| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| group_id | uuid, fk → groups.id, nullable | required for a group bet; always null for a standalone public bet |
| created_by | uuid, fk → users.id | |
| question | text | e.g. "Does Ahmed go to the gym this week?" |
| description | text, nullable | optional longer context |
| visibility | enum: `group`, `public` | this is the bet's mutually exclusive scope; see the constraint below |
| status | enum: `open`, `closed`, `resolved` | `closed` = past end_time, awaiting resolution; `resolved` = paid out |
| end_time | timestamptz | betting closes at this time |
| resolved_outcome_id | uuid, fk → outcomes.id, nullable | set once resolved |
| resolved_at | timestamptz, nullable | time of the first resolution; set once and not moved by later corrections, so leaderboard time windows stay stable |
| resolved_by | uuid, fk → users.id, nullable | authorized user responsible for the current winning outcome; a group admin for group bets |
| liquidity_seed | numeric | the `L` value from §3.1, fixed at creation, needed to reconstruct pool state and for the system-owned liquidity-provider position at payout time |
| created_at | timestamptz | |

Add a database `CHECK` constraint named `ck_bets_scope_matches_group`:

```sql
(visibility = 'group' AND group_id IS NOT NULL)
OR
(visibility = 'public' AND group_id IS NULL)
```

This is a hard separation, not a presentation rule. A public bet is a platform-level
bet with no group origin or attribution; it must never appear in a group bet query or
group leaderboard. Conversely, a group bet must always identify exactly one group and
must never appear in the public feed or global leaderboard. Bet scope is immutable from
creation: changing a group bet into a public bet (or the reverse) is not allowed, even
before the first trade. Create a new bet in the intended scope instead.

### `outcomes`
| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| bet_id | uuid, fk → bets.id | |
| label | text | e.g. "Yes" / "No", or custom labels like "Person A" / "Person B" |
| pool_shares | numeric | this is `pool_yes` or `pool_no` from §3.1-3.3, generically named since it's not hardcoded to 2 rows |
| display_order | int | so UI always shows outcomes in a stable order |

Application-layer constraint (not a DB constraint, to keep the schema forward-compatible
per the note at the top of this document): exactly 2 rows per `bet_id` in v1.

### `positions`
A user's current holding of shares in one outcome of one bet.

| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| user_id | uuid, fk → users.id | |
| bet_id | uuid, fk → bets.id | |
| outcome_id | uuid, fk → outcomes.id | |
| shares | numeric | accumulated `shares_out` from §3.2 across all this user's buys on this outcome |
| points_spent | numeric | sum of `amount` this user has put into this outcome — kept alongside `shares` so "how much did I put in vs. what do I hold" is answerable without replaying ledger history |
| created_at | timestamptz | |
| updated_at | timestamptz | |

Unique constraint on `(user_id, bet_id, outcome_id)` — a user's YES position on a given
bet is one row that accumulates, not one row per trade. (Individual trades are still
fully recorded in `ledger_entries` for audit purposes — see below. `positions` is a
denormalized "current holdings" view for fast reads; `ledger_entries` is the source of
truth for history.)

### `ledger_entries`
**This is the most important table in the schema.** Append-only. Every points movement
for every user is a row here, and a user's balance is `SUM(amount) WHERE user_id = ?`.

| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| user_id | uuid, fk → users.id | |
| amount | numeric | positive (credit) or negative (debit) |
| entry_type | enum: `refill`, `bet_placed`, `payout`, `resolution_reversal` | see below |
| bet_id | uuid, fk → bets.id, nullable | null for `refill` entries |
| related_ledger_entry_id | uuid, fk → ledger_entries.id, nullable | for `resolution_reversal` rows, points back at the `payout` entry being reversed — this is what makes §3.5's "exact reversal" auditable and mechanical rather than a special code path that recomputes from scratch |
| created_at | timestamptz | |

Entry types, mapped directly to actions in `01_overview_and_mechanism.md`:
- `refill`: the weekly/monthly points top-up (positive amount, added on top of current
  balance per the user's explicit choice — see design decision log in this document's
  final section).
- `bet_placed`: negative amount, the `amount` a user spent buying shares (§3.2).
- `payout`: positive amount, `1 * shares_held` for a winning position at resolution
  (§3.4).
- `resolution_reversal`: used when an authorized resolver corrects a resolution (§3.5).
  Two things happen on a correction: (1) a `resolution_reversal` entry with the
  *negative* of the
  original `payout` amount, referencing it via `related_ledger_entry_id`, and (2) a new
  `payout` entry for the corrected outcome. A user's balance after correction is
  therefore exactly `original_balance - old_payout + new_payout`, which is provably
  correct rather than "recompute and hope."

A `user_balances` value is never stored as a mutable column — it's always
`SELECT SUM(amount) FROM ledger_entries WHERE user_id = :id`. For performance once the
table grows, add a materialized view or a cached `balance_cache` column that's
recomputed on write within the same transaction as any new ledger entry — but the
`ledger_entries` table stays the source of truth either way. Don't let a cache column
become the source of truth; that's exactly the kind of subtle bug class this document's
whole design is trying to avoid (see the AMM formula correction in
`01_overview_and_mechanism.md` §3 for why "verify, don't assume" matters here as much as
in the math).

### `resolution_events`
The audit trail referenced in §3.5.

| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| bet_id | uuid, fk → bets.id | |
| outcome_id | uuid, fk → outcomes.id | which outcome was marked as winner in this event |
| resolved_by | uuid, fk → users.id | |
| is_correction | boolean | false for the first resolution, true for any later correction |
| created_at | timestamptz | |

This table exists *in addition to* the `resolved_outcome_id` and `resolved_by` columns on
`bets` (which reflect the current result) and its immutable first `resolved_at`
leaderboard anchor. `resolution_events` is the full history — every resolution and every
correction, in order — so "show me the dispute history for this bet" is a simple query,
matching the requirement in §3.5 that corrections be "visible in the bet's history to
all participants."

### `bet_visibility_overrides`
Handles the "hidden/shown to certain people in the group" requirement from the user's
original spec.

| column | type | notes |
|---|---|---|
| id | uuid, pk | |
| bet_id | uuid | part of the composite bet/group foreign key below |
| group_id | uuid | non-null; denormalized intentionally so the composite foreign keys below enforce group-only use |
| user_id | uuid | part of the composite membership foreign key below |

**Semantics, spelled out because this is easy to get backwards:** if a bet has zero rows
in this table, it's visible to the entire group (default, matches "a bet can be
hidden/shown to certain people" reading as opt-in restriction rather than opt-in
visibility). If a bet has one or more rows, it is visible **only** to the users listed
here (plus the creator and group admins, always). This is an allow-list, not a
block-list — pick one interpretation and enforce it consistently in the backend
authorization check (see `03_backend_architecture.md`), and write a unit test asserting
a non-listed member genuinely cannot see the bet via the API, not just that the UI hides
it.

Add a unique constraint on `bets(id, group_id)`, then enforce composite foreign keys
`bet_visibility_overrides(bet_id, group_id) → bets(id, group_id)` and
`bet_visibility_overrides(group_id, user_id) → group_members(group_id, user_id)`.
Also make `(bet_id, user_id)` unique so an allowed user cannot be listed twice for the
same bet.
Because `bet_visibility_overrides.group_id` is non-null while a public bet's
`bets.group_id` is always null, a public bet cannot receive an override row at the
database level. The membership foreign key also prevents an allow-list from naming
someone outside the bet's group. The service should still reject either mistake with a
useful domain error before the constraint fires.

---

## Derived / read-model concerns (not new tables, just noted here so the agent doesn't invent extra tables for these)

- **Leaderboards** (weekly/bi-weekly/monthly/all-time) are computed read models, not
  stored tables. The ranking value is **realized net betting profit/loss**, never the
  user's current balance:

  ```text
  net_profit_loss =
      SUM(bet_placed + payout + resolution_reversal ledger-entry amounts)
  ```

  Because `bet_placed` amounts are negative and payouts are positive, someone who
  spends 30 points and receives 50 has `+20`; someone who spends 30 and receives
  nothing has `-30`. Refills are excluded. Open and closed-but-unresolved bets are
  excluded so a stake is not shown as a loss before its outcome is known. Corrections
  are naturally reflected because the old payout, its negative reversal, and the new
  payout sum to the corrected result.

  Scope is mandatory in the query:

  - A **group leaderboard** joins `ledger_entries → bets`, requires
    `bets.status = 'resolved'`, `bets.visibility = 'group'`, and
    `bets.group_id = :group_id`. It includes no entries from other groups and no public
    bets, even when the same user participated in them.
  - The **global leaderboard** requires `bets.status = 'resolved'`,
    `bets.visibility = 'public'`, and `bets.group_id IS NULL`. It ranks only the
    standalone public-betting scope; it is not an aggregation of private group
    performance.

  For weekly/bi-weekly/monthly windows, filter on the bet's immutable first
  `resolved_at`, not individual ledger-entry timestamps. This keeps a bet's stake and
  payout together in one period even if the stake was placed earlier, and a later
  correction updates that original period instead of creating a misleading new win or
  loss. All-time has no date predicate. Add test cases proving that refills, unresolved
  bets, another group's bets, and public bets cannot leak into a group result. This
  remains acceptable as an on-demand query at friend-group scale; add caching only if
  measured performance requires it.

- **Current bet price/probability** (§3.3) is likewise not stored — it's computed
  on-demand from the two `outcomes.pool_shares` values whenever a bet is fetched. It
  only becomes stale-relevant if we later add price history charts (a v2 feature, note
  in `06_open_questions_and_config.md`), which would need a separate
  `price_snapshots` table logging price after every trade. Not needed for v1.

---

## Design decision log (so future readers know these weren't accidents)

- **Refill adds on top of current balance, doesn't top up to a fixed amount** — this was
  an explicit choice (not a default) so that skilled/lucky bettors snowball ahead over
  time and the all-time leaderboard means something across a season, rather than
  resetting every period. Refills affect spendable wallet balance but never leaderboard
  profit/loss. This is why leaderboards need explicit scope and time-window filters
  rather than balance alone telling the whole story.
- **Balances can go negative? No — enforce at the application layer that a `bet_placed`
  ledger entry can never bring a user's balance below zero.** This must be checked
  inside the same DB transaction that inserts the ledger entry (read current balance,
  check, insert, commit — all one transaction) to avoid a race condition where two
  simultaneous bets both pass the check before either commits. This is exactly the kind
  of bug Postgres transactions exist to prevent, and exactly the kind of bug that
  wouldn't be caught by looking at either request in isolation — it needs a concurrency
  test, not just a unit test (see `05_build_phases.md`).

---

## SQLAlchemy ORM and Alembic migration contract

Implement every table above as a SQLAlchemy 2.x declarative model using the async
session at runtime. The `Bet.group_id` attribute is nullable at the Python type level
because public bets have no group, while the named `CheckConstraint` above enforces the
valid combinations. Define separate repository methods for group bets and public bets;
do not expose an unscoped list method that callers can accidentally use for a
leaderboard. Relationships must not invent a `Group.public_bets` association.

The initial Alembic history must:

1. Create PostgreSQL enum types, then `users`, `groups`, and `group_members`.
2. Create `bets` with `ck_bets_scope_matches_group`. Because
   `bets.resolved_outcome_id → outcomes.id` and `outcomes.bet_id → bets.id` form a
   dependency cycle, create the `outcomes` table before adding the named
   `resolved_outcome_id` foreign key (or use SQLAlchemy's `use_alter=True`) so both
   upgrade and downgrade ordering are deterministic.
3. Create `positions`, `ledger_entries`, `resolution_events`, and
   `bet_visibility_overrides`, including every unique constraint and foreign key named
   in this document.
4. Add query indexes for `(group_id, status, resolved_at)` on group bets,
   `(visibility, status, resolved_at)` for the public leaderboard, and
   `(bet_id, user_id, entry_type)` on `ledger_entries`.
5. Include working `downgrade()` operations in reverse dependency order. Application
   startup and tests must run `alembic upgrade head`; `Base.metadata.create_all()` is
   not an accepted substitute.

If this constraint is added to an already-populated draft database, first audit existing
rows. Remove public-bet visibility overrides, backfill the remaining overrides'
`group_id` from their group bet, and then make that column non-null and add its composite
foreign keys. Detach public bets by setting `bets.group_id = NULL`, reject any group bet
whose `group_id` is null, and only then validate `ck_bets_scope_matches_group`. Since
detaching loses the former group attribution, export that mapping before the migration
if rollback of production data is required.
