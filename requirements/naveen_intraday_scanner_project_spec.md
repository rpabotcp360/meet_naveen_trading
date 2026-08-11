# NSE Intraday Signal Scanner – Project Specification

## 1. Project Goal

Build a local Windows-based intraday signal scanning application that uses the official Upstox API as the primary market-data source, applies the same logic as the existing **Naveen Algo V3 Alpha**, sends Telegram notifications whenever BUY conditions are satisfied, and displays realtime signal details in a clean Stripe-style React web application.

The application is for **signal generation and monitoring only**. It must not place, modify, or cancel any orders.

The application should scan:

- A dynamic **Top 30 NSE stock universe** selected every market day.
- Every symbol manually added to the user's Watch List.
- Duplicates between Top 30 and Watch List must be removed automatically.

The web application must show realtime data for each qualifying signal, including at minimum:

- Stock name / trading symbol
- Direction: BUY or SELL
- Current price
- Entry price
- Stop Loss
- Target 1
- Target 2
- Target 3
- Signal score
- Relative volume
- Trend state
- VWAP state
- Higher-timeframe state
- Signal timestamp

Telegram must receive the same core signal information.

---

# 2. Explicit Scope

## Included in V1

- Official Upstox API integration
- Upstox OAuth/login status
- Upstox Market Data Feed V3 WebSocket
- NSE equity universe management
- Dynamic Top 30 scanner universe
- Manual Watch List
- 5-minute primary signal timeframe
- 15-minute higher-timeframe confirmation
- Naveen Algo V3 Alpha signal logic
- Realtime signal calculations
- Realtime dashboard using WebSockets
- Telegram notifications
- Telegram configuration screen
- Upstox configuration/authentication screen
- SQLite local persistence
- Signal history
- Scanner status and health monitoring
- Local Windows deployment
- Light-mode Stripe-style enterprise UI

## Explicitly Excluded from V1

- Automatic Upstox order placement
- Manual order placement from this app
- Paper trading portfolio
- Position management
- Broker order synchronization
- Portfolio/holdings trading actions
- Options trading logic
- Futures trading logic
- Cloud deployment
- PostgreSQL
- Redis
- TradingView dependency

The application may later be extended to support these features, but V1 must not require them.

---

# 3. Recommended Technology Stack

## Backend

Use Python.

Recommended components:

- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic
- SQLAlchemy or SQLModel
- SQLite
- Pandas
- NumPy
- `ta` or equivalent technical indicator package where appropriate
- Upstox official SDK when practical
- Native WebSocket client for Market Data Feed V3 where necessary
- Protobuf decoding for Upstox Market Data Feed V3
- APScheduler or an internal asyncio scheduler
- `httpx` for HTTP requests
- `python-telegram-bot` or Telegram Bot API through `httpx`
- `keyring` for Windows Credential Manager secret storage

## Frontend

Use React with Next.js.

Recommended components:

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui or Radix primitives where useful
- Lucide icons
- TanStack Query
- Zustand only if local shared UI state is required
- Native WebSocket client for realtime updates
- TradingView Lightweight Charts only if a price chart is later added

## Storage

Use SQLite only.

SQLite should persist:

- Watch List
- Signal history
- Scanner universe snapshots
- Non-sensitive application settings
- Notification history
- Runtime health events if needed

Sensitive values must not be stored unencrypted in SQLite.

---

# 4. Upstox Integration Requirements

The integration must use current official Upstox APIs.

Upstox currently uses OAuth 2.0 authorization-code authentication. The application must never collect or store the user's Upstox login password. Authentication must occur through the Upstox-hosted login flow.

Use the current **Market Data Feed V3** for realtime streaming. The V3 feed uses an authorized WebSocket URL and Protobuf encoded market messages.

Use `instrument_key` as the canonical Upstox instrument identifier. Do not use exchange token as the primary persistent identifier because Upstox recommends `instrument_key` for stable instrument identification.

Use the Upstox JSON instrument data or the Upstox instrument-search API for resolving symbols.

The integration layer must be isolated behind an adapter/service interface so API changes do not require changes throughout the signal engine.

Required Upstox services:

1. Authentication service
2. Instrument master service
3. Market snapshot service
4. Historical candle service
5. Realtime market WebSocket service
6. Market-status service

The application is read-only with respect to trading.

