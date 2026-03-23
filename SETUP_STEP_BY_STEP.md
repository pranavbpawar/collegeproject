# TBAPS Complete Setup - Step by Step Guide

**Complete installation guide for TBAPS (Pragyantri) system with traffic monitoring**

---

## 📋 System Requirements

- **OS:** Linux (Ubuntu 20.04+, Debian 11+, Kali Linux)
- **RAM:** 8GB minimum (16GB recommended)
- **Disk:** 20GB free space
- **User:** sudo/root access required

---

## 🚀 Installation Steps

### STEP 1: Update System

```bash
sudo apt update && sudo apt upgrade -y
```

---

### STEP 2: Install PostgreSQL

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
psql --version
```

**Expected output:** `psql (PostgreSQL) 12.x` or higher

---

### STEP 3: Create Database User and Database

```bash
# Switch to postgres user and open psql
sudo -u postgres psql
```

**Inside PostgreSQL prompt, run these commands:**

```sql
-- Create user
CREATE USER ztuser WITH PASSWORD 'ztpass';

-- Give user permission to create databases
ALTER USER ztuser CREATEDB;

-- Create database
CREATE DATABASE zerotrust OWNER ztuser;

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE zerotrust TO ztuser;

-- Exit psql
\q
```

---

### STEP 4: Configure PostgreSQL Authentication

```bash
# Find and edit pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

**Find this line:**
```
local   all             all                                     peer
```

**Change to:**
```
local   all             all                                     md5
```

**Also ensure these lines exist (add if missing):**
```
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

**Restart PostgreSQL:**
```bash
sudo systemctl restart postgresql
```

---

### STEP 5: Test Database Connection

```bash
psql -U ztuser -d zerotrust -h localhost
```

**When prompted for password, enter:** `ztpass`

**You should see:**
```
zerotrust=>
```

**Type `\q` to exit**

✅ **If this works, database is configured correctly!**

---

### STEP 6: Install Redis

```bash
# Install Redis
sudo apt install -y redis-server

# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping
```

**Expected output:** `PONG`

---

### STEP 7: Install RabbitMQ

```bash
# Install RabbitMQ
sudo apt install -y rabbitmq-server

# Start and enable RabbitMQ
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Check status
sudo rabbitmqctl status
```

**RabbitMQ Management UI:** http://localhost:15672 (username: `guest`, password: `guest`)

---

### STEP 8: Install Python 3.11

```bash
# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Verify installation
python3.11 --version
```

**Expected output:** `Python 3.11.x`

---

### STEP 9: Install Node.js

```bash
# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version
npm --version
```

**Expected output:** `v18.x.x` and `9.x.x`

---

### STEP 10: Install Network Tools (for Traffic Monitoring)

```bash
# Install packet capture tools
sudo apt install -y tcpdump tshark libpcap-dev

# Install build tools
sudo apt install -y build-essential libssl-dev libffi-dev

# Verify tcpdump
tcpdump --version
```

---

### STEP 11: Install OpenVPN

```bash
# Install OpenVPN
sudo apt install -y openvpn easy-rsa

# Verify installation
openvpn --version
```

---

### STEP 12: Install Nginx (Web Server)

```bash
# Install Nginx
sudo apt install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Test
curl http://localhost
```

**You should see:** HTML content (Nginx default page)

---

### STEP 13: Navigate to Project Directory

```bash
cd /home/kali/Desktop/MACHINE
```

---

### STEP 14: Create Environment Configuration

```bash
# Create .env file
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://ztuser:ztpass@localhost:5432/zerotrust
POSTGRES_USER=ztuser
POSTGRES_PASSWORD=ztpass
POSTGRES_DB=zerotrust

# Application Settings
DEBUG=true
SECRET_KEY=change-this-secret-key-in-production-min-32-chars
JWT_SECRET_KEY=change-this-jwt-secret-key-in-production-min-32
ENCRYPTION_KEY=change-this-encryption-key-32ch

