# TBAPS Local Setup Guide - Native Installation (No Docker)

This guide walks you through setting up the complete TBAPS (Pragyantri) system locally using native system services instead of Docker.

---

## 📋 Prerequisites

### System Requirements
- **OS:** Linux (Ubuntu 20.04+, Debian 11+, or Kali Linux)
- **RAM:** Minimum 8GB (16GB recommended)
- **Disk:** 20GB free space
- **CPU:** 4+ cores recommended

---

## 🚀 Step-by-Step Installation

### Step 1: Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install Redis
sudo apt install -y redis-server

# Install RabbitMQ
sudo apt install -y rabbitmq-server

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install network tools (for traffic monitoring)
sudo apt install -y tcpdump tshark libpcap-dev

# Install build tools
sudo apt install -y build-essential libssl-dev libffi-dev

# Install OpenVPN
sudo apt install -y openvpn easy-rsa

# Install Git
sudo apt install -y git
```

### Step 2: Verify Installations

```bash
psql --version          # PostgreSQL 12+
redis-cli --version     # Redis 6+
python3.11 --version    # Python 3.11+
node --version          # Node v18+
npm --version           # npm 9+
openvpn --version       # OpenVPN 2.5+
```

---

### Step 3: Configure PostgreSQL

```bash
# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database user and database
sudo -u postgres psql << EOF
CREATE USER ztuser WITH PASSWORD 'ztpass';
CREATE DATABASE zerotrust OWNER ztuser;
GRANT ALL PRIVILEGES ON DATABASE zerotrust TO ztuser;
\q
EOF

# Verify connection
psql -U ztuser -d zerotrust -h localhost -c "SELECT version();"
```

**If prompted for password, enter:** `ztpass`

---

### Step 4: Configure Redis

```bash
# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify Redis is running
redis-cli ping
```

**Expected output:** `PONG`

---

### Step 5: Configure RabbitMQ

```bash
# Start RabbitMQ service
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Create admin user (optional)
sudo rabbitmqctl add_user admin admin123
sudo rabbitmqctl set_user_tags admin administrator
sudo rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"

# Verify RabbitMQ is running
sudo rabbitmqctl status
```

**RabbitMQ Management UI:** http://localhost:15672 (guest/guest or admin/admin123)

---

### Step 6: Navigate to Project Directory

```bash
cd /home/kali/Desktop/MACHINE
```

---

### Step 7: Configure Environment Variables

```bash
# Create .env file
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://ztuser:ztpass@localhost:5432/zerotrust
POSTGRES_USER=ztuser
POSTGRES_PASSWORD=ztpass
POSTGRES_DB=zerotrust

# Database Pool Settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

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
POLL_INTERVAL=30

# Logging
LOG_LEVEL=INFO
EOF

# Set proper permissions
chmod 600 .env
```

---

### Step 8: Initialize Database Schemas

```bash
# Run main schema
psql -U ztuser -d zerotrust -h localhost -f scripts/init_schema.sql

# Run VPN schema
psql -U ztuser -d zerotrust -h localhost -f vpn/database/schema.sql

# Run traffic monitoring schema
psql -U ztuser -d zerotrust -h localhost -f scripts/traffic_monitoring_schema.sql
```

**Expected output:**
```
CREATE EXTENSION
CREATE TYPE
CREATE TABLE
...
✓ All traffic monitoring tables created successfully
```

**Verify tables:**

```bash
psql -U ztuser -d zerotrust -h localhost -c "\dt" | grep -E "traffic_|vpn_|employees|trust_scores"
```

You should see 20+ tables.

---

### Step 9: Install Backend Dependencies

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

# Verify installation
python -c "import fastapi; import sqlalchemy; import asyncpg; print('✓ Backend dependencies installed')"
```

---

### Step 10: Install Frontend Dependencies

```bash
cd ../frontend

# Install Node packages
npm install

# Verify installation
npm list react
```

---

### Step 11: Build Frontend

```bash
# Build production bundle
npm run build

# The build will be in dist/ folder
ls -lh dist/
```

---

### Step 12: Setup VPN Infrastructure

```bash
cd ../vpn

# Initialize VPN CA (Certificate Authority)
sudo ./scripts/init-vpn-ca.sh

# Configure OpenVPN server
sudo cp config/server.conf /etc/openvpn/server/

# Start OpenVPN service
sudo systemctl start openvpn-server@server
sudo systemctl enable openvpn-server@server

# Verify VPN is running
sudo systemctl status openvpn-server@server
```

**Check VPN interface:**

```bash
ip addr show tun0
```

---

### Step 13: Install Traffic Monitor Dependencies

