# TBAPS Cloud Deployment Guide
**Pragyantri — Production Deployment Cheatsheet**
*Supabase · Render · Vercel — Free Tier*

---

## Prerequisites

| Service | URL | Free plan |
|---------|-----|-----------|
| Supabase | https://supabase.com | 500 MB DB, 2 projects |
| Render | https://render.com | 750 h/month, sleeps after 15 min |
| Vercel | https://vercel.com | Unlimited frontend deploys |

GitHub repo: `pranavbpawar/collegeproject`

---

## Phase 1 — Database (Supabase)

### 1.1 Create a project
1. Go to [supabase.com](https://supabase.com) → **New Project**
2. Name: `tbaps-prod`, Region: choose nearest, create a strong DB password
3. Wait ~2 min for initialization

### 1.2 Get the connection string
Project Settings → **Database** → **Connection String** → **URI** tab
→ Switch to **Transaction Pooler** (port **6543**)

Copy the full URL — it looks like:
```
postgresql://postgres.abcdefghijkl:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```
> Replace `[YOUR-PASSWORD]` with the password you set in step 1.

### 1.3 Run the migration
1. Supabase dashboard → **SQL Editor** → **New query**
2. Open the file below, copy its entire content, paste, and click **Run**:

**File:** `supabase_full_migration.sql` (in the project root)

Expected output: `Migration complete! All TBAPS tables created successfully.`

Verify in Table Editor that these tables exist:
`admin_users`, `employees`, `agent_machines`, `work_sessions`, `employee_auth`

---

## Phase 2 — Backend (Render)

### 2.1 Create the web service
1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect GitHub → select `pranavbpawar/collegeproject`
3. Render auto-detects `render.yaml` → click **Apply**
4. Service name auto-sets to **tbaps-backend**

> The free instance URL will be: `https://tbaps-backend.onrender.com`

### 2.2 Set environment variables
Go to the service → **Environment** → add these manually:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Supabase Transaction Pooler URL (from Phase 1.2) |
| `JWT_SECRET_KEY` | Run: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `SECRET_KEY` | Run: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ENCRYPTION_KEY` | Run: `python3 -c "import secrets; print(secrets.token_hex(16))"` |
| `CORS_ORIGINS` | `https://YOUR-APP.vercel.app` (update after Vercel deploy) |
| `FRONTEND_URL` | `https://YOUR-APP.vercel.app` |
| `EMAIL_FROM_ADDRESS` | `kbtremote.employee@gmail.com` |
| `SMTP_USERNAME` | `kbtremote.employee@gmail.com` |
| `SMTP_PASSWORD` | `jagk izzc ibyp kqzy` (Gmail App Password) |

> Leave `REDIS_URL` blank — it is optional (`REDIS_OPTIONAL=true` is set automatically).

### 2.3 Verify deployment
After ~3 min, open in browser:
```
https://tbaps-backend.onrender.com/health
```
Expected: `{"status":"ok","service":"tbaps-api","version":"1.0.0"}`

```
https://tbaps-backend.onrender.com/readiness
```
Expected: `{"status":"ready","checks":{"database":"ok","redis":"degraded:..."}}`

---

## Phase 3 — Frontend (Vercel)

### 3.1 Import the project
1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import `pranavbpawar/collegeproject` from GitHub
3. Set **Root Directory** → `frontend`
4. Framework: **Vite** (auto-detected)

### 3.2 Set environment variable
In Vercel project settings → **Environment Variables**:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://tbaps-backend.onrender.com/api/v1` |

### 3.3 Deploy
Click **Deploy** — Vercel will build and publish.

Note your URL (`https://tbaps-pragyantri.vercel.app` or similar).

**Go back to Render** and update `CORS_ORIGINS` and `FRONTEND_URL` with the real Vercel URL.

### 3.4 Verify routes
| URL | Expected |
|-----|----------|
| `https://YOUR-APP.vercel.app/` | Admin dashboard loads |
| `https://YOUR-APP.vercel.app/employee` | Employee portal loads |

---

## Phase 4 — KBT Agent

The agent already defaults to `https://tbaps-backend.onrender.com` (baked in `kbt_config.py`).

### One-command install (include in onboarding emails)

**Linux / macOS:**
```bash
curl -s https://tbaps-backend.onrender.com/kbt/install.sh | bash
```

**Windows (PowerShell, run as Admin):**
```powershell
iwr -useb https://tbaps-backend.onrender.com/kbt/install.ps1 | iex
```

### Rebuild KBT executable (optional — for distributing a binary)
```bash
cd agent
bash build_kbt.sh
```
PyInstaller output: `dist/kbt` (Linux) or `dist/kbt.exe` (Windows)

---

## Phase 5 — Post-Deploy Validation

Run end-to-end:

1. **Admin login** → `https://YOUR-APP.vercel.app` → log in
2. **Create employee** → fill form, submit → check email inbox
3. **KBT install** → run the install command from the email on any device
4. **Activate** → enter activation code from email
5. **Dashboard** → confirm KBT appears, telemetry arrives, trust score updates
6. **Employee portal** → `https://YOUR-APP.vercel.app/employee` → log in, start session

---

## Free-Tier Limitations

| Issue | Impact | Mitigation |
|-------|--------|-----------|
| Render sleeps after 15 min idle | ~30 s cold start on first request | KBT has retry logic; no data is lost |
| Supabase 500 MB DB limit | Enough for hundreds of employees | Archive old `agent_events` rows monthly |
| Render 750 h/month | ≈31 days — always-on for 1 service | One web service stays within limit |

---

## Security Checklist

- [ ] `.env` is in `.gitignore` (never committed)
- [ ] `JWT_SECRET_KEY` set as a fixed, secure value in Render (not auto-generated each restart)
- [ ] SMTP password stored only in Render env vars
- [ ] All production traffic is HTTPS (Render + Vercel enforce this)
- [ ] `PROMETHEUS_ENABLED=false` (metrics endpoint closed)
- [ ] Rotate `ENCRYPTION_KEY` and `JWT_SECRET_KEY` from the defaults if running for real users

---

## Quick Reference: Generate New Secrets

```bash
# JWT secret key
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# App secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Encryption key (exactly 32 hex chars)
python3 -c "import secrets; print(secrets.token_hex(16))"
```
