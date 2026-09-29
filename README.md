# BullyMarket

BullyMarket is a play-money prediction market for friend groups. It also has a separate
public-market area. No real money is used.

## What it does

- Always-available binary trading using LMSR pricing
- Private groups, invites, member visibility controls, and group-scoped leaderboards
- Optional uploaded cover images for groups and bets
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

Uploaded images are served by the backend under `/media` and persisted in the Compose
`media-data` volume, so rebuilding the API container does not remove them. The default
limit is 5 MB and only JPEG, PNG, WebP, and GIF signatures are accepted. Do not use
`docker compose down -v` unless you intentionally want to delete both database and
uploaded-image volumes.

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

The frontend calls the API at the relative path `/api/v1`, and the Next.js dev server
forwards `/api` and `/media` to `http://localhost:8000`. Override that target with
`API_PROXY_TARGET` if the backend runs elsewhere.

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
BULLYMARKET_SMTP_PORT=587
BULLYMARKET_SMTP_SECURITY=starttls
BULLYMARKET_SMTP_USERNAME=your-smtp-login-from-brevo
BULLYMARKET_SMTP_PASSWORD=your-brevo-smtp-key
BULLYMARKET_EMAIL_FROM_ADDRESS=no-reply@bullymarket.morashad.com
BULLYMARKET_EMAIL_FROM_NAME=BullyMarket
BULLYMARKET_FRONTEND_URL=http://localhost:3000
```

Port `587` uses STARTTLS and is the recommended default here. If you deliberately use
Brevo's implicit-TLS port `465`, set `BULLYMARKET_SMTP_SECURITY=ssl` as well. See
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

## Deploy to Coolify

The deployment is same-origin: the browser only ever talks to the Next.js server,
which forwards `/api` and `/media` to the API over the internal Docker network. There
is no public API domain, no CORS allowlist, and no public URL baked into the frontend
build, so changing the domain never requires a rebuild.

`compose.coolify.yaml` describes `migrate`, `api`, `worker`, and `web`. It deliberately
does **not** define PostgreSQL.

### 1. Create the database

In Coolify, create a managed **PostgreSQL** resource and enable scheduled backups on it.
Backups only work for managed databases, which is why Postgres is not part of the
Compose stack. Copy its internal connection URL.

### 2. Create the application

**+ New → Docker Compose**, pointed at this repository:

- Base Directory: `/`
- Docker Compose Location: `compose.coolify.yaml`
- Enable **Connect to Predefined Network** so the stack can reach the managed database

Set the domain on the `web` service to your public URL. No other service is exposed.

### 3. Set the environment

```env
BULLYMARKET_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE
BULLYMARKET_JWT_SECRET=<openssl rand -base64 48>
BULLYMARKET_FRONTEND_URL=https://bullymarket.example.com
BULLYMARKET_EMAIL_ENABLED=true
BULLYMARKET_SMTP_USERNAME=<brevo smtp login>
BULLYMARKET_SMTP_PASSWORD=<brevo smtp key>
BULLYMARKET_EMAIL_FROM_ADDRESS=no-reply@bullymarket.example.com
```

The connection URL must use the `postgresql+asyncpg://` scheme, not `postgres://`.
`BULLYMARKET_FRONTEND_URL` is used only for links in outgoing email, never for routing.
`BULLYMARKET_CORS_ORIGINS` defaults to `[]` and should stay empty unless something
outside the browser app calls the API directly.

Deploy. `migrate` applies migrations and exits with code 0 before `api` and `worker`
start; a stopped `migrate` container is the expected end state, not a failure.

### 4. Schedule the balance refill

The refill is not automatic. Add a Coolify **Scheduled Task** on this resource:

- Container: `api`
- Command: `python -m app.modules.refill.job`
- Frequency: `0 3 * * 1`

### What persists

Uploaded images live in the `media-data` volume, which survives redeploys but is not
covered by the database backups and is destroyed if the resource is deleted. The
database is covered by the managed Postgres backup schedule.

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
