# 06. Open Questions, Config Values, and V2 Candidates

## Config values the coding agent should treat as settings, not hardcoded constants

These are all referenced elsewhere in this plan as specific numbers for worked examples,
but should be environment/config-driven, not literals buried in code:

- `DEFAULT_LIQUIDITY_SEED` (`L` in `01_overview_and_mechanism.md` §3.1) — used `100` in
  worked examples. Reasonable default, but should be a named constant in one place
  (probably `bets` module config), and ideally overridable per-bet at creation time later
  if that's ever wanted (not required for v1, but don't make it structurally impossible).
- `DEFAULT_STARTING_BALANCE` — the balance a brand new user gets on signup. Not
  specified numerically anywhere above; pick something reasonable (e.g. `1000`) and put
  it in one config location.
- `REFILL_AMOUNT` and `REFILL_INTERVAL` — how many points, how often (weekly vs.
  monthly — the user said "weekly bi weekly and monthly" for leaderboard *views*, but
  was less explicit about the refill *cadence* itself; this should be a single
  group-level or platform-level config, not hardcoded, so it can be tuned after the app
  is actually being used and it's clear whether weekly or monthly refills feel better
  for keeping the game interesting without letting balances snowball too fast or too
  slow).

## Explicit v1/v2 boundary (collected from decisions made throughout this plan)

**In v1:**
- Binary (2-outcome) bets only.
- CPMM/AMM pricing (`01_overview_and_mechanism.md` §3).
- No selling before resolution — positions locked until resolve.
- Group-admin resolution plus correction/reversal support; the standalone public-bet
  resolver policy is the explicit open question below.
- Mutually exclusive group bets and standalone public bets, plus per-user allow-lists
  for group bets only.
- Weekly/bi-weekly/monthly/all-time realized-profit/loss leaderboards: each group uses
  only that group's resolved bets, while global uses only standalone public bets.
- Polling-based odds updates (not real-time push).

**Deferred to v2 (schema left not-actively-hostile to these, per notes throughout, but
not built now):**
- N-outcome (>2) markets — noted in `01_overview_and_mechanism.md` §3.7 and
  `02_data_model.md`'s `outcomes`-as-a-table design.
- Selling positions before resolution — noted in §3.6; the math is a small addition to
  the existing CPMM functions (a sell is structurally the reverse of a buy) but adds UI
  complexity (showing live position value) that's explicitly out of scope for a simple
  v1.
- Price history charts — would need a `price_snapshots` table, noted in
  `02_data_model.md`'s derived-concerns section.
- Real-time (WebSocket/SSE) odds updates — noted in `04_frontend_architecture.md` §4.
- Per-bet custom liquidity seed at creation time (v1 uses one platform-wide default).

## Resolved product decisions

1. **Bet deletion is a cancellation with refunds.** Return every participant's original
   stake through append-only `bet_refund` ledger entries and retain the cancelled bet
   for auditability.
2. **Removed group members keep only existing-bet access.** A removed member cannot see
   or enter future group bets. They remain able to see bets in which they already hold
   a position until those bets resolve or are cancelled, and the UI must clearly show
   that they were removed and are only waiting for those bets to finish.
3. **A bet's `end_time` is editable.** Record every change in `bet_edit_events`; resolved
   and cancelled bets remain immutable.
4. **The minimum trade is 1 point.** Keep it in the `MINIMUM_TRADE_AMOUNT` setting rather
   than hardcoding it in the trading service.
5. **Public means signed-in platform users.** Public bets remain completely outside
   groups. Any account may view, create, and resolve a standalone public bet.