---

# 5. Authentication and Secret Handling

## Upstox

Settings UI must include:

- API Key / Client ID
- Redirect URI
- Connection status
- Connect Upstox button
- Reconnect button
- Disconnect button
- Last successful authentication timestamp
- Access-token status

Do not display client secret after it has been saved.

Sensitive Upstox secrets and access tokens should be persisted using **Windows Credential Manager**, via Python `keyring`, rather than plain SQLite.

SQLite may contain only metadata such as:

- Upstox configured: true/false
- Last authenticated time
- User-visible account label
- Redirect URI

## Telegram

The Settings page must allow the user to configure:

- Telegram Bot Token
- Telegram Chat ID
- Enable/Disable Telegram notifications
- Test Notification button

The bot token must be masked after save.

Recommended storage:

- Bot token: Windows Credential Manager
- Chat ID: SQLite
- Enabled flag: SQLite

The user must be able to update both from the UI.

---

# 6. Telegram Setup Instructions to Include in the Application

The application should have an expandable help section explaining:

1. Open Telegram.
2. Search for `@BotFather`.
3. Start a chat with BotFather.
4. Run `/newbot`.
5. Choose a bot name.
6. Choose a bot username ending in `bot`.
7. Copy the generated Bot Token.
8. Open a chat with the newly created bot and send at least one message such as `Hello`.
9. Obtain the Chat ID using the Telegram Bot API or another documented method.
10. Open this application's Settings > Telegram.
11. Paste Bot Token.
12. Paste Chat ID.
13. Click Save.
14. Click Send Test Notification.
15. Show success/failure clearly.

Never log the full Telegram Bot Token.

---

# 7. Timezone Rules

This is critical.

The Windows machine is configured in **US Eastern Time**.

All market/session calculations must explicitly use:

- `Asia/Kolkata`

Do not rely on the Windows local timezone for NSE session logic.

Store timestamps internally in UTC.

For display:

- Default market timestamps: IST
- Optionally show local machine time in diagnostic screens only

Scanner session:

- 09:15 IST: start realtime collection
- 09:20 IST: signal eligibility begins
- 14:45 IST: stop generating new trade-entry signals
- 15:15 IST: end active scanner session

Recommended internal scheduling rules:

- Instrument/universe preparation: before market open
- Market-status verification: before starting scanner
- Use Upstox market-status API as an additional guard
- Respect NSE holidays; do not scan when NSE is closed

---

# 8. Timeframe Design

Use the following timeframes in V1:

## Primary Signal Timeframe

**5 minutes**

This should drive:

- EMA 9
- EMA 21
- EMA 200
- VWAP
- RSI
- MACD
- Supertrend
- ATR
- Relative volume
- Breakout/breakdown
- Signal score
- Entry, Stop, T1, T2, T3

## Higher Timeframe

**15 minutes**

Use confirmed 15-minute candles for higher-timeframe trend confirmation.

Do not generate signals directly from 1-minute candles.

The WebSocket may consume realtime ticks or 1-minute market updates internally, but the trading signal engine must evaluate on completed 5-minute candles.

This design reduces noise while keeping the system responsive enough for intraday trading.

---

# 9. Dynamic Top 30 NSE Universe

The application must automatically build a Top 30 NSE equity universe every trading day.

Do not simply hardcode 30 symbols forever.

## Base Universe

Use a liquid NSE equity base universe such as:

- NIFTY 50
- plus selected highly liquid NIFTY Next 50 names

The base universe should generally be around 50-100 liquid equities.

The system must exclude:

- ETFs unless explicitly configured
- Penny stocks
- Suspended instruments
- Illiquid securities
- Instruments with invalid/missing market data
- Symbols outside the configured price range

## Daily Ranking

Before active signal scanning, rank the base universe using available Upstox snapshot data.

Recommended factors:

- Current traded volume
- Relative volume
- Percentage change versus previous close
- Intraday range / ATR
- Turnover/liquidity proxy
- Valid bid/ask and recent trading activity when available

Suggested ranking weights:

- Relative Volume: 30%
- Volume/Liquidity: 25%
- Intraday movement: 20%
- ATR/volatility suitability: 15%
- Trend/activity confirmation: 10%

Take the highest-ranked 30 stocks.

The exact algorithm must live in one configurable module and be easy to tune.

