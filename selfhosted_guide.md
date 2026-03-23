# TBAPS — Self-Hosted Deployment Guide

> **Scenario**: Your Windows/Linux PC acts as the backend server. Employee machines on different networks connect over the internet via the NEF Agent.

---

## Architecture

```
[Employee PC]                [Your PC — Server]
 NEF Agent                   FastAPI :8000
     │                       PostgreSQL :5432
     │   Internet             Frontend :5173
     └───────────────────────────► ngrok / port-forward
```

---

## Table of Contents

1. [Install Local Dependencies](#1-install-local-dependencies)
2. [PostgreSQL Database Setup](#2-postgresql-database-setup)
3. [Backend Setup](#3-backend-setup)
4. [Frontend Setup (Optional)](#4-frontend-setup-optional)
5. [Firewall Configuration](#5-firewall-configuration)
6. [Expose to Internet](#6-expose-to-internet)
7. [Configure NEF Agent](#7-configure-nef-agent)
8. [Full System Test](#8-full-system-test)
9. [Keep Server Running (Auto-Start)](#9-keep-server-running-auto-start)
10. [Security Checklist](#10-security-checklist)

---

## 1. Install Local Dependencies

### Windows

```powershell
# 1. Python 3.11
winget install Python.Python.3.11

# 2. Node.js 18
winget install OpenJS.NodeJS.LTS

# 3. Git
winget install Git.Git

# 4. PostgreSQL 16
winget install PostgreSQL.PostgreSQL.16

# Verify
python --version   # Python 3.11.x
node --version     # v18.x
psql --version     # psql 16.x
```

### Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
    nodejs npm git postgresql postgresql-contrib curl
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

## 2. PostgreSQL Database Setup

### Windows — using pgAdmin or psql

Open **SQL Shell (psql)** from Start Menu:

```sql
-- Create database and user
CREATE DATABASE tbaps_db;
CREATE USER tbaps_user WITH PASSWORD 'YourStrongPassword123!';
GRANT ALL PRIVILEGES ON DATABASE tbaps_db TO tbaps_user;
\q
```

### Linux

```bash
sudo -u postgres psql << 'EOF'
CREATE DATABASE tbaps_db;
CREATE USER tbaps_user WITH PASSWORD 'YourStrongPassword123!';
GRANT ALL PRIVILEGES ON DATABASE tbaps_db TO tbaps_user;
EOF
```

### Allow Remote Connections (if needed)

Edit PostgreSQL config:

```bash
# Linux
sudo nano /etc/postgresql/16/main/postgresql.conf
# Change:  listen_addresses = 'localhost'
# To:      listen_addresses = 'localhost'   ← keep localhost only (backend is same machine)

# No need to expose port 5432 to internet — backend queries DB locally
```

---

## 3. Backend Setup

### Clone & Configure

```bash
git clone https://github.com/yourorg/MACHINE.git
cd MACHINE/backend
```

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux:**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Create [.env](file:///r:/MACHINE/MACHINE/.env) File

```bash
cp ../.env.example .env
```

Edit [.env](file:///r:/MACHINE/MACHINE/.env) with your values:

```env
# ── Application ──────────────────────────────────────────────────────────────
APP_ENV=production
DEBUG=false

# ── Database (local PostgreSQL) ───────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://tbaps_user:YourStrongPassword123!@localhost:5432/tbaps_db

# ── Security (generate these!) ────────────────────────────────────────────────
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
JWT_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
ENCRYPTION_KEY=<run: python -c "import secrets; print(secrets.token_hex(16))">

# ── CORS (update after getting public URL in Step 6) ─────────────────────────
CORS_ORIGINS=*
FRONTEND_URL=http://localhost:5173

# ── Server URL (update after Step 6 with your public URL) ────────────────────
SERVER_URL=http://localhost:8000

# ── Email (optional — for agent distribution) ─────────────────────────────────
EMAIL_PROVIDER=smtp
EMAIL_FROM_ADDRESS=you@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true
```

Generate secrets:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Run 3 times — for SECRET_KEY, JWT_SECRET_KEY, ENCRYPTION_KEY
```

### Initialize Database Tables

```bash
python -c "
import asyncio
from app.core.database import Base, engine
from app.models import *
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✅ All tables created')
asyncio.run(init())
"
```

### Start Backend

> **Important**: Bind to `0.0.0.0` so it accepts connections from the internet (via ngrok/port-forward), NOT just localhost.

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify:
```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

API Docs: `http://localhost:8000/docs`

---

## 4. Frontend Setup (Optional)

### Option A — Run Locally

```bash
cd MACHINE/frontend
npm install
npm run dev
# → http://localhost:5173
```

### Option B — Deploy on Vercel (Recommended)

See the [deployment_guide.md](file:///C:/Users/prana/.gemini/antigravity/brain/50171549-ef87-4ebe-9c69-6acf05dc752d/deployment_guide.md) — Section 4. Point [vercel.json](file:///r:/MACHINE/MACHINE/frontend/vercel.json) rewrites to your ngrok/Cloudflare URL in Step 6.

---

## 5. Firewall Configuration

### Windows Defender Firewall

```powershell
# Allow port 8000 inbound (Run as Administrator)
New-NetFirewallRule `
    -DisplayName "TBAPS Backend" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8000 `
    -Action Allow

# Verify
Get-NetFirewallRule -DisplayName "TBAPS Backend"
```

Or via GUI:
1. **Windows Firewall** → **Advanced Settings**
2. **Inbound Rules** → **New Rule**
3. **Port** → TCP → **8000** → Allow → Name: `TBAPS Backend`

### Linux (ufw)

```bash
sudo ufw allow 8000/tcp
sudo ufw status

# Also make sure ufw is enabled
sudo ufw enable
```

> ⛔ **Do NOT open port 5432** (PostgreSQL). It must stay local-only.

---

## 6. Expose to Internet

Choose **one** of the three methods below.

---

### Method A — ngrok (Easiest · Recommended for Testing)

#### Install ngrok

**Windows:**
```powershell
winget install ngrok.ngrok
# OR download from https://ngrok.com/download
```

**Linux:**
```bash
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

#### Sign up and Configure

1. Go to [ngrok.com](https://ngrok.com) → Sign up (free)
2. Copy your **Auth Token** from dashboard
3. Set it up:
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

#### Start Tunnel

```bash
ngrok http 8000
```

Output:
```
Forwarding  https://a1b2c3d4e5f6.ngrok-free.app -> http://localhost:8000
```

**Your public URL**: `https://a1b2c3d4e5f6.ngrok-free.app`

> ⚠️ Free ngrok URLs change every restart. Use a **paid static domain** (`$8/mo`) for stability, or use Cloudflare Tunnel (Method C — free and permanent).

#### Update .env with ngrok URL

```env
SERVER_URL=https://a1b2c3d4e5f6.ngrok-free.app
CORS_ORIGINS=https://a1b2c3d4e5f6.ngrok-free.app,http://localhost:5173
```

Restart backend after changing [.env](file:///r:/MACHINE/MACHINE/.env).

---

### Method B — Port Forwarding (No third-party service)

#### Step 1 — Find Your Local PC IP

**Windows:**
```powershell
ipconfig | findstr "IPv4"
# Example: 192.168.1.100
```

**Linux:**
```bash
hostname -I | awk '{print $1}'
# Example: 192.168.1.100
```

#### Step 2 — Log Into Your Router

Open browser → go to `192.168.1.1` (or your router's gateway).

Common login pages:
- TP-Link: `192.168.0.1`
- Jio: `192.168.29.1`
- Airtel: `192.168.1.1`

#### Step 3 — Set Up Port Forwarding

Navigate to: **Advanced** → **NAT** → **Port Forwarding** (varies by router)

| Field | Value |
|---|---|
| **Service Name** | `TBAPS` |
| **External Port** | `8000` |
| **Internal IP** | `192.168.1.100` (your PC's local IP) |
| **Internal Port** | `8000` |
| **Protocol** | `TCP` |

Save and apply.

#### Step 4 — Get Your Public IP

```bash
curl https://api.ipify.org
# Example: 203.0.113.42
```

**Your public URL**: `http://203.0.113.42:8000`

> ⚠️ Most ISPs assign dynamic IPs that change. Use a **DDNS service** like [noip.com](https://noip.com) to get a fixed hostname.

#### Optional — Free Dynamic DNS (DDNS)

1. Sign up at [noip.com](https://www.noip.com) (free)
2. Create a hostname: `yourtbaps.ddns.net`
3. Install the NoIP DUC client on your PC — it auto-updates your IP
4. **Your URL**: `http://yourtbaps.ddns.net:8000`

---

### Method C — Cloudflare Tunnel (Best · Free · Permanent URL)

> ✅ **Most stable option** — permanent URL, HTTPS, no port forwarding, no router config needed.

#### Step 1 — Install cloudflared

**Windows:**
```powershell
winget install Cloudflare.cloudflared
```

**Linux:**
```bash
# The project already includes cloudflared.deb in the root:
sudo dpkg -i cloudflared.deb
# OR download fresh:
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

#### Step 2 — Login to Cloudflare

```bash
cloudflared tunnel login
# Opens browser — log in with your Cloudflare account (free)
```

#### Step 3 — Create a Tunnel

```bash
cloudflared tunnel create tbaps-tunnel
# → Outputs: Tunnel ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

#### Step 4 — Configure the Tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: tbaps-tunnel
credentials-file: /root/.cloudflared/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json

ingress:
  - hostname: tbaps.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

> Replace `tbaps.yourdomain.com` with a subdomain on your domain (you must own a domain in Cloudflare DNS).

> **No custom domain?** Use Quick Tunnel instead (see below).

#### Step 5 — Start the Tunnel

```bash
cloudflared tunnel run tbaps-tunnel
```

**Your permanent URL**: `https://tbaps.yourdomain.com`

#### Alternative — Quick Tunnel (No account, temporary)

```bash
cloudflared tunnel --url http://localhost:8000
# → https://some-random-name.trycloudflare.com
```

---

### Comparison Table

| Method | Cost | Stability | HTTPS | Setup Difficulty |
|---|---|---|---|---|
| **ngrok** | Free (URL changes) | ⚠️ URL changes on restart | ✅ | Easy |
| **Port Forward** | Free | ⚠️ IP may change | ❌ (use DDNS) | Medium |
| **Cloudflare Tunnel** | Free | ✅ Permanent | ✅ | Medium |

---

## 7. Configure NEF Agent

Once you have your public URL (from Step 6), configure the NEF Agent on each employee machine.

### Edit Agent Config

In the agent source, edit [agent/config.py](file:///r:/MACHINE/MACHINE/agent/config.py):

```python
SERVER_URL = "https://a1b2c3d4e5f6.ngrok-free.app"
# OR
SERVER_URL = "https://tbaps.yourdomain.com"
# OR
SERVER_URL = "http://203.0.113.42:8000"  # port forward
```

### Set via Environment Variable (preferred)

```bash
# Linux employee machine
export NEF_SERVER_URL="https://your-public-url"
./nef --server "$NEF_SERVER_URL"

# Windows employee machine
$env:NEF_SERVER_URL = "https://your-public-url"
.\nef-agent.exe --server $env:NEF_SERVER_URL
```

### Verify Agent Can Reach Server

On employee machine:
```bash
curl https://your-public-url/health
# Should return: {"status": "ok"}
```

### Update .env on Server

```env
SERVER_URL=https://your-public-url
CORS_ORIGINS=https://your-public-url,http://localhost:5173
```

Restart backend:
```bash
# Ctrl+C the running uvicorn, then:
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 8. Full System Test

Follow these steps end-to-end to verify everything works.

### Step 1 — Start Backend

```bash
cd MACHINE/backend
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 2 — Expose via ngrok (or Cloudflare)

```bash
# New terminal
ngrok http 8000
# Copy the https URL shown
```

### Step 3 — Seed Admin

```bash
curl -X POST https://YOUR-URL/api/v1/admin/users/seed-admin
```

### Step 4 — Login to Dashboard

- Local: open `http://localhost:5173`
- Vercel: open `https://your-app.vercel.app`
- Login: `admin / Admin@1234`

### Step 5 — Install NEF Agent on Employee PC

**Linux (employee machine):**
```bash
scp dist/nef-agent_1.0_amd64.deb user@employee-ip:~/
ssh user@employee-ip "sudo dpkg -i nef-agent_1.0_amd64.deb"
# Agent starts automatically via systemd
```

**Windows (employee machine):**
```powershell
.\nef-agent.exe --server https://YOUR-URL
```

### Step 6 — Generate Activity on Employee Machine

- Open a browser, visit a few sites
- Open apps
- Wait 30–60 seconds

### Step 7 — Verify Data in Dashboard

1. Check dashboard → employee should appear
2. Trust score should update
3. Activity events visible

### Step 8 — Verify API Directly

```bash
# Check agent connected
curl -H "Authorization: Bearer $TOKEN" \
  https://YOUR-URL/api/v1/agent/machines

# Check recent events
curl -H "Authorization: Bearer $TOKEN" \
  "https://YOUR-URL/api/v1/agent/events?limit=5"
```

---

## 9. Keep Server Running (Auto-Start)

You want the backend to survive PC restarts and run in the background.

### Windows — Run as Background Service

#### Option A — NSSM (Non-Sucking Service Manager)

```powershell
# Download NSSM
winget install NSSM.NSSM

# Install backend as Windows service
nssm install TBAPSBackend "R:\MACHINE\MACHINE\backend\.venv\Scripts\uvicorn.exe"
nssm set TBAPSBackend AppParameters "app.main:app --host 0.0.0.0 --port 8000"
nssm set TBAPSBackend AppDirectory "R:\MACHINE\MACHINE\backend"
nssm set TBAPSBackend Start SERVICE_AUTO_START
nssm start TBAPSBackend

# Verify
nssm status TBAPSBackend
```

#### Option B — Task Scheduler

1. Open **Task Scheduler**
2. **Create Basic Task** → Name: `TBAPS Backend`
3. Trigger: **When computer starts**
4. Action: **Start a program**
   - Program: `R:\MACHINE\MACHINE\backend\.venv\Scripts\uvicorn.exe`
   - Arguments: `app.main:app --host 0.0.0.0 --port 8000`
   - Start in: `R:\MACHINE\MACHINE\backend`
5. Check **Run whether user is logged on or not**

### Linux — systemd Service

The project includes a pre-made systemd service at [systemd/tbaps-backend.service](file:///r:/MACHINE/MACHINE/systemd/tbaps-backend.service):

```bash
# Copy to systemd
sudo cp systemd/tbaps-backend.service /etc/systemd/system/

# Edit paths as needed
sudo nano /etc/systemd/system/tbaps-backend.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable tbaps-backend
sudo systemctl start tbaps-backend

# Check status
sudo systemctl status tbaps-backend
journalctl -u tbaps-backend -f  # live logs
```

### Auto-start ngrok (Linux)

Create `/etc/systemd/system/ngrok-tbaps.service`:

```ini
[Unit]
Description=ngrok tunnel for TBAPS
After=network.target tbaps-backend.service

[Service]
ExecStart=/usr/local/bin/ngrok http 8000 --log=stdout
Restart=always
RestartSec=10
User=youruser

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ngrok-tbaps
sudo systemctl start ngrok-tbaps
```

> ℹ️ For auto-start on Windows, configure ngrok with a static domain (paid) and use Task Scheduler similarly.

---

## 10. Security Checklist

| Item | Status | Action |
|---|---|---|
| Port 5432 (DB) NOT exposed | Must do | Never open PostgreSQL to internet |
| Port 8000 open | Required | Allow in firewall only |
| HTTPS enabled | Must do | ngrok/Cloudflare provide this automatically |
| Strong passwords | Must do | DB password + JWT secrets |
| Change default admin password | Must do | `POST /auth/change-password` after first login |
| CORS restricted to known origins | Should do | Set `CORS_ORIGINS` to specific URLs, not `*` |
| `DEBUG=false` in production | Must do | Never run debug mode with real data |
| JWT expiry is reasonable | Done | 12 hours by default |
| Rate limiting on send-agent | Done | `AGENT_SEND_RATE_LIMIT=10/minute` |
| Agent uses HTTPS (not HTTP) | Must do | Use ngrok/Cloudflare for HTTPS |

### Quick Security Fix — Restrict CORS

After testing, change [.env](file:///r:/MACHINE/MACHINE/.env):

```env
# Replace * with your actual frontend URL
CORS_ORIGINS=https://your-app.vercel.app
```

---

## Quick Reference

### Start Everything Locally

```bash
# Terminal 1 — Backend
cd R:\MACHINE\MACHINE\backend
.venv\Scripts\Activate.ps1              # or: source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Internet tunnel
ngrok http 8000

# Terminal 3 — Frontend (optional)
cd R:\MACHINE\MACHINE\frontend
npm run dev
```

### Key URLs

| Service | URL |
|---|---|
| Backend (local) | `http://localhost:8000` |
| API Docs | `http://localhost:8000/docs` |
| Public API (ngrok) | `https://xxxx.ngrok-free.app` |
| Frontend (local) | `http://localhost:5173` |
| Dashboard (Vercel) | `https://your-app.vercel.app` |

### Agent Server URL Priority

```
1. Cloudflare Tunnel  → https://tbaps.yourdomain.com   ← BEST (permanent, free)
2. ngrok paid static  → https://tbaps.ngrok.app         ← Good  (stable, $8/mo)
3. Port Forward+DDNS  → http://yourtbaps.ddns.net:8000  ← OK    (free, no HTTPS)
4. ngrok free         → https://xxxx.ngrok-free.app     ← Only for testing
```
