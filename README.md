# BullyMarket

BullyMarket is a play-money prediction market for friend groups, plus a completely
separate public betting scope. It combines a FastAPI/PostgreSQL backend with a Next.js
frontend.

The important product invariant is enforced from the database through the UI:

- A group leaderboard uses realized profit/loss only from resolved bets in that group.
- The global leaderboard uses realized profit/loss only from standalone public bets.
- Refills and overall wallet balances never determine leaderboard rank.
- A bet is either group-scoped or public; it can never be both.

## LMSR pricing and house accounting

Every new binary market uses a Logarithmic Market Scoring Rule (LMSR), so the platform
is the counterparty and a user never waits for a matching order. A market stores net
YES/NO shares `q_yes`, `q_no` and a fixed liquidity value `b`:

```text
C(q_yes, q_no) = b * ln(exp(q_yes / b) + exp(q_no / b))
P_yes = exp(q_yes / b) / (exp(q_yes / b) + exp(q_no / b))
trade_cost = C(q_after) - C(q_before)
```

Positive shares buy; negative shares sell existing holdings. The signed cost is paid
from the user to the house, and a winning share redeems for exactly 1 point. The
maximum possible house loss is bounded by `b * ln(2)`, which is recorded as reserved
exposure when the market is created. Every trade, reserve, refund, payout, and realized
house P/L change is stored in an append-only audit ledger. A resolution is final and
cannot be corrected or replaced. House summaries
are available per market, per exact group, and globally. Historical CPMM markets retain
their original pricing tag and data. The backend retains signed selling support, while
the current frontend intentionally exposes purchases only.

## Repository layout

- `backend/` — async FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, pytest
- `frontend/` — Next.js App Router, TypeScript, Tailwind CSS, TanStack Query
- `backend/compose.yaml` — the API, notification/email worker, migration, and PostgreSQL stack
- `01_...md` through `06_...md` — product and architecture decisions

## Run with Docker

The Compose project lives in `backend/` and starts PostgreSQL, applies all pending
Alembic migrations, then starts the API and notification/email worker:

```bash
cd backend
cp .env.example .env
docker compose up --build
```

The API is available at `http://localhost:8000`, and its interactive documentation is
at `http://localhost:8000/docs`. Run the frontend separately using the instructions
under [Frontend](#2-frontend); it connects to this API through the default
`frontend/.env.example` configuration.

The database is persisted in the `bullymarket_postgres-data` Docker volume. Stop the
stack without deleting its data:

```bash
cd backend
docker compose down
```

For any shared or internet-accessible environment, replace `POSTGRES_PASSWORD` and
`BULLYMARKET_JWT_SECRET` in `backend/.env` before starting the stack.

Run the periodic balance refill inside the API image when needed:

```bash
cd backend
docker compose run --rm api python -m app.modules.refill.job
```

## Run without Docker

### 1. Backend

Python 3.12+ and PostgreSQL are supported. For a quick local run without PostgreSQL,
Alembic and the API also support an on-disk SQLite database:

```bash
uv venv .venv
uv pip install -e 'backend[dev]'
export BULLYMARKET_DATABASE_URL='sqlite+aiosqlite:///./backend/bullymarket.db'
.venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/uvicorn app.main:app --app-dir backend --reload
```

For PostgreSQL, use the defaults from `backend/.env.example` with a locally installed
database:

```bash
cp backend/.env.example backend/.env
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive OpenAPI documentation is
at `http://localhost:8000/docs`.

Run the scheduled refill as a separate daily cron command:

```bash
cd backend
../.venv/bin/python -m app.modules.refill.job
```

Run notifications and email delivery as a separate long-running process when not using
Compose:

```bash
cd backend
../.venv/bin/python -m app.modules.notifications.worker
```

## Email with a Cloudflare domain

Yes—if the domain is onboarded to Cloudflare Email Service **Email Sending**. Email
Routing/DNS by itself only handles routing records; it does not make this application
an outbound mail server. In the Cloudflare dashboard:

1. Enable Email Sending for the domain and publish the SPF/DKIM records Cloudflare
   provides. Add a DMARC policy for the domain as well.
2. Create a Cloudflare API token with `Email Sending: Edit` permission.
3. Copy `backend/.env.example` to `backend/.env`, set
   `BULLYMARKET_SMTP_PASSWORD` to that token, set
   `BULLYMARKET_EMAIL_FROM_ADDRESS` to an address on the onboarded domain, and set
   `BULLYMARKET_EMAIL_ENABLED=true`.
4. Keep the SMTP host `smtp.mx.cloudflare.net`, port `465`, and username `api_token`.
   The worker uses implicit TLS, which is the mode required by Cloudflare's SMTP
   endpoint.

Cloudflare references: [SMTP credentials and endpoint](https://developers.cloudflare.com/email-service/api/send-emails/smtp/),
[SMTP sending example](https://developers.cloudflare.com/email-service/examples/email-sending/smtp/),
and [email authentication](https://developers.cloudflare.com/email-service/concepts/email-authentication/).
Do not commit the API token.

Registration is not completed until the backend validates the six-digit email code.
The code is stored as an HMAC hash in the verification table and is never returned by
the API. Password reset behaves the same way and deliberately gives the same request
response for known and unknown addresses. In-app alerts and optional emails cover group
bet creation, close time, creator resolution reminders, final resolution, and participant
refunds. **Public bets never create notifications or email messages.**

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

## Validation

```bash
.venv/bin/pytest backend/tests
.venv/bin/ruff check backend/app backend/migrations backend/tests
.venv/bin/mypy backend/app
.venv/bin/alembic -c backend/alembic.ini upgrade head --sql

cd frontend
npm run typecheck
npm run lint
npm test
npm run build
npm audit --omit=dev
```

The backend integration suite creates databases through `alembic upgrade head`; it
never substitutes `Base.metadata.create_all()`.

## Plan documents

1. [`01_overview_and_mechanism.md`](01_overview_and_mechanism.md) — product behavior,
   LMSR math, and house accounting
2. [`02_data_model.md`](02_data_model.md) — relational schema and leaderboard rules
3. [`03_backend_architecture.md`](03_backend_architecture.md) — API module boundaries
4. [`04_frontend_architecture.md`](04_frontend_architecture.md) — client structure
5. [`05_build_phases.md`](05_build_phases.md) — implementation and verification gates
6. [`06_open_questions_and_config.md`](06_open_questions_and_config.md) — configuration
   and resolved product decisions

No real money is used anywhere. Points only.