```bash
cd traffic-monitor

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify Scapy installation
python -c "from scapy.all import sniff; print('✓ Scapy installed')"
```

---

### Step 14: Create Systemd Services

#### Backend API Service

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

#### Traffic Monitor Packet Capture Service

```bash
sudo tee /etc/systemd/system/tbaps-packet-capture.service > /dev/null << 'EOF'
[Unit]
Description=TBAPS Traffic Monitor - Packet Capture
After=network.target postgresql.service openvpn-server@server.service

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

#### Website Tracker Service

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

#### VPN Logger Service

```bash
sudo tee /etc/systemd/system/tbaps-vpn-logger.service > /dev/null << 'EOF'
[Unit]
Description=TBAPS VPN Connection Logger
After=network.target postgresql.service openvpn-server@server.service

[Service]
Type=simple
User=kali
WorkingDirectory=/home/kali/Desktop/MACHINE/vpn/logger
Environment="PATH=/home/kali/Desktop/MACHINE/backend/venv/bin"
EnvironmentFile=/home/kali/Desktop/MACHINE/.env
ExecStart=/home/kali/Desktop/MACHINE/backend/venv/bin/python vpn_logger.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

#### Reload systemd

```bash
sudo systemctl daemon-reload
```

---

### Step 15: Start All Services

```bash
# Start Backend API
sudo systemctl start tbaps-api
sudo systemctl enable tbaps-api

# Start Traffic Monitor services
sudo systemctl start tbaps-packet-capture
sudo systemctl enable tbaps-packet-capture

sudo systemctl start tbaps-website-tracker
sudo systemctl enable tbaps-website-tracker

# Start VPN Logger
sudo systemctl start tbaps-vpn-logger
sudo systemctl enable tbaps-vpn-logger

# Check status of all services
sudo systemctl status tbaps-api
sudo systemctl status tbaps-packet-capture
sudo systemctl status tbaps-website-tracker
sudo systemctl status tbaps-vpn-logger
```

---

### Step 16: Setup Frontend Web Server (Nginx)

```bash
# Install Nginx
sudo apt install -y nginx

# Create Nginx configuration
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

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

### Step 17: Create Log Directories

```bash
# Create log directories
sudo mkdir -p /var/log/tbaps
sudo chown -R kali:kali /var/log/tbaps

# Create symlinks for easy access
ln -sf /var/log/tbaps ~/tbaps-logs
```

---

### Step 18: Test the System

#### Test 1: Check Services

```bash
# Check all TBAPS services
systemctl list-units | grep tbaps
```

**Expected output:**
```
tbaps-api.service                loaded active running
tbaps-packet-capture.service     loaded active running
tbaps-website-tracker.service    loaded active running
tbaps-vpn-logger.service         loaded active running
```

#### Test 2: Check API Health

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-02-11T14:30:00Z"
}
```

#### Test 3: Check Frontend

```bash
curl http://localhost/
```

Should return HTML content.

**Open browser:** http://localhost

#### Test 4: Check Database

```bash
psql -U ztuser -d zerotrust -h localhost -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```

**Expected:** 20+ tables

#### Test 5: Test Website Categorizer

```bash
cd /home/kali/Desktop/MACHINE/backend
source venv/bin/activate

python -c "
from app.services.website_categorizer import WebsiteCategorizer
import asyncio

async def test():
    cat = WebsiteCategorizer('postgresql://ztuser:ztpass@localhost:5432/zerotrust')
    await cat.connect()
    
    domains = ['github.com', 'facebook.com', 'stackoverflow.com', 'youtube.com']
    for domain in domains:
        category, score = cat.categorize(domain)
        print(f'{domain:25} -> {category:20} (score: {score})')
    
    await cat.disconnect()

asyncio.run(test())
"
```

**Expected output:**
```
github.com                -> productivity         (score: 100)
facebook.com              -> social_media         (score: 20)
stackoverflow.com         -> productivity         (score: 95)
youtube.com               -> entertainment        (score: 30)
```

---

### Step 19: Onboard Test Employee

```bash
cd /home/kali/Desktop/MACHINE

# Onboard employee with VPN certificate
sudo ./onboard-employee-with-nef.sh test@example.com "Test Employee"
```

**This will:**
1. Create employee in database
2. Generate VPN certificate
3. Create `.nef` file in `vpn/certs/`

---

### Step 20: Grant Traffic Monitoring Consent

```bash
# Grant consent via API
curl -X POST http://localhost:8000/api/v1/traffic/consent \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "test@example.com",
    "consented": true,
    "consent_text": "I consent to traffic monitoring for productivity analysis"
  }'
```

---

## 🔧 Service Management

### View Logs

