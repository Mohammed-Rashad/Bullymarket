# BullyMarket Overview and LMSR Mechanism

## 1. Product scope

BullyMarket is a play-money prediction market for small friend groups, plus a separate
platform-wide public-betting scope. No real money is used.

- Every v1 market is binary. The first outcome is the YES side and the second is NO;
  labels may be customized.
- A market belongs to exactly one group or is standalone public. It can never be both.
- Group leaderboards use realized user profit/loss only from resolved bets in that exact
  group. The global leaderboard uses resolved standalone public bets only.
- Refills and overall wallet balances never determine leaderboard rank.
- The platform is the counterparty to every new trade. There is no order book and no
  wait for another user to match an order.

## 2. Why LMSR

A central-limit order book needs many simultaneous buyers, sellers, and market makers.
Most friend-group questions receive only a handful of trades, so an order book would
usually be empty. A Logarithmic Market Scoring Rule (LMSR) gives every market a
continuous price and makes it always tradeable even with one participant.

Historical markets created before migration retain `pricing_method = 'cpmm'` and remain
readable and settleable with the old rules. Every newly created market is tagged
`pricing_method = 'lmsr'`. Pricing method is immutable.

## 3. Binary LMSR math

Each market stores three fixed/current values:

- `b_liquidity`: fixed liquidity/depth selected at creation; it must be positive.
- `q_yes`: net YES shares issued by the house, starting at zero.
- `q_no`: net NO shares issued by the house, starting at zero.

### 3.1 Cost function

The LMSR cost function is:

```text
C(q_yes, q_no) = b * ln(exp(q_yes / b) + exp(q_no / b))
```

The implementation uses the log-sum-exp transformation and never exponentiates raw,
unbounded `q / b` values:

```text
m = max(q_yes, q_no)
C = m + b * ln(exp((q_yes - m) / b) + exp((q_no - m) / b))
```

Transcendental work uses bounded floats; persisted quantities, user balances, costs,
and payouts are `Decimal` values quantized to eight decimal places.

### 3.2 Current marginal price

```text
P_yes = exp(q_yes / b) / (exp(q_yes / b) + exp(q_no / b))
P_no  = 1 - P_yes
```

At `q_yes = q_no = 0`, both prices are 0.5. Buying a side increases its price. A larger
`b` makes the market deeper and moves prices more slowly; a smaller `b` makes the market
more responsive. `b = 50–200` is a practical fake-money range, with a default of 100.

### 3.3 Buy and sell quotes

A trade specifies a side and a signed share delta:

- positive `delta_shares`: buy shares;
- negative `delta_shares`: sell shares already held.

```text
trade_cost = C(q_yes_after, q_no_after) - C(q_yes_before, q_no_before)
```

A positive cost is paid by the user to the house. A negative cost is paid by the house
to the user. The exact same function handles buys and sells. A buy followed immediately
by an equal sell returns to the original state and has zero net cost apart from the
platform's eight-decimal rounding.

Users may hold fractional shares but may not short: a sell is rejected if its magnitude
exceeds the user's position on that side. Global `q_yes` and `q_no` therefore also remain
nonnegative.

### 3.4 Settlement and bounded house loss

A winning share redeems for exactly 1 point and a losing share for zero. For a binary
market, the LMSR house's maximum possible loss is known at creation:

```text
max_house_loss = b * ln(2)
```

That amount is recorded as reserved exposure before trading opens. On resolution:

```text
total_collected = SUM(signed trade costs)
total_paid_out  = shares held on the winning side
house_profit_loss = total_collected - total_paid_out
```

The equivalent theoretical collection is
`C(q_yes_final, q_no_final) - C(0, 0)`. Resolution asserts that final house P/L is not
less than `-b * ln(2)` beyond the supported rounding tolerance.

## 4. House accounting

House accounting is separate from the user ledger and is append-only.

- Every trade stores its signed `house_cash_flow`, equal to the signed LMSR cost.
- Every market stores its reserved exposure, running net cash from trades/payouts, and
  final realized house P/L once resolved.
- `house_ledger_entries` records reserve, trade, payout, payout reversal, refund,
  reserve release, and realized-P/L adjustment events.
- Each trade and house event has a per-market monotonic sequence so the complete state
  can be reconstructed even if timestamps tie.
- A group summary filters by that exact `group_id`. A global house summary includes all
  LMSR markets and exposes concurrent reserved exposure. Public/group user leaderboard
  separation remains unchanged.

Reserved exposure is capital at risk, not a realized loss. Running trade cash is not
called profit while a market remains unresolved. Realized P/L is assigned only after a
winner is paid.

## 5. Atomicity and lifecycle

- Quote endpoints never write. Execution recomputes the quote inside the transaction.
- PostgreSQL locks the market row with `SELECT FOR UPDATE` before reading `q_yes/q_no`.
  SQLite development mode uses a process-local market lock held through commit because
  SQLite ignores row locks.
- The same transaction updates market quantities, the user's position, the user ledger,
  the immutable trade row, and the house ledger.
- Cancellation returns each user's net LMSR cash paid (buys minus sell proceeds),
  reverses the house cash, and releases reserved exposure.
- Resolution correction reverses the prior user payouts and matching house payout,
  pays the corrected side, and records only the change in realized house P/L.
- Removed group members retain access only to markets where they already have a
  position until those markets settle or are cancelled.

## 6. API contract

- `GET /api/v1/markets/{id}/price` — current LMSR prices and quantities; read-only and
  unauthenticated.
- `GET /api/v1/markets/{id}/quote?side=yes&shares=N` — signed hypothetical quote with
  average fill price and post-trade prices; no write.
- `POST /api/v1/markets/{id}/trade` — authenticated atomic buy/sell.
- `GET /api/v1/markets/{id}/trades` — ordered immutable audit history.
- `POST /api/v1/bets/{id}/resolve` — authorized settlement/correction.
- `GET /api/v1/bets/{id}/house` and `/house-ledger` — market accounting.
- `GET /api/v1/groups/{id}/house` — exact-group house summary for a group admin.
- `GET /api/v1/house` — authenticated global house summary.

The frontend never implements LMSR math. It debounces quote requests and polls the
price endpoint every few seconds.

## 7. Required invariants and tests

1. `price_yes + price_no == 1` for every valid state.
2. `C(0, 0, b) == b * ln(2)`.
3. Buying and immediately selling the same shares is reversible.
4. Random valid trade sequences cannot create a resolution loss below `-b * ln(2)`.
5. Extreme quantity ratios cannot overflow.
6. A sell cannot exceed the user's held shares.
7. Simultaneous trades have monotonic sequences and no lost `q` update.
8. User and house cash movements are equal and opposite.
9. Resolution correction is financially identical to resolving directly to the final
   outcome.
10. Group/public leaderboard and house-summary scopes cannot leak into each other.

## Appendix: future N-outcome LMSR

N outcomes are out of scope, but LMSR generalizes without changing the accounting
model:

```text
C(q_1...q_n) = b * ln(sum(exp(q_i / b) for i in 1...n))
P_i = exp(q_i / b) / sum(exp(q_j / b) for j in 1...n)
```

The current `outcomes` table remains normalized so this can be added later. v1 service
validation still requires exactly two outcomes.