## Watch List Merge

Final scan universe:

**Dynamic Top 30 + Enabled Watch List Symbols**

Rules:

- Remove duplicates
- Watch List symbols are always included regardless of Top 30 rank
- Disabled Watch List symbols are not scanned
- Show source badge: `TOP 30`, `WATCHLIST`, or `BOTH`

---

# 10. Watch List Requirements

Create a dedicated Watch List page.

User actions:

- Search NSE equities
- Add stock
- Remove stock
- Enable scanning
- Disable scanning
- Pin/favorite stock
- View live status
- View latest signal

Columns/cards should include:

- Symbol
- Company name
- LTP
- Change %
- RVOL
- BUY Score
- SELL Score
- Current signal state
- Enabled/Disabled
- Source

Search must resolve valid Upstox NSE equity instruments.

Do not allow duplicate entries.

Persist Watch List in SQLite.

---

# 11. Naveen Algo V3 Alpha Logic

The Python backend must reproduce the same conceptual logic used in the current Pine strategy.

Do not depend on TradingView for signal generation.

## Core Indicators

Default values:

- Fast EMA: 9
- Slow EMA: 21
- Major EMA: 200
- RSI: 14
- MACD: 12 / 26 / 9
- Supertrend ATR: 10
- Supertrend factor: mode-dependent
- ATR: 14
- Volume average: 20
- Breakout lookback: 20
- Higher timeframe: 15m
- HTF EMA: 50

## Modes

Support:

- Aggressive
- Balanced
- Conservative

Default mode for V1 UI: **Balanced** unless the user changes it.

Settings must be editable in the UI.

## BUY Score

Conceptual maximum: 100.

Default scoring:

- EMA bullish: +15
- Price above VWAP: +15
- Supertrend bullish: +15
- RSI bullish: +10
- MACD bullish: +10
- Healthy volume: +5
- Volume spike: +10
- Bullish breakout: +10
- 15m HTF bullish: +5
- Price above EMA 200: +5

## SELL Score

Mirror the BUY logic:

- EMA bearish: +15
- Price below VWAP: +15
- Supertrend bearish: +15
- RSI bearish: +10
- MACD bearish: +10
- Healthy volume: +5
- Volume spike: +10
- Bearish breakdown: +10
- 15m HTF bearish: +5
- Price below EMA 200: +5

## Thresholds

Mode defaults should follow the existing strategy concept:

- Aggressive: approximately 58
- Balanced: approximately 68
- Conservative: approximately 78

Keep values configurable.

## Non-Repainting Rule

Signals must only be finalized using completed 5-minute candles.

Higher-timeframe trend must use completed 15-minute candles.

A signal may be displayed as a provisional live state before candle close, but Telegram must only use finalized signal conditions unless the user later enables intrabar alerts.

Default behavior: finalized candle-close signals only.

---

# 12. Signal Frequency Requirement

The user explicitly wants notifications whenever a BUY condition satisfies.

Therefore, do **not** suppress repeated qualifying BUY notifications for an entire trade lifecycle.

However, avoid notification spam caused by multiple ticks within the same candle.

Required rule:

- Evaluate finalized BUY/SELL conditions at each completed 5-minute candle.
- If BUY condition is satisfied on a completed candle, send one BUY notification for that stock/candle.
- If BUY condition remains satisfied on the next completed 5-minute candle, send another BUY notification.
- Same behavior for SELL.
- Never send duplicate notifications for the same symbol + direction + candle timestamp.

Use a deterministic event key:

`symbol + timeframe + candle_close_timestamp + direction`

Persist sent event keys so application restarts do not resend old notifications.

---

# 13. Entry, Stop Loss and Profit Targets

For every qualifying signal calculate:

- Entry
- Stop Loss
- Target 1
- Target 2
- Target 3

Use ATR-based levels matching the existing V3 Alpha philosophy.

Recommended Balanced defaults:

- Initial Stop: 1.5 ATR
- T1: 2.0 ATR
- T2: 4.0 ATR
- T3: 6.0 ATR

Long:

- Entry = completed signal candle close
- Stop = Entry - ATR × stop multiplier
- T1 = Entry + ATR × T1 multiplier
- T2 = Entry + ATR × T2 multiplier
- T3 = Entry + ATR × T3 multiplier

Short:

