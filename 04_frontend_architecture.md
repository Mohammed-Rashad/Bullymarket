# 04. Frontend Architecture

Stack: **Next.js (App Router), TypeScript, a lightweight styling approach (Tailwind is
fine — simple, no build-config decisions to agonize over).**

## 1. Structure, mirroring the backend's module boundaries

The frontend should mirror the backend's module split (auth, groups, bets, trading,
resolution, leaderboard) rather than organizing purely by page/route. This keeps the
"which code am I looking for" answer consistent whether you're in the backend or
frontend, and keeps feature logic (e.g. "how do I compute display price from pool
shares" — which should just call the backend's already-computed price, not reimplement
§3.3 in TypeScript) grouped with its own feature rather than scattered by route.

```
app/                    # Next.js App Router pages/layouts (routing only)
  (auth)/
  groups/[groupId]/
  bets/[betId]/
  leaderboard/
features/                    # mirrors backend modules
  auth/
    api.ts          # typed fetch wrappers for auth endpoints
    hooks.ts          # useLogin, useSignup, useCurrentUser
    components/
  groups/
  bets/
  trading/          # signed LMSR trade flow, quotes, prices, and audit
  leaderboard/
components/          # truly generic, cross-feature UI (Button, Card, Modal — no business logic)
lib/
  api-client.ts          # shared fetch wrapper: base URL, auth header injection, error handling
  types.ts          # shared TS types generated from or matching backend schemas
```

**Rule matching the backend's module boundary:** a `features/leaderboard` component may
import from `features/leaderboard/api.ts`, but should not reach into
`features/trading`'s internals to compute something itself. If leaderboard needs
something trading-related, it goes through trading's own exported hook/function, same
principle as the backend's "call the service, don't reach into internals" rule in
`03_backend_architecture.md` §1.

## 2. Never reimplement the AMM math on the frontend

This is worth stating explicitly because it's a tempting shortcut: when showing the
cost and price impact for a signed share order, **do not port the LMSR formula into
TypeScript and compute it client-side.** The
backend is the single source of truth for this math (that's the entire point of the
`amm` module's isolation in `03_backend_architecture.md` §2.1 — one implementation, one
set of tests, one place a bug can hide). Instead, add a lightweight `/preview` endpoint
(`GET /api/v1/markets/{id}/quote?side=yes&shares=N`) that returns the exact signed cost,
average fill price, and post-trade marginal prices without writing. The frontend calls
it on debounce as the user changes side, action, or shares. Execution calls `/trade`,
which recomputes the quote while holding the market lock.

## 3. Key pages/flows

- **Group dashboard**: list of open bets in the group (respecting visibility rules from
  `02_data_model.md`'s `bet_visibility_overrides`), group leaderboard preview, "create
  bet" action. Creating here always creates a group bet; there is no "make public"
  toggle because public bets do not belong to groups.
- **Bet detail page**: question, current odds from the polled `/price` response, a
  buy-share form with the live quote described above, immutable trade audit, and market
  house reserve/cash/realized-P&L. Selling remains implemented by the signed backend API
  but is temporarily hidden from the client.
  It also lists who's bet on what (respecting visibility — if hidden, only
  show to allowed users), countdown to `end_time`, and — critically — once `status =
  closed`, the resolve UI visible only to the authorized resolver (a group admin for a
  group bet), and once `status = resolved`, the payout breakdown and the
  `resolution_events` history if any corrections happened (§3.5's audit trail needs to
  actually be visible somewhere, not just stored).
- **Leaderboard page**: toggle between weekly / bi-weekly / monthly / all-time. A group
  view shows realized points won/lost only from resolved bets in that selected group;
  the global/public view shows realized points won/lost only from standalone public
  bets. Do not label either value as wallet balance, and never merge a user's results
  from other groups into the current group. These views are backed directly by the
  backend's scoped leaderboard queries (`02_data_model.md`'s "derived, not stored"
  note) — the frontend should not attempt any aggregation itself.
- **Public bets feed**: a separate page (matches the user's spec: "a page to show them")
  listing standalone `visibility='public'` bets. These bets have no group attribution
  or group navigation, and the public-only global leaderboard can appear alongside
  them.

## 4. State management

Keep this simple: **React Query (TanStack Query)** for all server state (bets, groups,
leaderboard data) — it handles caching, refetching, and loading/error states without
hand-rolled `useEffect` + `useState` data-fetching, which is both more code and more
places for subtle bugs (stale closures, race conditions on rapid refetch) to hide. No
need for a separate global client-state library (Redux, Zustand, etc.) unless a genuine
need for complex client-only state shows up during the build — start without one, add
only if actually needed, matching the project's overall "simple first" instruction.

For the live "current odds" display specifically: poll or (if time allows in a later
phase) use a simple WebSocket/SSE connection so odds update without a manual refresh
when other group members place bets. **Defer real-time updates to a later build phase**
(see `05_build_phases.md`) — polling every few seconds is a perfectly good v1 behavior
and far simpler to build and reason about than a WebSocket layer, and the "watch odds
move" feeling still comes through fine with a short poll interval.

## 5. Error and loading states, tied back to backend logging

Every data-fetching hook should surface loading/error states explicitly in the UI (not
swallow errors silently) — a failed bet placement must show the user *why* it failed
(insufficient balance, bet already closed, etc. — these should be distinguishable error
codes from the backend, not one generic "something went wrong"). This matters because
the backend's structured logging (`03_backend_architecture.md` §4) is only as useful as
the ability to correlate a user's bug report ("my bet didn't go through") with a
`request_id` — so failed-request toasts/errors in the UI should be paired with enough
detail that a user could screenshot it and a developer could grep the logs for what
happened.
