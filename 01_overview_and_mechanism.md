# Friend-Group Prediction Market Called BullyMarket — Project Plan

## 0. Purpose of this document

This is a build plan for a coding agent. It is written so the agent can implement the
system without re-deriving design decisions. Where a decision was made for a specific
reason, the reason is included, because "just do it like Polymarket" is not sufficient —
this system deliberately does **not** copy Polymarket's current mechanism, and the agent
needs to know why.

Read this whole document before writing code. Then read `02_data_model.md`,
`03_backend_architecture.md`, `04_frontend_architecture.md`, and `05_build_phases.md`
in order.

---

## 1. What we are building, in plain language

A web app where a closed friend group bets play-money points on real-life questions
("who leaves work later tomorrow", "will it rain Saturday", "does Ahmed actually go to
the gym this week"). No real money anywhere, ever. Structure:

- Users have accounts and a points balance.
- Users create or join **groups**.
- Inside a group, any member can create a **group bet** (a market with 2+ possible
  outcomes, usually YES/NO) with an end time.
- **Public bets are a separate, platform-wide betting scope.** They are created and
  listed outside groups and never belong to, originate from, or retain an attribution
  to a group. A group bet cannot also be public.
- Members buy shares in the outcome they think will happen. The price moves as people
  bet — this is the "Polymarket feel."
- After the end time, a group **admin** resolves a group bet (picks the winning
  outcome). Standalone public bets use the separate platform-level resolver policy
  called out in `06_open_questions_and_config.md`. Winners are paid out from the pool
  automatically.
- An authorized resolver can **correct** a resolution later if there's a dispute, and
  the payout automatically reverses and recomputes.
- Group bets can be **hidden** from specific group members (visible to a subset) at
  creation time. This setting does not apply to standalone public bets.
- Leaderboards exist for weekly / bi-weekly / monthly / all-time windows, but their
  scopes must never be mixed. A group leaderboard ranks net points won or lost only
  from resolved bets inside that group. The global leaderboard ranks net points won or
  lost only from standalone public bets. Neither leaderboard is based on a user's
  overall wallet balance, and activity in one group must never affect another group's
  standings.

---

## 2. Why the payout mechanism is an AMM, and specifically NOT Polymarket's current one

This section exists because "make it like Polymarket" is ambiguous — Polymarket has used
two different mechanisms historically, and copying the wrong one will make this app feel
broken. Read this before touching the betting math.

### 2.1 What Polymarket actually does today

Polymarket **used to** run on an AMM (an automated formula, specifically LMSR — a
Logarithmic Market Scoring Rule) but **migrated away from it**. Today, <cite index="2-1">Polymarket
chose to upgrade from an AMM to an order book model,</cite> because <cite index="2-1">the platform's
user base has exploded, resulting in ample liquidity and a relatively stable order book
experience,</cite> and the order-book model <cite index="2-1">is more suitable for professional
market makers.</cite>

Concretely, Polymarket now runs a Central Limit Order Book (CLOB): <cite index="16-1">it works by
collecting every open limit order — both buy orders (bids) and sell orders (asks) —
sorting them by price, and matching them whenever a buyer's price meets a seller's
price.</cite> <cite index="15-1">Prices aren't set by Polymarket — they emerge from supply and demand as users
trade with each other.</cite> The price shown to users is <cite index="15-1">the midpoint of the bid-ask
spread</cite> — for example, <cite index="15-1">if the best bid for "Yes" is $0.34 and the best ask is
$0.40: Displayed price = ($0.34 + $0.40) / 2 = $0.37 (37% probability).</cite> Critically,
this requires enough independent traders on both sides that a book actually has depth.

### 2.2 Why that's the wrong model for this app

A CLOB only works when there's enough independent order flow to fill it. With 5-30
friends betting on "who leaves work later tomorrow," there will often be 2-3 total bets
on a market. A real order book with 2-3 orders is mostly empty — bets would sit unfilled,
odds wouldn't move sensibly, and the "watch the odds shift as people pile on" feeling
(the whole appeal of this style of app) would not happen. This exact tradeoff is
documented in the wild: <cite index="3-1">Polymarket runs a CLOB because its flagship markets attract
professional market makers and concentrated flow. Manifold runs a CPMM-AMM because its
users spin up thousands of thin, long-tail questions that no professional MM will ever
quote.</cite> Our situation — many small, thin, friend-created questions with no
professional liquidity — is the Manifold case, not the Polymarket case.

### 2.3 What we're building instead: a CPMM (constant-product AMM)

We use a **Constant Product Market Maker (CPMM)**, the same family of formula Polymarket
itself used to run (as LMSR) and that Manifold currently runs. <cite index="1-1">This is the most
common AMM model... It uses the formula x * y = k, where x and y represent the
quantities of two assets in a liquidity pool, and k is a constant.</cite> Applied to a
prediction market with two outcome pools, the mechanism guarantees **someone is always
willing to trade with you, at a price that moves against you as you buy more** — no
empty order book, ever, regardless of how few people are in the market. This is
Section 3 below, fully specified.

We are deliberately building the *original* AMM-style Polymarket mechanism, not the
*current* order-book Polymarket mechanism. The "Polymarket feel" the user wants (buy
early on a longshot, price moves as people bet, resolve YES/NO, winners split $1/share)
is fully present in the AMM version and does not require the order-book/liquidity-depth
machinery that only makes sense at Polymarket's actual trading volume.

### 2.4 The invariant we keep from Polymarket regardless of mechanism

One thing is true in both models and we keep it: <cite index="12-1">1 YES + 1 NO = $1</cite> (in our
case, 1 point). Every outcome share is worth exactly 1 point if it wins and 0 if it
loses. <cite index="18-1">Winning shares pay $1.00 — if your prediction is correct, each share is
worth exactly $1.00.</cite> This is what makes "price = probability" a coherent idea
and what makes payout math well-defined. Section 3 shows exactly how this plays out with
a CPMM instead of an order book.

---

## 3. The betting math, fully specified

This is the part that must be implemented exactly as written and covered by unit tests,
because it is the one part of the system where a bug means the money math is wrong for
everyone. Everything else in the app (groups, permissions, leaderboards) is normal CRUD;
this section is not.

### 3.1 Model: two-outcome market as a liquidity pool

Every bet (market) has two pools of virtual shares: `pool_yes` and `pool_no` (for
non-binary bets with more than 2 outcomes, see 3.7). At market creation, the creator (or
the system, per config) seeds both pools with an equal starting liquidity amount `L`
(e.g. `L = 100`), so:

```
pool_yes = L
pool_no  = L
k = pool_yes * pool_no        # k is fixed for the life of the market
```

Starting price of each side is always 0.5 / 0.5 when pools are equal, because price is
derived from the *ratio* of the pools (3.3), matching real-world CPMM behavior: <cite index="6-1">the
number of shares a market's liquidity pool always forces a balance in the number of
shares of each outcome in the market — when an imbalance is introduced... outcome prices
change and shares are redistributed.</cite>

Seeding both sides equally was a deliberate choice (see `06_open_questions_and_config.md`
for the alternative we rejected): it keeps early odds near 50/50 instead of letting the
first bettor set an extreme price, while still allowing the pools to move to extreme
odds later once real bets come in — nothing in the formula prevents NO from becoming 1¢
if enough people pile onto YES, this only affects the *starting* point.

### 3.2 Buying shares (placing a bet)

The key mental model: `pool_yes` and `pool_no` represent the AMM's own *inventory* of
each share type, available to sell to buyers. When you buy YES, you're paying `amount`
points into the pool, and the AMM sells you YES shares out of its YES inventory — so
`pool_yes` (inventory remaining) goes **down** and `pool_no` (points-in, expressed on
the other side of the invariant) goes **up**. This inventory-depletion framing is the
one to keep in your head; getting the direction backwards is the single easiest mistake
to make in this whole system, and it happened once already while drafting this document
(see the numeric derivation this section is based on, which the unit tests in 3.8
enforce independently of this prose).

To buy shares of YES with `amount` points:

```
new_pool_yes = (pool_yes * pool_no) / (pool_no + amount)
shares_out   = pool_yes - new_pool_yes

# then commit:
pool_no  = pool_no + amount
pool_yes = new_pool_yes
```

To buy shares of NO with `amount` points, swap every `yes`/`no` in the block above.

This is the standard constant-product swap: <cite index="7-1">the CPMM guarantees that the
product between the amounts of the two reserved pool currencies stays constant. This
property ensures that the price for swapping between these pairs mimics the behavior of
a demand curve of a normal good.</cite> In our case that means: the more you buy of one
side, the worse the price gets for the next unit you buy (slippage), because you are
depleting that side's inventory and pushing the pool ratio further from balance.

The user's `amount` points are deducted from their balance immediately and are locked
into that position until the market resolves (or, if we implement selling — see 3.6 —
until they sell).

**Worked example** (`L = 100`, so `pool_yes = pool_no = 100`, `k = 10000`):

User A buys YES with 20 points:
```
new_pool_yes = 10000 / (100 + 20) = 83.333...
shares_out   = 100 - 83.333... = 16.666...
pool_no  = 120
pool_yes = 83.333...
```
User A paid 20 points and received ~16.67 YES shares. Note `shares_out < amount` — this
is expected and correct: the "price per share" A paid was above 1 point because YES got
more expensive as A bought it (this is slippage, and it's the mechanism's built-in
"can't move the market for free" property). If YES wins, A gets 16.67 points back — a
loss versus their 20-point stake, because A moved a fairly thin pool a lot. In a
deeper/more-traded pool, `shares_out` would sit much closer to `amount`.

### 3.3 Displayed price (implied probability)

After any trade, the displayed price of YES is:

```
price_yes = pool_no / (pool_yes + pool_no)
price_no  = pool_yes / (pool_yes + pool_no)
```

`price_yes` uses `pool_no` in the numerator: the side whose *inventory got depleted*
(fewer shares left in the pool) is the side that's now more expensive/likely, because
that's the side buyers have been buying. This mirrors the real relationship Polymarket
describes: <cite index="13-1">the price of each outcome represents the market's implied
probability... if a Yes share trades at $0.72, the market collectively assigns a 72%
probability to that outcome occurring.</cite>

Continuing the worked example: after A buys YES, `pool_yes = 83.33`, `pool_no = 120`, so
`price_yes = 120 / (83.33 + 120) = 0.590` and `price_no = 83.33 / 203.33 = 0.410`. Buying
YES correctly pushed YES's own price *up*, from 0.5 to 0.59 — confirmed numerically, not
just asserted. `price_yes + price_no == 1.0` always, matching the core $1 invariant from
2.4.

### 3.4 Resolution and payout

When the authorized resolver marks the market as "YES wins":

- Every user holding YES shares receives `1 point per YES share` they hold.
- Every user holding NO shares receives `0`.
- This matches the core invariant from 2.4: <cite index="18-1">winning shares pay $1.00... losing
  ones expire worthless</cite> (here, 1 point / 0 points).
- The **seeded liquidity** (`L` on each side) is provider-owned, not user-owned. Standard
  practice, so the platform's seed capital doesn't silently leak into user payouts or
  disappear — see `02_data_model.md` for how this is tracked as a system-owned
  `liquidity_provider` position rather than a special case in the payout code.

### 3.5 Resolution correction (dispute handling)

This is the one place we depart from Polymarket's own approach on purpose, in a
simplifying direction, because our trust model is different — we're not resolving a
market with strangers' money, we're resolving a bet between friends who know each other
and can just talk to the admin.

Polymarket resolves markets via **UMA**, an external decentralized oracle, specifically
so <cite index="10-1">the mechanism does not require an active intermediary to match trades</cite> and
so no single party can quietly manipulate the outcome. We don't need that: our "oracle"
*is* the group admin for a group bet, exactly as the user specified. Standalone public
bets need the platform-level resolver policy identified in
`06_open_questions_and_config.md`. For a group bet:

- Resolution is a normal admin action: pick the winning outcome, payouts run
  immediately.
- If the admin needs to correct it (dispute), the correction is **not** a special
  "dispute flow" — it's implemented as: (1) reverse the previous resolution's payouts
  exactly (subtract what was paid out, restore share positions to unresolved), (2)
  re-run resolution with the new winning outcome. Because payouts are just "1 point per
  winning share," reversal is exact and lossless — this only works because we chose the
  simple points-per-share model in 3.4 rather than something order-dependent.
- All resolution changes are logged with a timestamp, the acting admin's user id, and old
  vs. new winning outcome, and are visible in the bet's history to all participants (see
  `02_data_model.md`, `resolution_events` table). This is the friend-group equivalent of
  an oracle's audit trail — not blockchain-verifiable, but transparent and undeniable
  within the group.