# VPN Configuration
VPN_SERVER_IP=192.168.1.100
VPN_INTERFACE=tun0

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672/
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Redis
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Traffic Monitoring
CAPTURE_FILTER=udp port 53 or tcp port 443
BATCH_SIZE=100
FLUSH_INTERVAL=10
AGGREGATION_INTERVAL=60

# Logging
LOG_LEVEL=INFO
EOF

# Set permissions
chmod 600 .env
```

---

### STEP 15: Initialize Database Schemas

```bash
# Run main schema
psql -U ztuser -d zerotrust -h localhost -f scripts/init_schema.sql
```

**Password:** `ztpass`

```bash
# Run VPN schema
psql -U ztuser -d zerotrust -h localhost -f vpn/database/schema.sql
```

**Password:** `ztpass`

```bash
# Run traffic monitoring schema
psql -U ztuser -d zerotrust -h localhost -f scripts/traffic_monitoring_schema.sql
```

**Password:** `ztpass`

**Expected output:** Multiple `CREATE TABLE`, `CREATE FUNCTION`, etc.

---

### STEP 16: Verify Database Tables

```bash
psql -U ztuser -d zerotrust -h localhost -c "\dt"
```

**Password:** `ztpass`

**You should see 20+ tables including:**
- `employees`
- `signal_events`
- `trust_scores`
- `vpn_connections`
- `traffic_dns_queries`
- `traffic_website_visits`
- `traffic_monitoring_consent`
- etc.

---

### STEP 17: Install Backend Dependencies

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt
```

**This will take 2-3 minutes**

**Verify installation:**
```bash
python -c "import fastapi; import sqlalchemy; import asyncpg; print('✓ Backend dependencies installed')"
```

**Expected output:** `✓ Backend dependencies installed`

---

### STEP 18: Install Frontend Dependencies

```bash
cd ../frontend

# Install Node packages
npm install
```

**This will take 3-5 minutes**

**Verify installation:**
```bash
npm list react
```

**Expected output:** `react@18.x.x`

---

### STEP 19: Build Frontend

```bash
# Build production bundle
npm run build
```

**This will create `dist/` folder with compiled files**

**Verify build:**
```bash
ls -lh dist/
```

**You should see:** `index.html`, `assets/`, etc.

---

### STEP 20: Install Traffic Monitor Dependencies

```bash
cd ../vpn/traffic-monitor

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Verify Scapy:**
```bash
python -c "from scapy.all import sniff; print('✓ Scapy installed')"
```

**Expected output:** `✓ Scapy installed`

---

### STEP 21: Create Systemd Service for Backend API

```bash
sudo tee /etc/systemd/system/tbaps-api.service > /dev/null << 'EOF'
[Unit]
Description=TBAPS Backend API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=kali
WorkingDirectory=/home/kali/Desktop/MACHINE/backend
Environment="PATH=/home/kali/Desktop/MACHINE/backend/venv/bin"
EnvironmentFile=/home/kali/Desktop/MACHINE/.env
ExecStart=/home/kali/Desktop/MACHINE/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

---

### STEP 22: Create Systemd Service for Packet Capture

```bash
sudo tee /etc/systemd/system/tbaps-packet-capture.service > /dev/null << 'EOF'
[Unit]
Description=TBAPS Traffic Monitor - Packet Capture
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/kali/Desktop/MACHINE/vpn/traffic-monitor
Environment="PATH=/home/kali/Desktop/MACHINE/vpn/traffic-monitor/venv/bin"
EnvironmentFile=/home/kali/Desktop/MACHINE/.env
ExecStart=/home/kali/Desktop/MACHINE/vpn/traffic-monitor/venv/bin/python packet_capture.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

---

### STEP 23: Create Systemd Service for Website Tracker

```bash
sudo tee /etc/systemd/system/tbaps-website-tracker.service > /dev/null << 'EOF'
[Unit]
Description=TBAPS Traffic Monitor - Website Tracker
After=network.target postgresql.service

