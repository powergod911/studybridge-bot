# StudyBridge Bot

Telegram bot for a private A/L study group. It routes commands, text, and photos to DeepSeek via NVIDIA NIM or Gemini 3.5 Flash, logs each interaction in Postgres, and uses Redis-backed aiogram FSM storage.

## Before VPS Deployment

Run these checks on Shadow before editing `.env` or deploying:

```bash
docker network ls
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Networks}}'
```

Confirm:

- The existing bots' Docker network name. If it is not `bots_default`, edit `docker-compose.yml` to match.
- The Postgres container hostname on that network. The default `.env.example` assumes `postgres`.
- The Redis container hostname and DB indexes already in use. This project defaults to Redis DB `2`.

If those cannot be confirmed from the VPS, stop and inspect the existing compose files before deploying.

## Configure

```bash
cp .env.example .env
```

Fill:

```bash
TELEGRAM_BOT_TOKEN=
GEMINI_API_KEY=
NVIDIA_API_KEY=
POSTGRES_DSN=postgresql+asyncpg://studybridge_user:PASSWORD@postgres:5432/studybridge
REDIS_URL=redis://redis:6379/2
```

Use a new BotFather bot token. Do not reuse Mai, Paddock, or Mohini tokens.

Recommended BotFather setting for v1:

```text
/setprivacy -> Enable
```

With privacy mode on, students should use `/deep`, `/gem`, reply to the bot, or mention it.

## Create Database/User

Use the real Postgres container name from `docker ps`.

```bash
docker exec -it POSTGRES_CONTAINER psql -U postgres
```

Then in `psql`:

```sql
CREATE DATABASE studybridge;
CREATE USER studybridge_user WITH PASSWORD 'CHANGE_ME';
GRANT ALL PRIVILEGES ON DATABASE studybridge TO studybridge_user;
\c studybridge
GRANT ALL ON SCHEMA public TO studybridge_user;
```

## Run Migrations

After `.env` is filled:

```bash
docker compose run --rm studybridge alembic upgrade head
```

## Deploy

```bash
docker compose up -d --build
docker logs -f studybridge_bot
```

This compose file starts only `studybridge_bot` and joins the existing external Docker network. It does not restart Mai, Paddock, Mohini, Postgres, or Redis.

## GitHub Flow

From this folder:

```bash
git init
git add .
git commit -m "Initial StudyBridge bot MVP"
git branch -M main
git remote add origin git@github.com:YOUR_USER/studybridge.git
git push -u origin main
```

On the VPS:

```bash
git clone git@github.com:YOUR_USER/studybridge.git
cd studybridge
cp .env.example .env
```

Fill `.env`, verify Docker network names, run migrations, then deploy.