### 3.6 Selling before resolution — explicitly out of scope for v1

Real Polymarket lets you sell your position before resolution: <cite index="13-1">you are never
locked in. If sentiment shifts and your shares increase in value, you can sell before the
event concludes and pocket the difference.</cite> We are **not building this in v1**. It
adds meaningful complexity (reverse-CPMM math, plus UI for "your current position value")
for a feature that matters far less in a friend-group context where markets resolve in
hours or days, not months. Positions are locked from bet-time to resolution-time.
`06_open_questions_and_config.md` documents this as the first "v2 candidate" feature —
the CPMM math in 3.2 is symmetric and selling is a small formula addition, but it's
explicitly deferred so v1 stays simple, per the user's own stated priority.

### 3.7 Multi-outcome markets — explicitly out of scope for v1

v1 supports exactly 2 outcomes per bet (YES/NO, or any custom pair of labels, e.g.
"Person A" / "Person B"). N-outcome markets (e.g. "who wins the fantasy league, pick one
of 6 people") are a real Polymarket feature but require either N pools with a more
complex invariant or splitting into N separate binary markets, and add real complexity
to the resolution and payout logic. Deferred to v2, documented in
`06_open_questions_and_config.md`. The data model in `02_data_model.md` is still
designed so this isn't a rewrite later (outcomes are a table, not a hardcoded pair of
columns), but the AMM math implementation, resolution logic, and UI are 2-outcome-only
for v1.