[Service]
Type=simple
User=kali
WorkingDirectory=/home/kali/Desktop/MACHINE/vpn/traffic-monitor
Environment="PATH=/home/kali/Desktop/MACHINE/vpn/traffic-monitor/venv/bin"
EnvironmentFile=/home/kali/Desktop/MACHINE/.env
ExecStart=/home/kali/Desktop/MACHINE/vpn/traffic-monitor/venv/bin/python website_tracker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

---

### STEP 24: Reload Systemd

```bash
sudo systemctl daemon-reload
```

---

### STEP 25: Configure Nginx for Frontend

```bash
sudo tee /etc/nginx/sites-available/tbaps > /dev/null << 'EOF'
server {
    listen 80;
    server_name localhost;
    
    # Frontend
    location / {
        root /home/kali/Desktop/MACHINE/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # API Docs
    location /docs {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/tbaps /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t
```

**Expected output:** `syntax is ok` and `test is successful`

---

### STEP 26: Restart Nginx

```bash
sudo systemctl restart nginx
```

---

### STEP 27: Start Backend API Service

```bash
# Start service
sudo systemctl start tbaps-api

# Enable auto-start on boot
sudo systemctl enable tbaps-api

# Check status
sudo systemctl status tbaps-api
```

**Expected output:** `active (running)`

---

### STEP 28: Start Traffic Monitoring Services

```bash
# Start packet capture
sudo systemctl start tbaps-packet-capture
sudo systemctl enable tbaps-packet-capture

# Start website tracker
sudo systemctl start tbaps-website-tracker
sudo systemctl enable tbaps-website-tracker

# Check status
sudo systemctl status tbaps-packet-capture
sudo systemctl status tbaps-website-tracker
```

**Expected output:** Both services `active (running)`

---

### STEP 29: Create Log Directory

```bash
sudo mkdir -p /var/log/tbaps
sudo chown -R kali:kali /var/log/tbaps
```

---

### STEP 30: Test the System

#### Test 1: Check API Health

```bash
curl http://localhost:8000/health
```

**Expected output:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-02-11T14:30:00Z"
}
```

#### Test 2: Check Frontend

```bash
curl http://localhost/
```

**Should return:** HTML content

**Open browser:** http://localhost

#### Test 3: Check API Documentation

**Open browser:** http://localhost:8000/docs

**You should see:** Swagger API documentation

#### Test 4: Check Database Tables

```bash
psql -U ztuser -d zerotrust -h localhost -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```

**Password:** `ztpass`

**Expected output:** `20` or more tables

#### Test 5: Test Website Categorizer

```bash
cd /home/kali/Desktop/MACHINE/backend
source venv/bin/activate

python << 'EOF'
from app.services.website_categorizer import WebsiteCategorizer
import asyncio

async def test():
    cat = WebsiteCategorizer('postgresql://ztuser:ztpass@localhost:5432/zerotrust')
    await cat.connect()
    
    domains = ['github.com', 'facebook.com', 'stackoverflow.com']
    for domain in domains:
        category, score = cat.categorize(domain)
        print(f'{domain:25} -> {category:20} (score: {score})')
    
    await cat.disconnect()

asyncio.run(test())
EOF
```

**Expected output:**
```
github.com                -> productivity         (score: 100)
facebook.com              -> social_media         (score: 20)
stackoverflow.com         -> productivity         (score: 95)
```

---

## ✅ System Health Check

Create a health check script:

```bash
cat > /home/kali/Desktop/MACHINE/health-check.sh << 'EOF'
#!/bin/bash

echo "=== TBAPS System Health Check ==="
echo ""

# Check PostgreSQL
echo -n "PostgreSQL: "
systemctl is-active postgresql > /dev/null 2>&1 && echo "✓ Running" || echo "✗ Stopped"

# Check Redis
echo -n "Redis: "
systemctl is-active redis-server > /dev/null 2>&1 && echo "✓ Running" || echo "✗ Stopped"

# Check RabbitMQ
echo -n "RabbitMQ: "
systemctl is-active rabbitmq-server > /dev/null 2>&1 && echo "✓ Running" || echo "✗ Stopped"

