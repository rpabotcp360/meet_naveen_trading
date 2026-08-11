# NSE Intraday Signal Scanner

Local Windows intraday signal scanning application using Upstox Market Data V3, Naveen Algo V3 Alpha logic (ported from Pine Script), Telegram notifications, and a realtime Next.js dashboard.

**Signal generation and monitoring only — no order placement.**

## Quick Start (Windows)

```powershell
# 1. First-time setup
.\scripts\setup.ps1

# 2. Optional: paste Analytics Token in Settings UI (recommended)
#    Or put token in .env as UPSTOX_API_KEY=eyJ...

# 3. Start both services
.\scripts\start-all.ps1
```

- Backend: http://127.0.0.1:8000
- Frontend: http://127.0.0.1:3000
- API docs: http://127.0.0.1:8000/docs

## Setup Checklist

1. **Upstox**: Settings → paste **Analytics Token** → Save Token (no Client Secret needed)
2. **Telegram**: Settings → Bot Token + Chat ID → Send Test
3. **Scanner**: Settings → Start Scanner (during market hours)

See [docs/upstox-setup.md](docs/upstox-setup.md) and [docs/telegram-setup.md](docs/telegram-setup.md).

## Deploy (Ubuntu)

Production deploy on Ubuntu 22.04/24.04 with Python 3.12, Node.js 20, nginx, and systemd:

See [docs/ubuntu-deploy.md](docs/ubuntu-deploy.md).

## Architecture

```
Upstox V3 WebSocket → candle builder → indicator engine → signal engine → SQLite + Telegram + browser WebSocket
```

See [docs/architecture.md](docs/architecture.md).

## Project Structure

```
backend/     Python FastAPI — scanner engine, Upstox, Telegram
frontend/    Next.js — dashboard, scanner, watchlist, settings
data/        SQLite database (gitignored)
logs/        Rotating log files (gitignored)
scripts/     PowerShell start/stop scripts
docs/        Setup and architecture docs
```

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
pytest tests/ -v
```

## Key Defaults

| Setting | Value |
|---------|-------|
| Market timezone | Asia/Kolkata |
| Signal timeframe | 5m |
| HTF | 15m |
| Scanner start | 09:20 IST |
| Stop new signals | 14:45 IST |
| Top N universe | 30 |
| Capital per trade | ₹20,000 |
| Strategy mode | Balanced |

## Security

- Upstox Analytics Token and Telegram bot tokens stored in **Windows Credential Manager** via `keyring`
- No passwords collected
- Secrets never logged or returned to frontend after save

.\scripts\start-all.ps1