### 3.8 Required unit tests for the betting engine (non-negotiable)

The coding agent must write these before considering the betting module done. They are
the tests that catch the class of bug that's easy to introduce (sign errors, wrong pool
updated, floating point drift) and easy to miss by eye:

1. `k` is invariant after every buy: `pool_yes * pool_no` before and after a trade are
   equal within a small epsilon (floating point tolerance, not exact equality).
2. Buying YES always increases `price_yes` and decreases `price_no`, and the two always
   sum to `1.0` within epsilon, for a range of pool states (balanced, YES-heavy,
   NO-heavy, near-zero-on-one-side).
3. `shares_out` relative to `amount` depends on the price of the side being bought, and
   the test must assert the *correct* relationship rather than a flat rule — this was
   checked numerically while writing this spec and an earlier draft of this checklist
   had it wrong (claimed `shares_out < amount` always, which is false whenever the side
   being bought is priced under 0.5, e.g. `pool_yes=200, pool_no=100` buying YES for 10
   points yields ~18.2 shares, correctly, because YES is the cheap/underbought side
   there — same as buying more than $10 worth of a stock trading under a dollar). The
   real invariants to test: `shares_out` is always positive and finite for positive
   `amount`; when pools are exactly balanced (price = 0.5 on both sides), `shares_out` is
   strictly less than `amount` (this is the one case where the flat rule does hold, and
   is what the worked example in 3.2 demonstrates); and more generally, `shares_out *
   price_after_side_being_bought` is always less than or equal to `amount` (you never
   extract more value than you paid, evaluated at the post-trade price) — this is the
   version of "no free lunch" that holds unconditionally.