# Check Nginx
echo -n "Nginx: "
systemctl is-active nginx > /dev/null 2>&1 && echo "✓ Running" || echo "✗ Stopped"

# Check TBAPS services
echo -n "Backend API: "
systemctl is-active tbaps-api > /dev/null 2>&1 && echo "✓ Running" || echo "✗ Stopped"

echo -n "Packet Capture: "
systemctl is-active tbaps-packet-capture > /dev/null 2>&1 && echo "✓ Running" || echo "✗ Stopped"

echo -n "Website Tracker: "
systemctl is-active tbaps-website-tracker > /dev/null 2>&1 && echo "✓ Running" || echo "✗ Stopped"

# Check API endpoint
echo -n "API Health: "
curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "✓ Responding" || echo "✗ Not responding"

echo ""
echo "=== All Systems Check Complete ==="
EOF

chmod +x /home/kali/Desktop/MACHINE/health-check.sh
```

**Run health check:**

```bash
./health-check.sh
```

**Expected output:**
```
=== TBAPS System Health Check ===

PostgreSQL: ✓ Running
Redis: ✓ Running
RabbitMQ: ✓ Running
Nginx: ✓ Running
Backend API: ✓ Running
Packet Capture: ✓ Running
Website Tracker: ✓ Running
API Health: ✓ Responding

=== All Systems Check Complete ===
```

---

## 🎯 Quick Reference

### Important URLs
- **Frontend:** http://localhost
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **RabbitMQ Management:** http://localhost:15672

### Database Credentials
- **Username:** `ztuser`
- **Password:** `ztpass`
- **Database:** `zerotrust`
- **Host:** `localhost`
- **Port:** `5432`

### Service Management Commands

```bash
# Start all services
sudo systemctl start tbaps-api tbaps-packet-capture tbaps-website-tracker

# Stop all services
sudo systemctl stop tbaps-api tbaps-packet-capture tbaps-website-tracker

# Restart all services
sudo systemctl restart tbaps-api tbaps-packet-capture tbaps-website-tracker

# Check status
sudo systemctl status tbaps-api
sudo systemctl status tbaps-packet-capture
sudo systemctl status tbaps-website-tracker

# View logs
sudo journalctl -u tbaps-api -f
sudo journalctl -u tbaps-packet-capture -f
sudo journalctl -u tbaps-website-tracker -f
```

### Database Access

```bash
# Connect to database
psql -U ztuser -d zerotrust -h localhost

# List tables
psql -U ztuser -d zerotrust -h localhost -c "\dt"

# Check traffic monitoring consent
psql -U ztuser -d zerotrust -h localhost -c "SELECT * FROM traffic_monitoring_consent;"
```

---

## 🔧 Troubleshooting

### Issue: PostgreSQL Authentication Failed

```bash
# Recreate user
sudo -u postgres psql -c "DROP USER IF EXISTS ztuser; CREATE USER ztuser WITH PASSWORD 'ztpass';"

# Recreate database
sudo -u postgres psql -c "DROP DATABASE IF EXISTS zerotrust; CREATE DATABASE zerotrust OWNER ztuser;"

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Issue: Service Won't Start

```bash
# Check service status
sudo systemctl status tbaps-api

# View logs
sudo journalctl -u tbaps-api -n 50

# Restart service
sudo systemctl restart tbaps-api
```

### Issue: Port Already in Use

```bash
# Check what's using port 8000
sudo netstat -tlnp | grep 8000

# Kill process if needed
sudo kill -9 <PID>
```

---

## 🎉 Setup Complete!

Your TBAPS system is now fully installed and running!

**Next Steps:**
1. Open http://localhost in your browser
2. Create your first employee account
3. Configure VPN certificates
4. Start monitoring employee activity

**For more information, see:**
- [LOCAL_SETUP_GUIDE.md](LOCAL_SETUP_GUIDE.md) - Detailed setup guide
- [DEPLOY_DOCKER_README.md](DEPLOY_DOCKER_README.md) - Docker deployment
- [README.md](README.md) - Project overview
