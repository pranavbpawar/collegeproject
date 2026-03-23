# TBAPS Native Deployment Guide
**Ubuntu 22.04+ — No Docker — Native systemd Services**

---

## Folder Structure

```
/home/kali/Desktop/MACHINE/
├── .env.example                    ← copy to .env and fill secrets
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py           ← Pydantic BaseSettings (localhost defaults)
│   │   │   ├── database.py         ← async SQLAlchemy pool
│   │   │   ├── security.py         ← JWT with issuer/audience
│   │   │   └── celery_app.py       ← Celery with 3 queues + retry
│   │   └── main.py                 ← FastAPI (JSON logging, /health, /readiness)
│   ├── gunicorn.conf.py            ← Gunicorn + UvicornWorker config
│   ├── requirements.txt            ← production deps (includes gunicorn)
│   └── requirements-dev.txt        ← dev/test deps
├── nginx/
│   └── tbaps.conf                  ← Nginx HTTPS + reverse proxy
├── systemd/
│   ├── tbaps-api.service
│   ├── tbaps-worker.service
│   └── tbaps-capture.service
└── scripts/
    ├── install-services.sh         ← one-shot installer
    ├── build-frontend.sh
    └── ssl-setup.sh
```

---

## Step 1 — System Prerequisites

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential libssl-dev libffi-dev \
    python3.11 python3.11-venv python3.11-dev \
    nodejs npm nginx rsync
```

---

## Step 2 — PostgreSQL 15 + TimescaleDB

```bash
# Add PostgreSQL repo
sudo apt install -y curl ca-certificates gnupg
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /usr/share/keyrings/postgresql.gpg
echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

# Add TimescaleDB repo
curl -fsSL https://packagecloud.io/timescale/timescaledb/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/timescaledb.gpg
echo "deb [signed-by=/usr/share/keyrings/timescaledb.gpg] https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list

sudo apt update
sudo apt install -y postgresql-15 timescaledb-2-postgresql-15

# Enable TimescaleDB
sudo timescaledb-tune --quiet --yes

# Start PostgreSQL
sudo systemctl enable --now postgresql

# Create DB user and database
sudo -u postgres psql <<'SQL'
CREATE USER ztuser WITH PASSWORD 'CHANGE_ME_strong_password';
ALTER USER ztuser CREATEDB;
CREATE DATABASE zerotrust OWNER ztuser;
GRANT ALL PRIVILEGES ON DATABASE zerotrust TO ztuser;
\c zerotrust
CREATE EXTENSION IF NOT EXISTS timescaledb;
SQL
```

---

## Step 3 — Redis 7

```bash
sudo apt install -y redis-server

# Harden Redis (bind to localhost only)
sudo sed -i 's/^bind .*/bind 127.0.0.1 ::1/' /etc/redis/redis.conf
sudo sed -i 's/^# requirepass .*/requirepass CHANGE_ME_redis_pass/' /etc/redis/redis.conf

sudo systemctl enable --now redis-server
redis-cli ping   # Expected: PONG
```

---

## Step 4 — RabbitMQ

```bash
sudo apt install -y rabbitmq-server

sudo systemctl enable --now rabbitmq-server

# Create dedicated vhost and user
sudo rabbitmqctl add_vhost tbaps_vhost
sudo rabbitmqctl add_user tbaps CHANGE_ME_rabbitmq_pass
sudo rabbitmqctl set_permissions -p tbaps_vhost tbaps ".*" ".*" ".*"
sudo rabbitmqctl set_user_tags tbaps management

# Enable management UI (optional)
sudo rabbitmq-plugins enable rabbitmq_management
# UI: http://localhost:15672
```

---

## Step 5 — OpenVPN

```bash
sudo apt install -y openvpn easy-rsa

# Initialize PKI
make-cadir /etc/openvpn/easy-rsa
cd /etc/openvpn/easy-rsa
./easyrsa init-pki
./easyrsa build-ca nopass
./easyrsa gen-dh
./easyrsa build-server-full server nopass
openvpn --genkey secret /etc/openvpn/ta.key

# Copy server certs
cp pki/ca.crt pki/issued/server.crt pki/private/server.key pki/dh.pem /etc/openvpn/server/

# Copy your server config
sudo cp /home/kali/Desktop/MACHINE/openvpn-server.conf /etc/openvpn/server/server.conf

sudo systemctl enable --now openvpn-server@server
```

---

## Step 6 — Configure Environment

```bash
cd /home/kali/Desktop/MACHINE
cp .env.example .env
chmod 600 .env

# Edit .env — fill in ALL CHANGE_ME values:
nano .env

# Generate secrets:
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_hex(16))"
openssl rand -hex 32  # for SECRET_KEY
```

---

## Step 7 — Install All Services

```bash
cd /home/kali/Desktop/MACHINE
sudo bash scripts/install-services.sh
```

This script:
- Creates `tbaps` system user
- Copies files to `/opt/tbaps/`
- Creates Python venvs and installs dependencies
- Installs and enables all 3 systemd services
- Installs Nginx config

---

## Step 8 — Initialize Database

```bash
psql -U ztuser -d zerotrust -h localhost \
    -f /home/kali/Desktop/MACHINE/scripts/init_schema.sql

# If VPN schema exists:
psql -U ztuser -d zerotrust -h localhost \
    -f /home/kali/Desktop/MACHINE/vpn/database/schema.sql

# If traffic monitoring schema exists:
psql -U ztuser -d zerotrust -h localhost \
    -f /home/kali/Desktop/MACHINE/scripts/traffic_monitoring_schema.sql
```

---

## Step 9 — Build Frontend

```bash
bash /home/kali/Desktop/MACHINE/scripts/build-frontend.sh
```

---

## Step 10 — Configure Nginx

```bash
# Install config (done by install-services.sh, but verify):
sudo ln -sf /etc/nginx/sites-available/tbaps.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable --now nginx
```

---

## Step 11 — SSL Certificate

**Option A — Let's Encrypt (public domain):**
```bash
sudo bash /home/kali/Desktop/MACHINE/scripts/ssl-setup.sh tbaps.yourcompany.com admin@yourcompany.com
```

**Option B — Self-signed (internal/LAN):**
```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout /etc/ssl/private/tbaps.key \
    -out /etc/ssl/certs/tbaps.crt \
    -subj '/CN=tbaps.yourcompany.local'

# Update nginx/tbaps.conf ssl_certificate paths accordingly
```

---

## Step 12 — Start All Services

```bash
sudo systemctl start tbaps-api tbaps-worker tbaps-capture
sudo systemctl status tbaps-api tbaps-worker tbaps-capture
```

---

## Service Management

```bash
# Start / stop / restart
sudo systemctl start|stop|restart tbaps-api
sudo systemctl start|stop|restart tbaps-worker
sudo systemctl start|stop|restart tbaps-capture

# View live logs
sudo journalctl -u tbaps-api    -f
sudo journalctl -u tbaps-worker -f
sudo journalctl -u tbaps-capture -f

# View log files
tail -f /var/log/tbaps/access.log
tail -f /var/log/tbaps/error.log
tail -f /var/log/tbaps/celery-worker.log
```

---

## Important URLs

| Service | URL |
|---|---|
| Frontend | https://tbaps.yourcompany.local |
| API | https://tbaps.yourcompany.local/api/ |
| API Docs (dev only) | http://localhost:8000/api/docs |
| Health | http://localhost:8000/health |
| Readiness | http://localhost:8000/readiness |
| RabbitMQ UI | http://localhost:15672 |
| Flower (Celery) | http://localhost:5555 |
