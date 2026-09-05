# BullyMarket

BullyMarket is a play-money prediction market for friend groups. It also has a separate
public-market area. No real money is used.

## What it does

- Always-available binary trading using LMSR pricing
- Private groups, invites, member visibility controls, and group-scoped leaderboards
- Separate public markets and a public leaderboard
- Final, immutable market resolution and automatic cancellation refunds
- Per-market and aggregate house profit/loss accounting
- Email-verified registration and password recovery
- In-app and email notifications for group-market creation, closing, resolution, and
  refunds
- Notifications are generated only for group markets, never public markets

Group leaderboard results use only realized profit/loss from resolved markets in that
group. Wallet refills, public markets, and activity in other groups do not affect them.
See [How pricing and accounting work](01_overview_and_mechanism.md) for the LMSR details.

## Quick start

### 1. Configure the backend

```bash
cp backend/.env.example backend/.env
```

At minimum, replace these development values in `backend/.env`:

```env
POSTGRES_PASSWORD=replace-with-a-strong-password
BULLYMARKET_JWT_SECRET=replace-with-at-least-32-random-bytes
BULLYMARKET_CORS_ORIGINS=["http://localhost:3000"]
BULLYMARKET_FRONTEND_URL=http://localhost:3000
```

Do not commit `backend/.env`.

### 2. Start the backend

```bash
cd backend
docker compose up -d --build
docker compose ps
```

This starts PostgreSQL, applies migrations, starts the API at `http://localhost:8000`,
and starts the notification/email worker. API documentation is at
`http://localhost:8000/docs`. The frontend intentionally runs separately.

To follow the logs:

```bash
docker compose logs -f api worker
```

To stop the backend without deleting database data:

```bash
docker compose down
```

### 3. Start the frontend

In a second terminal:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

## Configure email with Brevo

Cloudflare continues to host the DNS records, but Brevo sends the messages.

### 1. Authenticate the sending domain

In Brevo, open **Settings → Senders, Domains & Dedicated IPs → Domains**, add the exact
domain used after `@` in the sender address, and authenticate it.

To send from:

```text
no-reply@bullymarket.morashad.com
```

authenticate this exact domain:

```text
bullymarket.morashad.com
```

Copy Brevo's verification, DKIM, and DMARC records into **Cloudflare → DNS → Records**.
Keep DKIM CNAME records **DNS only** (grey cloud). Never create two DMARC TXT records
at the same hostname; update an existing one if necessary. Wait for Brevo to report the
domain as authenticated. See
[Brevo's domain-authentication guide](https://help.brevo.com/hc/en-us/articles/12163873383186-Authenticate-your-domain-with-Brevo-Brevo-code-DKIM-DMARC).

### 2. Create SMTP credentials

In **Brevo → Settings → SMTP & API → SMTP**, copy the displayed **SMTP login** and
generate an **SMTP key**. Use that login and key—not the Brevo account password or an
API key. See
[Brevo's SMTP-key guide](https://help.brevo.com/hc/en-us/articles/7959631848850-Create-and-manage-your-SMTP-keys).

Also open **Settings → Senders, Domains & Dedicated IPs → Senders** and add
`BullyMarket <no-reply@bullymarket.morashad.com>`. An address on an authenticated
domain is automatically verified. See
[Brevo's sender guide](https://help.brevo.com/hc/en-us/articles/208836149-Create-a-new-sender-From-name-and-From-email).

### 3. Add the Brevo settings

Set these values in `backend/.env`:

```env
BULLYMARKET_EMAIL_ENABLED=true
BULLYMARKET_SMTP_HOST=smtp-relay.brevo.com
BULLYMARKET_SMTP_PORT=465
BULLYMARKET_SMTP_USERNAME=your-smtp-login-from-brevo
BULLYMARKET_SMTP_PASSWORD=your-brevo-smtp-key
BULLYMARKET_EMAIL_FROM_ADDRESS=no-reply@bullymarket.morashad.com
BULLYMARKET_EMAIL_FROM_NAME=BullyMarket
BULLYMARKET_FRONTEND_URL=http://localhost:3000
```

Brevo recommends port 587 for clients using STARTTLS, but the current worker uses
implicit TLS. Therefore it must use Brevo's SSL port `465`. See
[Brevo's SMTP port guidance](https://help.brevo.com/hc/en-us/articles/10905415650322-Which-SMTP-port-should-I-use-Port-587-465-or-2525).

Restart the API and worker after changing the environment:

```bash
cd backend
docker compose up -d --build --force-recreate api worker
docker compose logs -f worker
```

Registration and password-reset codes are validated only by the backend and are never
returned to the browser. If email is disabled or the worker is stopped, messages remain
queued and users cannot receive their verification codes.

## Run the balance refill

```bash
cd backend
docker compose run --rm api python -m app.modules.refill.job
```

## Validation

```bash
.venv/bin/pytest backend/tests
.venv/bin/ruff check backend/app backend/migrations backend/tests
.venv/bin/mypy backend/app

cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

## Project documentation

- [Product behavior and LMSR](01_overview_and_mechanism.md)
- [Data model](02_data_model.md)
- [Backend architecture](03_backend_architecture.md)
- [Frontend architecture](04_frontend_architecture.md)
- [Build phases](05_build_phases.md)
- [Configuration decisions](06_open_questions_and_config.md)
