# Shadow Mentor

Shadow Mentor is a Telegram Mini App and bot for Sri Lankan G.C.E. A/L students. The
Railway service hosts the web interface, validates Telegram users, receives bot updates
through a webhook, and routes questions to DeepSeek through NVIDIA NIM or Gemini.

## What Students Get

- A Telegram-native chat interface
- Properly rendered Markdown and LaTeX equations
- DeepSeek, Gemini, or automatic model routing
- Gemini image questions
- Sinhala and English answers
- Plain-text fallback through ordinary bot messages

## Railway Architecture

One Railway application service runs FastAPI and the Telegram webhook. Add Railway
PostgreSQL and Redis services to the same project. `railway.json` runs Alembic before
each deployment and checks `/health` before promoting the new version.

Required application variables:

```text
TELEGRAM_BOT_TOKEN=
GEMINI_API_KEY=
NVIDIA_API_KEY=
POSTGRES_DSN=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
WEBAPP_URL=https://YOUR-DOMAIN.up.railway.app
```

`POSTGRES_DSN` accepts both Railway's `postgresql://` URL and an explicit
`postgresql+asyncpg://` URL.

Optional variables:

```text
TELEGRAM_AUTH_MAX_AGE_SECONDS=86400
WEB_RATE_LIMIT_PER_MINUTE=12
SHADOW_MENTOR_DEV_MODE=false
```

Never enable `SHADOW_MENTOR_DEV_MODE` on Railway. It bypasses Telegram authentication
only when testing the UI locally.

## Deploy

1. Connect this GitHub repository to the existing Railway application service.
2. Add Railway PostgreSQL and Redis services.
3. Set the variables above.
4. Generate a public Railway domain.
5. Set `WEBAPP_URL` to that HTTPS domain and redeploy.
6. Open the bot and send `/start` or `/app`.

The application configures the Telegram webhook and chat menu button during startup.
Only one Railway replica should be used unless webhook update deduplication is added.

## BotFather

In `@BotFather`, open:

```text
/mybots
Select Shadow Mentor
Bot Settings
Configure Mini App
Enable Mini App
```

Use the same HTTPS Railway domain when BotFather asks for the Mini App URL.

## Local Bot

Copy `.env.example` to `.env`, fill the values, and run:

```bash
python -m bot.main
```

This local command switches Telegram back to polling. Do not run it while the Railway
deployment is serving the same bot token.

## Local Web Preview

Set `SHADOW_MENTOR_DEV_MODE=true`, provide working PostgreSQL and Redis URLs, then run:

```bash
uvicorn web.main:app --reload
```

Open `http://127.0.0.1:8000`. Preview mode can call the API without Telegram init data,
so it must never be enabled in production.
