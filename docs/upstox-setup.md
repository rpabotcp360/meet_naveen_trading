# Upstox Setup

## Analytics Token (recommended for this scanner)

This app uses **read-only market data only** — no order placement.

1. Log in to [Upstox Developer Console](https://upstox.com/developer/)
2. Open the **Analytics** tab
3. Copy your **Analytics Token** (long-lived, 1 year validity)
4. Open http://127.0.0.1:3000/settings
5. Paste token in **Upstox Analytics Token** → **Save Token**
6. Status should show **connected**

No Client Secret is required for Analytics tokens.

## OAuth (optional, for Algo Trading apps)

If you have an Algo app with Client ID + Client Secret, OAuth flow is still supported via `/api/v1/upstox/login-url`.

## 3. Verify Connection

- System Status page should show Upstox REST: `connected`
- After starting scanner, Upstox WebSocket should show `connected`

## Security Notes

- Access tokens stored in Windows Credential Manager (not SQLite)
- Client secret masked after save
- No Upstox password is ever collected by this app
- App is read-only — no order APIs implemented

## Troubleshooting

| Issue | Fix |
|-------|-----|
| OAuth redirect error | Ensure redirect URI matches exactly in Upstox console |
| Token expired | Click Connect Upstox again to re-authenticate |
| No market data | Verify market is open (NSE 09:15–15:30 IST) |
| WebSocket stale | Check internet; scanner auto-reconnects with backoff |