```bash
# API logs
sudo journalctl -u tbaps-api -f

# Packet capture logs
sudo journalctl -u tbaps-packet-capture -f

# Website tracker logs
sudo journalctl -u tbaps-website-tracker -f

# VPN logger logs
sudo journalctl -u tbaps-vpn-logger -f

# All TBAPS logs
sudo journalctl -u 'tbaps-*' -f
```

### Restart Services

```bash
# Restart API
sudo systemctl restart tbaps-api

# Restart all TBAPS services
sudo systemctl restart tbaps-*

# Restart database
sudo systemctl restart postgresql

# Restart Nginx
sudo systemctl restart nginx
```

### Stop Services

```bash
# Stop all TBAPS services
sudo systemctl stop tbaps-*

# Stop database
sudo systemctl stop postgresql

# Stop Redis
sudo systemctl stop redis-server

# Stop RabbitMQ
sudo systemctl stop rabbitmq-server
```

---

## 📊 System Health Check Script

```bash
#!/bin/bash

echo "=== TBAPS System Health Check (Native) ==="
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

echo -n "VPN Logger: "
systemctl is-active tbaps-vpn-logger > /dev/null 2>&1 && echo "✓ Running" || echo "✗ Stopped"

# Check API endpoint
echo -n "API Health: "
curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "✓ Responding" || echo "✗ Not responding"

# Check database tables
echo -n "Database Tables: "
TABLE_COUNT=$(psql -U ztuser -d zerotrust -h localhost -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')
echo "$TABLE_COUNT tables"

# Check VPN interface
echo -n "VPN Interface: "
ip addr show tun0 > /dev/null 2>&1 && echo "✓ Active" || echo "✗ Not found"

echo ""
echo "=== System Status ==="
```

**Save as `health-check.sh` and run:**

```bash
chmod +x health-check.sh
./health-check.sh
```

---

## 🔧 Troubleshooting

### Issue 1: PostgreSQL Connection Failed

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo journalctl -u postgresql -n 50

# Restart PostgreSQL
sudo systemctl restart postgresql

# Verify connection
psql -U ztuser -d zerotrust -h localhost -c "SELECT 1;"
```

### Issue 2: Service Won't Start

```bash
# Check service status
sudo systemctl status tbaps-api

# View detailed logs
sudo journalctl -u tbaps-api -n 100 --no-pager

# Check if port is already in use
sudo netstat -tlnp | grep 8000

# Restart service
sudo systemctl restart tbaps-api
```

### Issue 3: Packet Capture Permission Denied

```bash
# Verify service is running as root
sudo systemctl status tbaps-packet-capture

# Check logs
sudo journalctl -u tbaps-packet-capture -n 50

# Manually test
cd /home/kali/Desktop/MACHINE/vpn/traffic-monitor
source venv/bin/activate
sudo -E venv/bin/python packet_capture.py
```

### Issue 4: VPN Interface Not Found

```bash
# Check OpenVPN status
sudo systemctl status openvpn-server@server

# Check OpenVPN logs
sudo journalctl -u openvpn-server@server -n 50

# Check network interfaces
ip addr show

# Restart OpenVPN
sudo systemctl restart openvpn-server@server
```

### Issue 5: Frontend Not Loading

```bash
# Check Nginx status
sudo systemctl status nginx

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Verify frontend files exist
ls -lh /home/kali/Desktop/MACHINE/frontend/dist/
```

---

## 📚 Quick Reference

### Service URLs
- **Frontend:** http://localhost
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **RabbitMQ Management:** http://localhost:15672

### Important Directories
- **Project:** `/home/kali/Desktop/MACHINE`
- **Logs:** `/var/log/tbaps/`
- **VPN Certs:** `/home/kali/Desktop/MACHINE/vpn/certs/`
- **Frontend Build:** `/home/kali/Desktop/MACHINE/frontend/dist/`

### Database Access
```bash
psql -U ztuser -d zerotrust -h localhost
```

### Service Commands
```bash
# Start all services
sudo systemctl start tbaps-*

# Stop all services
sudo systemctl stop tbaps-*

# Restart all services
sudo systemctl restart tbaps-*

# View all logs
sudo journalctl -u 'tbaps-*' -f
```

---

## ⚠️ Important Notes

1. **No Docker Required:** All services run natively on the system
2. **Systemd Services:** Services auto-start on boot
3. **Root Access:** Packet capture service runs as root
4. **VPN Required:** Traffic monitoring only works for VPN-connected clients
5. **Consent Required:** Employees must opt-in for traffic monitoring
6. **Privacy:** Only metadata is captured, no packet payloads

---

**Setup Complete! 🎉**

Your TBAPS system with traffic monitoring is now running natively without Docker.