- Entry = completed signal candle close
- Stop = Entry + ATR × stop multiplier
- T1 = Entry - ATR × T1 multiplier
- T2 = Entry - ATR × T2 multiplier
- T3 = Entry - ATR × T3 multiplier

Display all prices using the instrument tick-size precision.

---

# 14. Capital Handling

The current requirement is **₹20,000 per trade**.

The application does not place orders, but it should calculate an informational quantity.

Display:

- Capital per trade: ₹20,000
- Approximate quantity = floor(₹20,000 / Entry Price)
- Estimated capital used
- Risk per share
- Estimated total stop-loss risk

This is informational only.

Do not prevent a signal merely because calculated quantity is zero; instead mark it as `Capital insufficient` if the share price exceeds the configured capital per trade.

Capital per trade must be editable in Settings.

---

# 15. Telegram Notification Format

Use a concise mobile-friendly message.

Example BUY notification:

**BUY SIGNAL**

- Stock: TATASTEEL
- Entry: ₹154.20
- Qty for ₹20k: 129
- Stop Loss: ₹152.80
- T1: ₹156.30
- T2: ₹158.50
- T3: ₹161.20
- BUY Score: 82/100
- Mode: Balanced
- Timeframe: 5m
- RVOL: 1.84x
- Trend: Bullish
- VWAP: Above
- HTF: Bullish
- Time: 10:25 IST

SELL should use equivalent formatting.

Optional emoji can be used sparingly:

- Green circle for BUY
- Red circle for SELL

Do not over-format.

Telegram failures must never stop the scanner.

On Telegram failure:

- Record error
- Show degraded Telegram status
- Retry using bounded exponential backoff
- Do not duplicate already-successful notifications

---

# 16. Realtime Web Application Architecture

Browser must update without manual refresh.

Recommended flow:

Upstox V3 WebSocket
→ market-data service
→ candle builder
→ indicator engine
→ signal engine
→ application state
→ FastAPI WebSocket
→ React UI

The browser WebSocket should deliver normalized JSON objects rather than raw Upstox Protobuf messages.

Suggested event categories:

- `market_tick`
- `scanner_update`
- `signal_created`
- `watchlist_updated`
- `scanner_status`
- `telegram_status`
- `upstox_status`

Do not send every raw exchange tick to every browser if it is unnecessary.

Throttle general UI updates appropriately while delivering new signal events immediately.

---

# 17. Frontend UI/UX Direction

## Overall Style

- Light mode only
- Stripe-inspired
- Enterprise-grade
- Minimal
- High information density without clutter
- Large whitespace rhythm
- Soft neutral backgrounds
- Thin borders
- Restrained shadows
- Rounded cards
- Clear typography hierarchy
- Avoid flashy gradients
- Avoid neon trading-terminal appearance
- Avoid excessive red/green surfaces
- Use color primarily for states and signals

## Responsive Design

The UI must work well on:

- Desktop 1920×1080
- Laptop 1366×768
- Tablet
- Mobile

Mobile use is important.

Cards and tables must become mobile-friendly stacked layouts where required.

---

# 18. Application Pages

## 18.1 Dashboard

This is the primary screen.

Header:

- Application name
- NSE market status
- Current IST time
- Upstox connection status
- Telegram connection status
- Scanner state

Summary cards:

- Symbols being scanned
- Top 30 count
- Watch List count
- BUY signals today
- SELL signals today
- Last scan/candle time

Main Active Signals area:

Each signal card should show:

- Stock symbol
- Company name
- BUY/SELL badge
- Signal score
- Current price
- Entry
- Stop
- T1
- T2
- T3
- RVOL
- Trend
- VWAP state
- HTF state
- Signal age
- Source: Top 30 / Watch List / Both

Newest signals first.

Include filters:

- All
- BUY
- SELL
- Top 30
- Watch List
- Score range

## 18.2 Live Scanner

Show every currently scanned stock.

Recommended columns:

- Symbol
- LTP
- Change %
- RVOL
- BUY Score
- SELL Score
- EMA trend
- VWAP
- Supertrend
- RSI
- MACD
- HTF
- Scanner state
- Source

Support sorting by:

- BUY Score
- SELL Score
- RVOL
- % change
- Symbol

Use row virtualization if the list grows significantly.

## 18.3 Watch List

Features described earlier.

