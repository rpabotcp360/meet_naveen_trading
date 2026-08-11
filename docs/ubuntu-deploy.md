# Deploy on Ubuntu Server

Production deploy for the NSE Intraday Signal Scanner on **Ubuntu 22.04 or 24.04**.

Stack: Python 3.12 + FastAPI (uvicorn), Node.js 20 + Next.js, nginx reverse proxy, Let's Encrypt SSL, systemd, SQLite.

**Public URL:** https://algo.meetnaveen.in

**Signal generation and monitoring only — no order placement.**

## Defaults used in this guide

| Item | Value |
|------|-------|
| Domain | `algo.meetnaveen.in` |
| App URL | `https://algo.meetnaveen.in` |
| App path | `/opt/meet_naveen_trading` |
| Run user | `root` |
| Backend | `127.0.0.1:8000` |
| Frontend | `127.0.0.1:3000` |
| Public ports | `80` / `443` via nginx |
| SSL | Let's Encrypt (Certbot) — **required** |

All commands below assume you are logged in as **root**.

---

## 1. Prerequisites

- Fresh Ubuntu 22.04 LTS or 24.04 LTS
- SSH access as `root`
- DNS **A record** (and optional AAAA) for `algo.meetnaveen.in` pointing to this server's public IP
- Ports **80** and **443** reachable from the internet (required for Let's Encrypt HTTP-01 challenge)

Verify DNS before SSL:

```bash
dig +short algo.meetnaveen.in A
# must return this server's public IP
```

Open firewall ports:

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
```

---

## 2. Install system packages

### Base tools

```bash
apt update
apt install -y git curl build-essential ca-certificates gnupg
```

### Python 3.12

**Ubuntu 24.04** (Python 3.12 is default):

```bash
apt install -y python3 python3-venv python3-pip python3-dev
python3 --version   # expect 3.12.x
```

**Ubuntu 22.04** (needs deadsnakes for 3.12):

```bash
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.12 python3.12-venv python3.12-dev
python3.12 --version
```

### Node.js 20

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
node --version   # v20.x
npm --version
```

### nginx + Certbot

```bash
apt install -y nginx certbot python3-certbot-nginx
systemctl enable --now nginx
```

### Secret storage (keyring)

The app stores Upstox / Telegram / login secrets via Python `keyring` (same idea as Windows Credential Manager). On a headless server install:

```bash
apt install -y dbus-x11 gnome-keyring libsecret-1-0
```

If keyring fails under systemd (no interactive login session), see [Troubleshooting: keyring](#troubleshooting-keyring).

---

## 3. Clone project

```bash
mkdir -p /opt/meet_naveen_trading
cd /opt
git clone <YOUR_REPO_URL> meet_naveen_trading
cd /opt/meet_naveen_trading
mkdir -p data logs
```

If the code is already on the machine, copy/extract it into `/opt/meet_naveen_trading`.

---

## 4. Backend setup

```bash
cd /opt/meet_naveen_trading/backend
python3.12 -m venv .venv   # on 24.04: python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

### Create `.env`

```bash
nano /opt/meet_naveen_trading/.env
```

Example:

```env
APP_ENV=production
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
LOG_LEVEL=INFO

# Optional: Analytics token can also be set in Settings UI
# UPSTOX_API_KEY=eyJ...

# Upstox OAuth redirect (if used)
UPSTOX_REDIRECT_URI=https://algo.meetnaveen.in/api/v1/upstox/callback
```

SQLite DB defaults to `/opt/meet_naveen_trading/data/scanner.db`. Logs go under `/opt/meet_naveen_trading/logs`.

### CORS (required)

Backend CORS currently allows only `http://127.0.0.1:3000` and `http://localhost:3000`.

Edit `backend/app/main.py` and set:

```python
allow_origins=[
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "https://algo.meetnaveen.in",
],
```

---

## 5. Frontend setup

Create production env (HTTPS / WSS — baked in at build time):

```bash
cat > /opt/meet_naveen_trading/frontend/.env.production << 'EOF'
NEXT_PUBLIC_API_URL=https://algo.meetnaveen.in
NEXT_PUBLIC_WS_URL=wss://algo.meetnaveen.in/ws/live
EOF
```

Install and build:

```bash
cd /opt/meet_naveen_trading/frontend
npm install
npm run build
```

After changing `NEXT_PUBLIC_*`, run `npm run build` again and restart the frontend service.

---

## 6. systemd services

### Backend unit

```bash
tee /etc/systemd/system/nse-scanner-backend.service > /dev/null << 'EOF'
[Unit]
Description=NSE Intraday Scanner Backend (FastAPI)
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/meet_naveen_trading/backend
Environment=PYTHONPATH=/opt/meet_naveen_trading/backend
EnvironmentFile=-/opt/meet_naveen_trading/.env
ExecStart=/opt/meet_naveen_trading/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### Frontend unit

```bash
tee /etc/systemd/system/nse-scanner-frontend.service > /dev/null << 'EOF'
[Unit]
Description=NSE Intraday Scanner Frontend (Next.js)
After=network.target nse-scanner-backend.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/meet_naveen_trading/frontend
Environment=NODE_ENV=production
Environment=PORT=3000
Environment=HOSTNAME=127.0.0.1
ExecStart=/usr/bin/npm run start
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable --now nse-scanner-backend nse-scanner-frontend
systemctl status nse-scanner-backend nse-scanner-frontend --no-pager
```

Local smoke checks on the server:

```bash
curl -s http://127.0.0.1:8000/health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
```

---

## 7. nginx reverse proxy (HTTP first)

Certbot needs a working HTTP vhost on port 80 before it can issue the certificate.

```bash
tee /etc/nginx/sites-available/nse-scanner > /dev/null << 'EOF'
server {
    listen 80;
    server_name algo.meetnaveen.in;

    client_max_body_size 20m;

    # FastAPI HTTP API + health + OpenAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # Browser live WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # Next.js dashboard (everything else)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

Enable the site:

```bash
ln -sf /etc/nginx/sites-available/nse-scanner /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

Confirm HTTP responds:

```bash
curl -sI http://algo.meetnaveen.in/health
```

---

## 8. SSL certificate (Let's Encrypt) — required

Issue and install a free SSL certificate for `algo.meetnaveen.in`. Certbot will modify the nginx site to listen on **443**, install the cert, and redirect HTTP → HTTPS.

```bash
certbot --nginx -d algo.meetnaveen.in
```

When prompted:

1. Enter an email for renewal notices
2. Agree to Terms of Service
3. Choose whether to share email with EFF (optional)
4. Select **redirect HTTP to HTTPS** (recommended)

Verify:

```bash
curl -sI https://algo.meetnaveen.in/health
certbot certificates
```

Expected: certificate for `algo.meetnaveen.in`, paths under `/etc/letsencrypt/live/algo.meetnaveen.in/`.

### Auto-renewal

Certbot installs a systemd timer. Test renewal:

```bash
certbot renew --dry-run
systemctl list-timers | grep certbot
```

Certificates renew automatically before expiry. After a renew that rewrites nginx, reload if needed:

```bash
systemctl reload nginx
```

### If Certbot fails

| Check | Command / action |
|-------|------------------|
| DNS | `dig +short algo.meetnaveen.in A` matches server IP |
| Port 80 open | `ufw status`; cloud security group allows 80/443 |
| nginx up | `systemctl status nginx`; `nginx -t` |
| Rate limits | Wait and retry; use `--dry-run` first if testing often |

---

## 9. Post-deploy checklist

1. Open https://algo.meetnaveen.in
2. Confirm browser shows a valid lock / certificate for `algo.meetnaveen.in`
3. Create / log in with app credentials
4. **Upstox**: Settings → paste Analytics Token → Save. See [upstox-setup.md](upstox-setup.md).
5. **Telegram**: Settings → Bot Token + Chat ID → Send Test. See [telegram-setup.md](telegram-setup.md).
6. **Scanner**: Settings → Start Scanner (during NSE market hours, Asia/Kolkata).
7. Confirm:
   - https://algo.meetnaveen.in/health returns `{"status":"ok",...}`
   - Dashboard live updates (WebSocket over `wss://`)
   - Status page shows integrations healthy

---

## 10. Operations

### Logs

```bash
journalctl -u nse-scanner-backend -f
journalctl -u nse-scanner-frontend -f
ls -la /opt/meet_naveen_trading/logs/
```

### Restart

```bash
systemctl restart nse-scanner-backend nse-scanner-frontend
```

### Update deploy

```bash
cd /opt/meet_naveen_trading
git pull
cd backend
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ../frontend
npm install
npm run build
systemctl restart nse-scanner-backend nse-scanner-frontend
```

### Stop

```bash
systemctl stop nse-scanner-backend nse-scanner-frontend
```

---

## Troubleshooting

### Backend will not start

```bash
systemctl status nse-scanner-backend -l
cd /opt/meet_naveen_trading/backend
source .venv/bin/activate
export PYTHONPATH=/opt/meet_naveen_trading/backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Confirm Python is **3.12+** (`requires-python >= 3.12`).

### CORS / API errors in browser

- Origins must include `https://algo.meetnaveen.in` in `backend/app/main.py`
- Frontend must use `NEXT_PUBLIC_API_URL=https://algo.meetnaveen.in` and `NEXT_PUBLIC_WS_URL=wss://algo.meetnaveen.in/ws/live`
- Rebuild frontend after env changes, then `systemctl restart nse-scanner-frontend`

### WebSocket drops

- Confirm nginx `/ws/` block has `Upgrade` / `Connection` headers and a long `proxy_read_timeout`
- Confirm `NEXT_PUBLIC_WS_URL` is `wss://algo.meetnaveen.in/ws/live`
- Confirm SSL is valid (mixed content / failed WSS if cert is missing)

### SSL / certificate issues

```bash
certbot certificates
nginx -t
systemctl status nginx
curl -vI https://algo.meetnaveen.in/ 2>&1 | head -40
```

Re-run issue if needed:

```bash
certbot --nginx -d algo.meetnaveen.in --force-renewal
```

### Troubleshooting: keyring

If Settings cannot save secrets under systemd:

1. Confirm packages: `dbus-x11 gnome-keyring libsecret-1-0`
2. Fallback: put `UPSTOX_API_KEY` in `/opt/meet_naveen_trading/.env` and restart backend
3. Ensure `/root` is writable

### nginx 502

```bash
systemctl status nse-scanner-backend nse-scanner-frontend --no-pager
curl -s http://127.0.0.1:8000/health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
nginx -t
```

---

## Quick reference

| Service | URL |
|---------|-----|
| Dashboard | https://algo.meetnaveen.in/ |
| Health | https://algo.meetnaveen.in/health |
| API docs | https://algo.meetnaveen.in/docs |
| Live WS | `wss://algo.meetnaveen.in/ws/live` |

| Unit | Name |
|------|------|
| Backend | `nse-scanner-backend.service` |
| Frontend | `nse-scanner-frontend.service` |
| Proxy / SSL | `nginx` + Certbot (`/etc/letsencrypt/live/algo.meetnaveen.in/`) |
