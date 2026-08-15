# BullyMarket Data Model

All financial values use PostgreSQL `NUMERIC(24, 8)` and Python `Decimal`. UUID primary
keys and timezone-aware timestamps are used throughout. User and house financial logs
are append-only.

## 1. Identity and groups

### `users`

Stores email, display name, password hash, creation time, and last refill time. Wallet
balance is derived from `SUM(ledger_entries.amount)`; it is not a mutable user column.

### `groups` and `group_members`

`groups` stores name, description, creator, and invite code. `group_members` has a unique
`(group_id, user_id)`, scoped role (`member`/`admin`), and retained status
(`active`/`removed`). Removal never destroys settlement history.

## 2. Markets

The existing table is named `bets`; API routes use both “bets” and “markets” according
to the action.

### `bets`

Core columns include scope/status, creator, question, end time, current resolution, and:

| column | meaning |
|---|---|
| `pricing_method` | `cpmm` for migrated historical rows; `lmsr` for new rows |
| `liquidity_seed` | historical CPMM seed retained for backward compatibility |
| `b_liquidity` | LMSR depth, positive and immutable after creation |
| `q_yes`, `q_no` | current net shares issued by the LMSR house, initialized to zero |
| `house_reserve` | funded maximum exposure, `b * ln(2)` |
| `house_cash_balance` | running signed house cash from trades, refunds, and payouts |
| `house_profit_loss` | final realized P/L; null until settlement, zero when cancelled |

Scope is enforced by named check constraint `ck_bets_scope_matches_group`:

```sql
(visibility = 'group' AND group_id IS NOT NULL)
OR (visibility = 'public' AND group_id IS NULL)
```

Scope and pricing method are immutable. Public bets never receive a group attribution.

### `outcomes`

Exactly two rows are required by v1. Display order 0 is the LMSR YES side and order 1 is
NO, regardless of custom labels. `pool_shares` retains the historical CPMM value; for
LMSR rows it mirrors the corresponding `q` value for backward-compatible response
rendering.

### `positions`

Unique key `(user_id, bet_id, outcome_id)`. `shares` is the current net holding and has
a database nonnegative constraint. `points_spent` is net cash committed to that holding:
buys increase it, sell proceeds decrease it, and a fully closed position resets it to
zero. Positions are the fast current-state view; immutable trades are the audit source.

## 3. User ledger

`ledger_entries` remains the source of wallet balances:

- `refill`: positive platform top-up;
- database value `bet_placed`: signed LMSR trade movement as well as historical CPMM
  buys (negative buy cost, positive sell proceeds);
- `payout`: positive winning-share redemption;
- `resolution_reversal`: retained only for backward-compatible historical rows;
- `bet_refund`: cancellation credit.

Leaderboards include only trade/payout/reversal rows belonging to resolved bets in the
requested scope. A group leaderboard filters the exact `group_id`; the global user
leaderboard filters standalone public bets. Refills, open markets, balances, other
groups, and public bets never leak into a group result.

## 4. Immutable LMSR trades

### `trades`

| column | meaning |
|---|---|
| `bet_id`, `user_id`, `outcome_id` | market, actor, and concrete outcome |
| `sequence` | unique monotonic order within a market |
| `side` | `yes` or `no` |
| `delta_shares` | positive buy or negative sell; nonzero |
| `cost` | signed user-to-house LMSR cost |
| `house_cash_flow` | same signed value from the house perspective |
| `q_yes_after`, `q_no_after` | complete post-trade state for reconstruction |
| `created_at` | audit timestamp; sequence is authoritative for ordering |

Checks keep post-trade quantities nonnegative. Unique `(bet_id, sequence)` prevents
ambiguous reconstruction.

## 5. House ledger and summaries

### `house_ledger_entries`

Each row contains `bet_id`, denormalized nullable `group_id`, optional `trade_id`, unique
per-market `sequence`, and three independent signed dimensions:

- `cash_delta`: money received by the house is positive; paid by the house is negative;
- `reserve_delta`: positive when exposure is reserved, negative when released;
- `realized_pnl_delta`: final settlement changes to realized P/L.

Entry types are `reserve`, `trade`, `payout`, `resolution_reversal`, `refund`,
`reserve_release`, and `pnl_adjustment`; `resolution_reversal` remains a historical enum
value but new resolutions are immutable. A check requires at least one nonzero dimension.

House read models are derived from LMSR bets, trades, and the ledger:

- market: one bet only;
- group: only bets whose `group_id` equals the requested group;
- global: all LMSR bets, showing total concurrent reserved exposure.

Each summary reports market/trade counts, open reserved exposure, total trade cash flow,
current house cash balance, and realized P/L. Running cash on an unresolved bet is not
reported as realized profit.

## 6. Other audit tables

- `resolution_events`: the single final resolution, with actor and outcome. The legacy
  `is_correction` column remains false for new events.
- `bet_edit_events`: immutable end-time changes.
- `bet_visibility_overrides`: optional group-member allow-list, protected by composite
  bet/group and group/member foreign keys; public bets cannot receive rows.

## 7. Migration contract

Alembic revision `0002`:

1. backfills all existing bets with `pricing_method = 'cpmm'`;
2. adds nullable LMSR state and nonnull zeroed house accounting fields;
3. adds the position nonnegative constraint for PostgreSQL upgrades;
4. creates `trades` and `house_ledger_entries` with reversible enums, constraints,
   indexes, and foreign keys.

No historical market is converted or repriced. New creation code explicitly writes
`pricing_method = 'lmsr'`, initializes `q_yes = q_no = 0`, and appends the reserve event
within the same transaction.
