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

## Real open questions for the user (not decided in this plan — flag these before/during
build rather than silently picking an answer)

1. **What happens to a user's open positions if they leave a group, or a bet is deleted
   If a bet is deleted, the original amount must be returned to all participants. if a person gets kicked out of a group, he keeps particiating in bets he previously participated in until the bet ends, but he can not see or participate in future bets, and he gets clearly informed that he is kicked and waiting to finish the bets
2. **Can a bet's `end_time` be edited after creation?** Not addressed above. If yes, this
   Yes, a bet time can be edited.
3. **Minimum/maximum bet amount per trade?** Not addressed above — currently unbounded
   1 point
4. **What exactly counts as "public"?** Public bets are confirmed to be standalone and
   outside all groups. What remains to confirm is whether "public" means any signed-in
   account on the platform
5. **Who can create and resolve standalone public bets?** Group-admin authorization
   anyone with an account

These should be resolved (either by the user or by the coding agent making an explicit,
documented default choice and flagging it in a `DECISIONS.md` or similar in the actual
repo) rather than silently guessed at during implementation — the same "verify, don't
assume" principle that governed the AMM math in `01_overview_and_mechanism.md` applies
to product decisions too, just with different stakes.
