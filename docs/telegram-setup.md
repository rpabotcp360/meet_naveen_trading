# Telegram Setup

## Create a Bot

1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Choose a bot name and username (must end in `bot`)
5. Copy the **Bot Token**

## Get Chat ID

1. Open a chat with your new bot
2. Send any message (e.g. `Hello`)
3. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Find `"chat":{"id":123456789}` in the JSON response
5. Copy the Chat ID number

## Configure in App

1. Open http://127.0.0.1:3000/settings
2. Scroll to **Telegram** section
3. Paste Bot Token and Chat ID
4. Click **Save**
5. Click **Send Test** — you should receive a test message

## Notification Format

Signals include: symbol, entry, qty for ₹20k, SL, T1/T2/T3, score, mode, RVOL, trend, VWAP, HTF, and source.

## Notes

- Bot token stored in Windows Credential Manager
- Telegram failures never stop the scanner
- Failed sends are retried with exponential backoff
- Delivery logged in `notification_log` table