4. **Path independence**: buying `amount` in one trade yields the *exact same* `shares_out`
   (within epsilon) as buying it in two back-to-back trades that sum to `amount`, with
   no other trades in between. This is a real, verified property of the constant-product
   formula (confirmed numerically while writing this spec) — CPMM slippage is a function
   of trade *size*, not of how many separate calls you split it into. Do not write a test
   asserting splitting is "better" or "worse"; assert equality. If a future change to the
   formula breaks path independence, that's a signal something about the formula
   changed in a way worth double-checking, not an expected outcome.
4b. Buying a **larger** `amount` always yields a strictly worse *average* price per share
   (`amount / shares_out`) than buying a **smaller** `amount`, all else equal (this is
   the actual slippage-is-monotonic property, distinct from 4 above — 4 is about
   splitting one trade into two calls, 4b is about comparing genuinely different trade
   sizes).
5. Resolving a market pays exactly `1 * shares_held` points to each winner and `0` to
   each loser, summed across all participants, and the sum paid out never exceeds total
   points wagered by winners plus what losers forfeited (conservation check — no money
   created or destroyed except the seeded liquidity, which is tracked separately per
   3.4).
6. A resolution correction (3.5) is exactly reversible: resolve YES, record all balances,
   correct to NO, assert every affected user's balance equals what it would be had the
   market been resolved NO from the start (not "started YES then corrected" — those must
   be numerically identical, or the reversal logic has a leak).
7. Edge case: a market with only one trade ever placed still resolves correctly and pays
   out correctly (guards against off-by-one/empty-state bugs, not just steady-state
   behavior).
8. Edge case: two users buying the *opposite* side at the exact same amount at market
   start move the pools back toward balance somewhat, not further away — sanity check
   that the formula direction is right in both branches (buy-YES and buy-NO), not just
   the one branch that happened to get tested first.

These are true "does the money math work" tests, not framework smoke tests. They should
live in their own test module (`test_amm_engine.py` or equivalent) separate from
API-level tests, so they can run fast and in isolation — see `05_build_phases.md` for
where this fits in the build order (it comes very early, before any API layer exists).