Prominent `Add Stock` action.

Search should be fast and keyboard-friendly.

## 18.4 Signal History

Persist signals in SQLite.

Columns:

- Date/time IST
- Symbol
- Direction
- Entry
- Stop
- T1
- T2
- T3
- BUY Score
- SELL Score
- RVOL
- Mode
- Source
- Notification status

Filters:

- Date
- Symbol
- BUY/SELL
- Score
- Source

Allow CSV export later if easy, but CSV export is not required for the first milestone.

## 18.5 Settings

Sections:

### Trading

- Capital per trade
- Strategy mode
- Signal thresholds
- Session settings
- Timeframes

### Scanner

- Top-N count; default 30
- Base universe
- Price filters
- RVOL settings
- Universe refresh settings

### Upstox

- API configuration
- Connect/Reconnect
- Connection state

### Telegram

- Bot Token
- Chat ID
- Enable notifications
- Test notification

### Display

- Realtime update preference
- Number formatting

Do not add dark-mode controls in V1.

## 18.6 System Status

Useful for debugging.

Show:

- Backend status
- Upstox REST status
- Upstox WebSocket state
- WebSocket last message time
- Subscribed instrument count
- Last completed 5m candle
- Last completed 15m candle
- Telegram status
- SQLite status
- Application uptime
- Last exception/error

---

# 19. SQLite Data Model

Suggested tables:

## watchlist

Fields:

- id
- instrument_key
- trading_symbol
- company_name
- exchange
- enabled
- pinned
- created_at
- updated_at

## signals

Fields:

- id
- event_key unique
- instrument_key
- symbol
- company_name
- direction
- candle_timestamp_utc
- generated_at_utc
- entry
- stop_loss
- target_1
- target_2
- target_3
- buy_score
- sell_score
- rvol
- rsi
- atr
- vwap
- ema_fast
- ema_slow
- ema_major
- htf_direction
- supertrend_direction
- mode
- universe_source
- telegram_sent
- telegram_sent_at

## scanner_universe

Fields:

- id
- session_date
- instrument_key
- symbol
- rank
- rank_score
- source
- created_at

## app_settings

Only non-sensitive settings.

Examples:

- capital_per_trade
- strategy_mode
- top_n
- telegram_enabled
- telegram_chat_id
- scanner_enabled

## notification_log

- id
- signal_id
- channel
- status
- error_message
- attempted_at

Sensitive tokens should not be stored in these tables.

---

# 20. Backend Modules

Recommended architecture:

## `upstox`

Responsibilities:

- OAuth
- REST API wrapper
- instrument resolution
- Market Data V3 authorization
- WebSocket connection
- Protobuf decoding
- reconnect logic

## `market_data`

Responsibilities:

- normalize feed
- maintain live symbol state
- candle aggregation
- 5m candles
- 15m candles
- missing-data handling

## `universe`

Responsibilities:

- load base universe
- rank Top 30
- merge Watch List
- subscription management

## `indicators`

Pure calculation layer.

No Telegram/UI logic.

## `signals`

Responsibilities:

- Naveen Algo scoring
- direction
- finalized signal creation
- Entry/SL/T1/T2/T3
- duplicate prevention

## `notifications`

Responsibilities:

- Telegram formatting
- Telegram delivery
- retry logic
- notification audit

## `api`

FastAPI REST endpoints.

## `websocket`

Browser realtime event broadcaster.

## `storage`

SQLite models/repositories.

## `scheduler`

Daily startup/shutdown tasks.

---

# 21. Suggested REST API

Implement clean versioned endpoints under `/api/v1`.

Recommended endpoints:

## Health

- GET `/health`
- GET `/system/status`

## Scanner

- GET `/scanner/status`
- POST `/scanner/start`
- POST `/scanner/stop`
- GET `/scanner/universe`
- POST `/scanner/universe/refresh`
- GET `/scanner/live`

## Signals

- GET `/signals`
- GET `/signals/latest`
- GET `/signals/{id}`

## Watch List

- GET `/watchlist`
- POST `/watchlist`
- PATCH `/watchlist/{id}`
- DELETE `/watchlist/{id}`
- GET `/instruments/search`

## Settings

- GET `/settings`
- PATCH `/settings`

## Telegram

- GET `/telegram/status`
- POST `/telegram/config`
- POST `/telegram/test`

