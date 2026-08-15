# 06. Open Questions, Config Values, and V2 Candidates

## Config values the coding agent should treat as settings, not hardcoded constants

These are all referenced elsewhere in this plan as specific numbers for worked examples,
but should be environment/config-driven, not literals buried in code:

- `DEFAULT_LMSR_LIQUIDITY` (`b` in `01_overview_and_mechanism.md` §3) — defaults to 100
  and may be overridden at market creation. It must be positive and becomes immutable
  as soon as the market exists. Reserved exposure is derived as `b * ln(2)`.
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
- LMSR pricing for every new market, with historical CPMM markets tagged and preserved.
- Fractional buy and sell trades at the API layer; selling is capped at the user's
  current shares. The current frontend temporarily presents purchases only.
- Immutable trade and house ledgers, plus market/group/global house summaries.
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
- Price history charts — would need a `price_snapshots` table, noted in
  `02_data_model.md`'s derived-concerns section.
- Real-time (WebSocket/SSE) odds updates — noted in `04_frontend_architecture.md` §4.
- Fees or spreads on LMSR trades (current immediate round trip is neutral within
  eight-decimal rounding).

## Resolved product decisions

1. **Bet deletion is a cancellation with refunds.** For LMSR, return each participant's
   net cash paid across buys and sells, reverse the house trade cash, release reserved
   exposure, and retain every audit row. Historical CPMM cancellation keeps its original
   stake-refund behavior.
2. **Removed group members keep only existing-bet access.** A removed member cannot see
   or enter future group bets. They remain able to see bets in which they already hold
   a position until those bets resolve or are cancelled, and the UI must clearly show
   that they were removed and are only waiting for those bets to finish. The shared
   invite code cannot reactivate a removed membership and is not returned to that user.
3. **A bet's `end_time` is editable.** Record every change in `bet_edit_events`; resolved
   and cancelled bets remain immutable.
4. **LMSR trades are share-denominated and may be fractional.** A delta must be nonzero;
   buys require sufficient balance and sells cannot exceed holdings. The old
   `MINIMUM_TRADE_AMOUNT` applies only to historical point-denominated CPMM purchases.
5. **Public means signed-in platform users.** Public bets remain completely outside
   groups. Any account may view, create, and resolve a standalone public bet.
