# Architecture

## Overview

The NSE Intraday Scanner is a local Windows application with a Python FastAPI backend and Next.js frontend. It scans NSE equities using Upstox realtime data, applies the Naveen Algo V3 Alpha signal logic (ported from Pine Script), persists signals to SQLite, sends Telegram alerts, and pushes realtime updates to the browser via WebSocket.

## Data Flow

```
Upstox REST (OAuth, instruments, historical, snapshots)
Upstox V3 WebSocket (realtime ticks)
        ↓
Market Data Engine (5m/15m candle builder, backfill)
        ↓
Indicator Engine (EMA, VWAP, RSI, MACD, Supertrend, ATR, RVOL)
        ↓
Signal Engine (Naveen V3 scoring, filters, Entry/SL/T1/T2/T3)
        ↓
┌───────────────────┬────────────────────┐
│ SQLite (signals)  │ Telegram Notifier  │
│ Browser WebSocket │ (async, retry)     │
└───────────────────┴────────────────────┘
```

## Backend Modules

| Module | Responsibility |
|--------|---------------|
| `upstox/` | OAuth, REST, V3 WebSocket, protobuf decode |
| `market_data/` | Candle aggregation, backfill, live state |
| `indicators/` | Pure indicator calculations |
| `signals/` | Pine-ported scoring, filters, levels, dedupe |
| `universe/` | Top 30 ranking, watchlist merge |
| `notifications/` | Telegram formatting and delivery |
| `websocket/` | Browser event broadcaster |
| `scheduler/` | Daily session tasks (09:10, 09:20, 14:45, 15:15 IST) |
| `storage/` | SQLModel + SQLite repositories |

## Frontend Pages

| Route | Purpose |
|-------|---------|
| `/` | Dashboard — active signals, summary cards |
| `/scanner` | Live scanner table for all symbols |
| `/watchlist` | Manual watch list management |
| `/history` | Persisted signal history |
| `/settings` | Trading, Upstox, Telegram, scanner controls |
| `/status` | System health and integration states |

## Timezone

All market logic uses `Asia/Kolkata`. Timestamps stored as UTC. Windows local timezone is ignored for NSE session boundaries.

## Signal Dedupe

Event key: `symbol|5m|candle_close_utc|direction`

One notification per qualifying completed 5m candle per symbol/direction. Repeats on subsequent candles if conditions still hold.