## Upstox

- GET `/upstox/status`
- GET `/upstox/login-url`
- GET `/upstox/callback`
- POST `/upstox/disconnect`

---

# 22. Browser WebSocket API

Expose a FastAPI WebSocket endpoint such as:

`/ws/live`

On connection, send an initial snapshot followed by incremental events.

Frontend must automatically reconnect if connection is lost.

Use heartbeat/ping logic.

Show connection state visibly:

- Live
- Reconnecting
- Offline

---

# 23. Realtime Candle Handling

The backend must maintain reliable candles per instrument.

For each instrument:

- build/update active 5-minute candle
- build/update active 15-minute candle
- finalize candle exactly once
- run signal engine after finalization

Use IST boundaries irrespective of computer timezone.

Example 5-minute boundaries:

- 09:15-09:20
- 09:20-09:25
- 09:25-09:30

The first signal-eligible candle should follow the configured 09:20 IST start rule.

On application startup during market hours:

- backfill enough historical/intraday data to initialize EMA200 and other indicators
- then transition to realtime feed

Do not wait for 200 new live candles before generating signals.

---

# 24. Startup Backfill

At backend startup:

1. Authenticate/check Upstox connection.
2. Refresh instrument mapping if needed.
3. Determine active scan universe.
4. Fetch sufficient historical candles for all required indicators.
5. Compute initial indicator state.
6. Fetch current-day intraday candles.
7. Merge historical + current intraday series safely.
8. Connect Market Data Feed V3.
9. Subscribe to final universe.
10. Start browser WebSocket broadcaster.
11. Start Telegram notification service.

EMA200 requires enough lookback. Fetch sufficient historical 5-minute data rather than approximating it from a short session.

---

# 25. Upstox WebSocket Reliability

Implement:

- authorized V3 URL acquisition
- Protobuf decoding
- automatic reconnect
- exponential backoff
- stale-feed detection
- resubscription after reconnect
- last-message timestamp
- graceful disconnect

If realtime feed is stale:

- mark scanner as degraded
- stop issuing new signals until data freshness is restored
- keep UI online
- show clear warning

Never create signals from stale data.

---

# 26. Universe Refresh Strategy

Recommended daily behavior:

### Before Market

Build preliminary Top 30 from recent historical liquidity/volatility.

### 09:20 IST

Re-rank using live opening activity.

### Optional Intraday Refresh

Refresh Top 30 at a configurable interval, recommended every 30 minutes.

Important rule:

- Watch List stocks remain subscribed.
- When Top 30 changes, safely subscribe new symbols and unsubscribe removed symbols.
- Do not interrupt existing dashboard state.

For V1, a simpler safe implementation is acceptable:

- Build Top 30 at 09:20
- Keep it fixed for the rest of the trading day
- Watch List remains dynamic

This simpler implementation is preferred for the first stable milestone.

---

# 27. Error Handling

No single integration failure should crash the entire application.

Separate health states:

- Backend
- Upstox REST
- Upstox WebSocket
- Telegram
- SQLite
- Frontend WebSocket

Use structured logging.

Do not log secrets.

Errors should include:

- timestamp
- module
- severity
- symbol when applicable
- user-friendly message
- technical detail in logs

---

# 28. Logging

Use rotating local logs.

Recommended location:

`logs/`

Files:

- app.log
- scanner.log
- upstox.log
- telegram.log
- errors.log

Retention should be configurable.

Do not allow logs to grow indefinitely.

---

# 29. Local Windows Development and Runtime

Project must run cleanly on Windows.

Expected development workflow:

Backend:

- Python virtual environment
- FastAPI on localhost

Frontend:

- Next.js dev server

Production-like local mode:

- Build Next.js production bundle
- Run backend and frontend through simple start scripts

Provide Windows PowerShell setup instructions in the project README.

Include scripts for:

- first-time setup
- backend start
- frontend start
- start all
- stop all

Optional later improvement:

- package backend as Windows service

Do not require Docker for V1.

---

# 30. Recommended Project Structure

Root repository should clearly separate frontend and backend.

Suggested structure:

- `backend/`
  - app/
  - api/
  - core/
  - upstox/
  - market_data/
  - indicators/
  - signals/
  - universe/
  - notifications/
  - storage/
  - websocket/
  - scheduler/
  - tests/
