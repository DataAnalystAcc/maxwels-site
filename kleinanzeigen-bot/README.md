# Kleinanzeigen Listing Automation Bot

Automate second-hand listing creation for [Kleinanzeigen.de](https://www.kleinanzeigen.de) — from Telegram photo capture to browser-automated posting.

## How It Works

1. **📱 Capture** — Send photos of items via Telegram (albums + optional notes)
2. **🤖 Identify** — AI identifies the item, generates title & description in German
3. **💰 Price** — Scrapes Kleinanzeigen for comparables, computes competitive price
4. **📝 Review** — Desktop UI to review, edit, and approve draft listings
5. **🚀 Post** — Playwright automates posting to Kleinanzeigen sequentially

## Architecture

| Service | Port | Purpose |
|---|---|---|
| PostgreSQL | 5433 | Database (listings, images, pricing, audit log) |
| Redis | 6380 | Media group buffering, posting queue |
| n8n | 5679 | Workflow orchestration |
| Core API | 8001 | FastAPI backend + Review UI |
| Telegram Bot | — | Photo intake via Telegram |
| Posting Worker | — | Playwright browser automation |

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenRouter API Key (free tier: [openrouter.ai](https://openrouter.ai))

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your credentials:
# - TELEGRAM_BOT_TOKEN
# - ALLOWED_TELEGRAM_CHAT_ID (your Telegram user ID)
# - OPENROUTER_API_KEY
# - DEFAULT_ZIP (your postal code)
```

### 3. Launch

```bash
docker compose up -d
```

### 4. Use

- Send photos to your Telegram bot
- Open Review UI: `http://localhost:8001/review`
- API docs: `http://localhost:8001/docs`
- n8n dashboard: `http://localhost:5679`

## Project Structure

```
kleinanzeigen-bot/
├── docker-compose.yml          # All services
├── db/migrations/              # SQL schema + seeds
├── services/
│   ├── core-api/               # FastAPI backend
│   │   ├── routers/            # API endpoints
│   │   ├── services/           # Business logic (LLM, pricing, scraping)
│   │   └── static/             # Review UI (HTML/JS/CSS)
│   ├── telegram-bot/           # Telegram intake
│   └── posting-worker/         # Playwright posting
├── data/                       # Images, screenshots, backups (volume mount)
└── n8n/workflows/              # Exported n8n workflow JSONs
```

## LLM Cost

Using free OpenRouter models (Gemma 4 27B), the cost per item is **$0.00**.
Fallback to Gemini 2.0 Flash costs ~$0.003/item.

## Configuration

All configuration is via environment variables (see `.env.example`).

Key settings:
- `DRY_RUN=true` — Posting worker fills forms but doesn't submit (default: true)
- `POSTING_MAX_PER_SESSION=10` — Max listings posted before pausing
- `DEFAULT_PRICE_STRATEGY=competitive` — Pricing strategy (fast_sale / competitive / fair)

## Kleinanzeigen Login

Login is **manual by design** to avoid CAPTCHA issues and account bans.
The posting worker saves the session after manual login for reuse.

## License

Private project — not for redistribution.