- `frontend/`
  - app/
  - components/
  - features/
  - hooks/
  - lib/
  - types/
- `data/`
- `logs/`
- `scripts/`
- `docs/`
- `.env.example`
- `README.md`

Do not place business logic directly inside API route files.

---

# 31. UI Component Requirements

Create reusable components:

- AppShell
- TopNavigation
- MarketStatusBadge
- ConnectionBadge
- MetricCard
- SignalCard
- SignalDirectionBadge
- ScoreBadge
- PriceLevelStack
- ScannerTable
- WatchListTable
- AddStockDialog
- InstrumentSearch
- EmptyState
- LoadingSkeleton
- ErrorState
- SettingsSection
- MaskedSecretInput
- TelegramTestPanel
- SystemHealthPanel

Signal cards should be especially polished because they are the core of the product.

Suggested signal-card visual hierarchy:

1. Symbol + BUY/SELL
2. Entry price
3. Stop / T1 / T2 / T3
4. Score
5. RVOL / Trend / VWAP / HTF
6. Timestamp/source

---

# 32. Dashboard Realtime Behavior

When a new signal is created:

- Immediately push it through browser WebSocket.
- Add it at top of Active Signals.
- Briefly animate/highlight the new card without flashy effects.
- Trigger Telegram asynchronously.
- Update daily counters.

Price values for active/recent signal cards may update in realtime, but original signal Entry/SL/Targets must remain unchanged for historical integrity.

Show both:

- Signal Entry
- Current LTP

---

# 33. Signal History Integrity

Never modify original signal values after creation.

Persist:

- original entry
- original stop
- original targets
- original score
- original indicator snapshot

Realtime LTP is transient and must not overwrite historical Entry.

---

# 34. Testing Requirements

## Unit Tests

Test:

- EMA calculations
- RSI calculations
- MACD calculations
- Supertrend calculations
- ATR
- RVOL
- breakout logic
- BUY score
- SELL score
- target calculations
- timezone/candle boundaries
- duplicate event prevention
- quantity calculation

## Integration Tests

Test:

- SQLite
- Telegram test message
- Upstox instrument resolution
- Upstox historical candle retrieval
- WebSocket decode pipeline
- reconnect behavior
- browser WebSocket

## Signal Regression Tests

Create fixed candle datasets and expected outputs.

The same dataset must always generate the same:

- BUY Score
- SELL Score
- Signal
- Entry
- Stop
- T1/T2/T3

## UI Tests

Test:

- Desktop
- Mobile
- empty states
- disconnected states
- large Watch List
- multiple simultaneous signals

---

# 35. Acceptance Criteria

V1 is complete only when all of the following work:

1. App runs locally on Windows.
2. User can authenticate with Upstox.
3. No Upstox password is stored by the app.
4. Application obtains realtime market data through Upstox V3.
5. Dynamic Top 30 is generated.
6. User can add/remove/enable/disable Watch List stocks.
7. Top 30 and Watch List are merged without duplicates.
8. 5-minute candles are generated correctly in IST.
9. 15-minute confirmed trend works.
10. Naveen Algo scores are calculated.
11. BUY and SELL signals are created.
12. Entry, SL, T1, T2 and T3 are generated.
13. ₹20,000 informational quantity is calculated.
14. Telegram can be configured from the web UI.
15. Telegram Test button works.
16. Every completed qualifying 5-minute candle can send one notification.
17. Same candle is never notified twice.
18. Dashboard updates in realtime without refresh.
19. Signal history persists after restart.
20. Watch List persists after restart.
21. App survives Telegram failures.
22. App reconnects to Upstox WebSocket after temporary disconnect.
23. Scanner stops generating signals when feed becomes stale.
24. No order-placement API is implemented.
25. UI is polished and mobile-friendly.

---

# 36. Implementation Phases for Cursor

## Phase 1 – Foundation

- Repository structure
- FastAPI backend
- Next.js frontend
- SQLite
- Settings model
- health endpoints
- light-mode design system

## Phase 2 – Upstox

- OAuth
- credentials management
- instrument search
- instrument master
- historical candles
- V3 realtime WebSocket
- Protobuf decode

## Phase 3 – Market Engine

- realtime state
- candle aggregation
- 5m and 15m
- backfill
- market-session logic

## Phase 4 – Strategy Engine

- technical indicators
- V3 Alpha scoring
- mode configuration
- Entry/SL/T1/T2/T3
- signal event model
- dedupe

## Phase 5 – Universe

- Top 30 ranking
- Watch List
- merge logic
- subscriptions

## Phase 6 – Telegram

- configuration UI
- Windows Credential Manager
- test message
- signal notifications
- retry/error states

## Phase 7 – Realtime UI

- FastAPI browser WebSocket
- Dashboard
- Scanner
- Watch List
- Signal History
- Settings
- System Status

## Phase 8 – Reliability

- reconnection
- stale feed logic
- structured logs
- tests
- Windows scripts
- documentation

Do not try to implement everything in one monolithic pass.

---

# 37. Cursor Coding Instructions

Cursor should follow these constraints while implementing:

- Build production-quality modules, not prototypes.
- Keep source files reasonably small and focused.
- Use strict TypeScript.
- Use typed Pydantic models.
- Avoid `any` in frontend code unless unavoidable.
- Keep indicator calculations deterministic.
- Keep Upstox-specific structures inside the Upstox adapter.
- Never expose secrets to the frontend after save.
- Never log tokens.
- Never use Windows system timezone for NSE calculations.
- Use UTC internally and Asia/Kolkata for market logic/display.
- Use completed candles for finalized signals.
- Do not introduce order-placement functionality.
- Do not introduce PostgreSQL or Redis.
- Do not require Docker.
- Maintain a clean README and `.env.example`.
- Add comments only where they add real value.
- Do not create placeholder UI; build polished final components.
- Every page must include loading, empty, error and disconnected states.
- Mobile responsiveness is mandatory.

---

# 38. Recommended V1 Defaults

- Market: NSE Equity
- Primary timeframe: 5m
- HTF: 15m
- Scanner eligibility: 09:20 IST
- Stop new signals: 14:45 IST
- Session end: 15:15 IST
- Dynamic universe: Top 30
- Strategy mode: Balanced
- Capital per trade: ₹20,000
- Telegram: Enabled after configuration
- UI: Light only
- Database: SQLite
- Local timezone assumption: Ignore machine timezone for market logic
- Browser realtime: WebSocket
- Default new-signal behavior: one Telegram notification per qualifying symbol/direction/completed 5m candle

---

# 39. Important Product Principle

The application should behave as a **market intelligence and signal-monitoring system**, not an execution bot.

Its primary job is to answer, in realtime:

- What stocks are being scanned?
- Which stock currently has the strongest BUY or SELL setup?
- Why did the signal fire?
- What is the Entry?
- Where is the Stop Loss?
- Where are T1/T2/T3?
- What quantity approximately fits ₹20,000?
- Was the Telegram notification successfully delivered?

The interface should make these answers understandable within a few seconds.

---

# 40. Current Upstox API Notes for Implementation

At the time this specification was prepared:

- Upstox authentication uses OAuth 2.0 authorization-code flow.
- Market Data Feed V3 is the current realtime WebSocket feed.
- V3 uses an authorized redirect URL and Protobuf messages.
- Upstox recommends using `instrument_key` for unique instrument identification.
- Instrument data is available in JSON format and through instrument search.
- OHLC Quotes V3 supports bulk snapshots and includes volume.
- LTP Quotes V3 supports bulk LTP snapshots and includes cumulative volume and previous close.
- Historical Candle Data V3 supports custom minute intervals, including 5-minute and 15-minute use cases.
- Intraday Candle Data V3 supports current-day minute intervals.

Cursor must verify the latest official Upstox documentation before locking endpoint paths, schemas, WebSocket subscription limits, or authentication behavior.

---

# 41. Final Deliverables Expected from Cursor

Cursor should produce:

1. Complete backend source.
2. Complete frontend source.
3. SQLite migrations/initialization.
4. Windows development setup.
5. Windows start/stop scripts.
6. `.env.example`.
7. Telegram setup documentation.
8. Upstox setup/authentication documentation.
9. User README.
10. Architecture README.
11. Test suite.
12. Clean responsive light UI.
13. Working realtime signal scanner.
14. Working Top 30 + Watch List scanner.
15. Working Telegram notifications.
16. Working realtime browser WebSocket.
17. Signal history and scanner status pages.

The project should be usable locally without TradingView after setup.
