# TBAPS - Native Deployment Guide (No Docker)

## 📋 Overview

This guide provides step-by-step instructions to deploy TBAPS directly on your Linux system **without Docker**, using native services.

**Deployment Type:** Native/Bare Metal  
**Estimated Time:** 45-60 minutes  
**Last Updated:** 2026-01-28

---

## 🖥️ System Requirements

### Hardware
- **CPU:** 4+ cores
- **RAM:** 8GB minimum, 16GB recommended
- **Disk:** 20GB free space

### Software
- **OS:** Ubuntu 20.04+, Debian 11+, or similar Linux distribution
- **Python:** 3.11+
- **PostgreSQL:** 15+
- **OpenVPN:** 2.5+
- **OpenSSL:** 1.1.1+
- **Nginx:** 1.18+ (optional, for production)

---

## 📥 STEP 1: Install System Dependencies

### Install PostgreSQL

```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update and install PostgreSQL
sudo apt update
sudo apt install -y postgresql-15 postgresql-contrib-15

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
sudo systemctl status postgresql
psql --version
```

### Install Python 3.11+

```bash
# Install Python and pip
sudo apt install -y python3.11 python3.11-venv python3-pip python3.11-dev

# Verify installation
python3.11 --version
pip3 --version
```

### Install OpenVPN

```bash
# Install OpenVPN and Easy-RSA
sudo apt install -y openvpn easy-rsa

# Verify installation
openvpn --version
```

### Install OpenSSL

```bash
# Install OpenSSL
sudo apt install -y openssl

# Verify installation
openssl version
```

### Install Additional Tools

```bash
# Install required tools
sudo apt install -y git curl wget net-tools uuidgen

# Verify installations
git --version
curl --version
```

---

## 📂 STEP 2: Create Directory Structure

```bash
# Create application directories
sudo mkdir -p /opt/tbaps/{backend,vpn,logs,data}
sudo mkdir -p /srv/tbaps/vpn/{ca,certs,configs,config}
sudo mkdir -p /var/log/tbaps
sudo mkdir -p /etc/tbaps

# Set ownership
sudo chown -R $USER:$USER /opt/tbaps
sudo chown -R $USER:$USER /srv/tbaps
sudo chown -R $USER:$USER /var/log/tbaps
sudo chown -R $USER:$USER /etc/tbaps

# Verify directories
ls -la /opt/tbaps
ls -la /srv/tbaps/vpn
```

---

## 🗄️ STEP 3: Setup PostgreSQL Database

### Create Database User and Database

```bash
# Switch to postgres user
sudo -u postgres psql << EOF
-- Create database user
CREATE USER tbaps WITH PASSWORD 'tbaps_secure_password_2026';

-- Create database
CREATE DATABASE tbaps OWNER tbaps;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE tbaps TO tbaps;

-- Enable extensions
\c tbaps
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Exit
\q
EOF

# Verify database creation
psql -U tbaps -d tbaps -h localhost -c "SELECT version();"
```

### Configure PostgreSQL for Local Access

```bash
# Edit pg_hba.conf to allow local connections
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Add this line (or modify existing):
# local   all             tbaps                                   md5
# host    all             tbaps           127.0.0.1/32            md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Load Database Schemas

```bash
# Navigate to project directory
cd ~/Desktop/MACHINE

# Load VPN infrastructure schema
psql -U tbaps -d tbaps -h localhost -f vpn/database/schema.sql

# Load NEF certificate schema
psql -U tbaps -d tbaps -h localhost -f vpn/database/nef_schema.sql

# Verify tables were created
psql -U tbaps -d tbaps -h localhost -c "\dt"

# You should see tables like:
# - employees
# - vpn_certificates
# - vpn_connections
# - vpn_connection_logs
# - nef_delivery_audit
# - vpn_audit_log
```

---

## 🔐 STEP 4: Setup VPN Infrastructure

### Initialize Certificate Authority (CA)

```bash
# Navigate to CA directory
cd /srv/tbaps/vpn/ca

# Generate CA private key (2048-bit RSA)
openssl genrsa -out ca.key 2048

# Generate CA certificate (valid for 10 years)
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  -subj "/C=US/ST=California/L=San Francisco/O=TBAPS/OU=IT/CN=TBAPS-CA"

# Set secure permissions
chmod 600 ca.key
chmod 644 ca.crt

# Verify CA certificate
openssl x509 -in ca.crt -text -noout | head -20
```

### Generate Diffie-Hellman Parameters

```bash
# Generate DH parameters (2048-bit, takes 2-5 minutes)
openssl dhparam -out /srv/tbaps/vpn/dh2048.pem 2048

# Set permissions
chmod 644 /srv/tbaps/vpn/dh2048.pem
```

### Generate TLS Authentication Key

```bash
# Generate TLS auth key
openvpn --genkey secret /srv/tbaps/vpn/ta.key

# Set secure permissions
chmod 600 /srv/tbaps/vpn/ta.key
```

### Generate Server Certificate

```bash
# Navigate to certs directory
cd /srv/tbaps/vpn/certs

# Generate server private key
openssl genrsa -out server.key 2048

# Generate certificate signing request (CSR)
openssl req -new -key server.key -out server.csr \
  -subj "/C=US/ST=California/L=San Francisco/O=TBAPS/OU=IT/CN=vpn.tbaps.local"

# Sign server certificate with CA (valid for 1 year)
openssl x509 -req -in server.csr -CA /srv/tbaps/vpn/ca/ca.crt \
  -CAkey /srv/tbaps/vpn/ca/ca.key -CAcreateserial \
  -out server.crt -days 365

# Set permissions
chmod 600 server.key
chmod 644 server.crt

# Verify server certificate
openssl x509 -in server.crt -text -noout | head -20
```

### Configure OpenVPN Server

```bash
# Create OpenVPN server configuration
sudo tee /etc/openvpn/server/tbaps.conf > /dev/null << 'EOF'
# TBAPS OpenVPN Server Configuration

# Network settings
port 1194
proto udp
dev tun

# SSL/TLS settings
ca /srv/tbaps/vpn/ca/ca.crt
cert /srv/tbaps/vpn/certs/server.crt
key /srv/tbaps/vpn/certs/server.key
dh /srv/tbaps/vpn/dh2048.pem
tls-auth /srv/tbaps/vpn/ta.key 0

# Encryption settings
cipher AES-256-CBC
auth SHA256
tls-version-min 1.2

# Network configuration
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist /var/log/openvpn/ipp.txt

# Push routes to clients
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 8.8.4.4"

# Client settings
client-to-client
keepalive 10 120
max-clients 500

# Privileges
user nobody
group nogroup
persist-key
persist-tun

# Logging
status /var/log/openvpn/openvpn-status.log
log-append /var/log/openvpn/openvpn.log
verb 3
mute 20
EOF

# Create log directory
sudo mkdir -p /var/log/openvpn
sudo chown nobody:nogroup /var/log/openvpn

# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf

# Configure firewall (UFW)
sudo ufw allow 1194/udp
sudo ufw allow OpenSSH

# Add NAT rules
sudo iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o eth0 -j MASQUERADE
sudo iptables-save | sudo tee /etc/iptables/rules.v4

# Start OpenVPN server
sudo systemctl start openvpn-server@tbaps
sudo systemctl enable openvpn-server@tbaps

# Verify OpenVPN is running
sudo systemctl status openvpn-server@tbaps
```

### Configure Server IP

```bash
# Get your server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# Or use public IP for remote access
# SERVER_IP=$(curl -s ifconfig.me)

# Save server IP
echo "$SERVER_IP" > /srv/tbaps/vpn/config/server_ip.txt

echo "VPN Server IP: $SERVER_IP"
```

---

## 🐍 STEP 5: Setup Python Backend

### Copy Project Files

```bash
# Copy backend files to /opt/tbaps
cp -r ~/Desktop/MACHINE/backend/* /opt/tbaps/backend/
cp -r ~/Desktop/MACHINE/vpn /opt/tbaps/

# Verify files copied
ls -la /opt/tbaps/backend
ls -la /opt/tbaps/vpn
```

### Create Python Virtual Environment

```bash
# Navigate to backend directory
cd /opt/tbaps/backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installations
pip list | grep fastapi
pip list | grep asyncpg
pip list | grep uvicorn
```

### Configure Environment Variables

```bash
# Create .env file
cat > /opt/tbaps/backend/.env << EOF
# Database Configuration
DATABASE_URL=postgresql://tbaps:tbaps_secure_password_2026@localhost:5432/tbaps

# Application Configuration
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=False
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000

# VPN Configuration
OPENVPN_SERVER_IP=$(cat /srv/tbaps/vpn/config/server_ip.txt)
VPN_CA_PATH=/srv/tbaps/vpn/ca/ca.crt
VPN_TA_KEY_PATH=/srv/tbaps/vpn/ta.key

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/tbaps/backend.log
EOF

# Secure the .env file
chmod 600 /opt/tbaps/backend/.env
```

### Test Backend

```bash
# Activate virtual environment
cd /opt/tbaps/backend
source venv/bin/activate

# Test run (Ctrl+C to stop)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal, test:
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/nef/health
```

---

## 🔧 STEP 6: Create Systemd Services

### Create Backend Service

```bash
# Create systemd service file
sudo tee /etc/systemd/system/tbaps-backend.service > /dev/null << EOF
[Unit]
Description=TBAPS FastAPI Backend
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/tbaps/backend
Environment="PATH=/opt/tbaps/backend/venv/bin"
ExecStart=/opt/tbaps/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Start backend service
sudo systemctl start tbaps-backend
sudo systemctl enable tbaps-backend

# Check status
sudo systemctl status tbaps-backend
```

### Create VPN Logger Service

```bash
# Create VPN logger script
cat > /opt/tbaps/vpn/vpn_logger.sh << 'EOF'
#!/bin/bash
cd /opt/tbaps/backend
source venv/bin/activate
python3 /opt/tbaps/vpn/logger/vpn_logger.py
EOF

chmod +x /opt/tbaps/vpn/vpn_logger.sh

# Create systemd service
sudo tee /etc/systemd/system/tbaps-vpn-logger.service > /dev/null << EOF
[Unit]
Description=TBAPS VPN Connection Logger
After=network.target postgresql.service openvpn-server@tbaps.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/tbaps/vpn
ExecStart=/opt/tbaps/vpn/vpn_logger.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Start VPN logger service
sudo systemctl start tbaps-vpn-logger
sudo systemctl enable tbaps-vpn-logger

# Check status
sudo systemctl status tbaps-vpn-logger
```

---

## 🧪 STEP 7: Test the System

### Test Database Connection

```bash
# Connect to PostgreSQL
psql -U tbaps -d tbaps -h localhost

# Run test queries
SELECT COUNT(*) FROM vpn_certificates;
SELECT COUNT(*) FROM employees;
\q
```

### Test VPN Server

```bash
# Check OpenVPN status
sudo systemctl status openvpn-server@tbaps

# View OpenVPN logs
sudo tail -f /var/log/openvpn/openvpn.log

# Check listening port
sudo netstat -tulpn | grep 1194
```

### Test Backend API

```bash
# Health check
curl http://localhost:8000/health

# NEF certificate endpoints
curl http://localhost:8000/api/v1/nef/health
curl http://localhost:8000/api/v1/nef/list?status=active
curl http://localhost:8000/api/v1/nef/statistics

# API documentation
curl http://localhost:8000/docs
# Open in browser: http://YOUR_SERVER_IP:8000/docs
```

### Generate Test Certificate

```bash
# Make scripts executable
chmod +x /opt/tbaps/vpn/scripts/*.sh

# Generate test certificate
cd /opt/tbaps/vpn/scripts
./generate-nef-certificate.sh "Test User" "test@company.com"

# Verify certificate created
ls -lh /srv/tbaps/vpn/configs/test_user.nef

# Check in database
psql -U tbaps -d tbaps -h localhost -c \
  "SELECT certificate_id, employee_name, status FROM vpn_certificates WHERE certificate_id='test_user';"
```

### Test Employee Onboarding

```bash
# Run onboarding script
cd /opt/tbaps/vpn/scripts
./onboard-employee-with-nef.sh

# Follow prompts to create test employee
```

### Test Batch Generation

```bash
# Create test CSV
cat > /tmp/test_employees.csv << EOF
name,email,department,role
Alice Johnson,alice@company.com,Engineering,Developer
Bob Smith,bob@company.com,Sales,Manager
Carol White,carol@company.com,HR,Specialist
EOF

# Run batch generation
cd /opt/tbaps/vpn/scripts
./batch-generate-nef-certificates.sh /tmp/test_employees.csv

# Check results
ls -lh /srv/tbaps/vpn/configs/
```

---

## 🌐 STEP 8: Configure Nginx (Optional - Production)

### Install Nginx

```bash
# Install Nginx
sudo apt install -y nginx

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Configure Nginx as Reverse Proxy

```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/tbaps << 'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    # Backend API
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support (if needed)
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files (if any)
    location /static {
        alias /opt/tbaps/backend/static;
    }

    # Logs
    access_log /var/log/nginx/tbaps_access.log;
    error_log /var/log/nginx/tbaps_error.log;
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/tbaps /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Allow HTTP through firewall
sudo ufw allow 'Nginx Full'
```

---

## 📊 STEP 9: Verify Complete Deployment

### System Services Check

```bash
# Check all services
echo "=== Service Status ==="
sudo systemctl status postgresql | grep Active
sudo systemctl status openvpn-server@tbaps | grep Active
sudo systemctl status tbaps-backend | grep Active
sudo systemctl status tbaps-vpn-logger | grep Active
sudo systemctl status nginx | grep Active
```

### Database Check

```bash
# Check database tables
psql -U tbaps -d tbaps -h localhost -c "\dt" | wc -l
# Should show 10+ tables

# Check views
psql -U tbaps -d tbaps -h localhost -c "\dv"

# Check functions
psql -U tbaps -d tbaps -h localhost -c "\df"
```

### VPN Infrastructure Check

```bash
# Check CA files
ls -la /srv/tbaps/vpn/ca/ca.{crt,key}

# Check server certificate
ls -la /srv/tbaps/vpn/certs/server.{crt,key}

# Check TLS auth key
ls -la /srv/tbaps/vpn/ta.key

# Check DH parameters
ls -la /srv/tbaps/vpn/dh2048.pem

# Check OpenVPN status
sudo systemctl status openvpn-server@tbaps
```

### Backend API Check

```bash
# Health endpoint
curl http://localhost:8000/health

# NEF endpoints
curl http://localhost:8000/api/v1/nef/health
curl http://localhost:8000/api/v1/nef/statistics

# List certificates
curl http://localhost:8000/api/v1/nef/list?status=active
```

### Network Ports Check

```bash
# Check listening ports
sudo netstat -tulpn | grep -E '(5432|8000|1194|80)'

# Expected output:
# 5432 - PostgreSQL
# 8000 - FastAPI Backend
# 1194 - OpenVPN Server
# 80   - Nginx (if configured)
```

### Certificate Generation Check

```bash
# List generated certificates
ls -lh /srv/tbaps/vpn/configs/

# Count certificates in database
psql -U tbaps -d tbaps -h localhost -c \
  "SELECT COUNT(*) as total_certificates FROM vpn_certificates;"
```

---

## 🔄 STEP 10: Daily Operations

### Start All Services

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Start OpenVPN
sudo systemctl start openvpn-server@tbaps

# Start Backend
sudo systemctl start tbaps-backend

# Start VPN Logger
sudo systemctl start tbaps-vpn-logger

# Start Nginx (if configured)
sudo systemctl start nginx
```

### Stop All Services

```bash
# Stop services in reverse order
sudo systemctl stop nginx
sudo systemctl stop tbaps-vpn-logger
sudo systemctl stop tbaps-backend
sudo systemctl stop openvpn-server@tbaps
sudo systemctl stop postgresql
```

### View Logs

```bash
# Backend logs
sudo journalctl -u tbaps-backend -f

# VPN logger logs
sudo journalctl -u tbaps-vpn-logger -f

# OpenVPN logs
sudo tail -f /var/log/openvpn/openvpn.log

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# Nginx logs (if configured)
sudo tail -f /var/log/nginx/tbaps_access.log
```

### Generate Employee Certificate

```bash
cd /opt/tbaps/vpn/scripts
./generate-nef-certificate.sh "Employee Name" "email@company.com"
```

### Onboard New Employee

```bash
cd /opt/tbaps/vpn/scripts
./onboard-employee-with-nef.sh
```

### Revoke Certificate

```bash
cd /opt/tbaps/vpn/scripts
./revoke-employee-cert.sh employee_id "Reason for revocation"
```

### Database Backup

```bash
# Backup database
pg_dump -U tbaps -h localhost tbaps > /opt/tbaps/data/tbaps_backup_$(date +%Y%m%d).sql

# Restore database
psql -U tbaps -h localhost tbaps < /opt/tbaps/data/tbaps_backup_20260128.sql
```

---

## 🐛 Troubleshooting

### PostgreSQL Issues

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# Test connection
psql -U tbaps -d tbaps -h localhost -c "SELECT 1;"
```

### OpenVPN Issues

```bash
# Check OpenVPN status
sudo systemctl status openvpn-server@tbaps

# Restart OpenVPN
sudo systemctl restart openvpn-server@tbaps

# Check OpenVPN logs
sudo tail -f /var/log/openvpn/openvpn.log

# Check if port 1194 is listening
sudo netstat -tulpn | grep 1194

# Check firewall
sudo ufw status
```

### Backend API Issues

```bash
# Check backend status
sudo systemctl status tbaps-backend

# Restart backend
sudo systemctl restart tbaps-backend

# Check backend logs
sudo journalctl -u tbaps-backend -f

# Check if port 8000 is listening
sudo netstat -tulpn | grep 8000

# Test manually
cd /opt/tbaps/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Certificate Generation Issues

```bash
# Check CA files
ls -la /srv/tbaps/vpn/ca/

# Check permissions
chmod 600 /srv/tbaps/vpn/ca/ca.key
chmod 644 /srv/tbaps/vpn/ca/ca.crt

# Check OpenSSL
openssl version

# Test CA certificate
openssl x509 -in /srv/tbaps/vpn/ca/ca.crt -text -noout
```

### Permission Issues

```bash
# Fix directory permissions
sudo chown -R $USER:$USER /opt/tbaps
sudo chown -R $USER:$USER /srv/tbaps
sudo chown -R $USER:$USER /var/log/tbaps

# Fix script permissions
chmod +x /opt/tbaps/vpn/scripts/*.sh

# Fix certificate permissions
chmod 600 /srv/tbaps/vpn/ca/ca.key
chmod 644 /srv/tbaps/vpn/ca/ca.crt
chmod 600 /srv/tbaps/vpn/ta.key
```

---

## 📝 Configuration Files Summary

### Key Files and Locations

```
/opt/tbaps/
├── backend/                      # FastAPI application
│   ├── app/                      # Application code
│   ├── venv/                     # Python virtual environment
│   ├── .env                      # Environment variables
│   └── requirements.txt          # Python dependencies
└── vpn/                          # VPN management
    ├── scripts/                  # Management scripts
    ├── database/                 # Database schemas
    └── logger/                   # VPN logger

/srv/tbaps/vpn/
├── ca/                           # Certificate Authority
│   ├── ca.crt                    # CA certificate
│   └── ca.key                    # CA private key
├── certs/                        # Server & client certificates
│   ├── server.crt                # Server certificate
│   └── server.key                # Server private key
├── configs/                      # Generated .nef files
├── config/                       # Configuration
│   └── server_ip.txt             # VPN server IP
├── dh2048.pem                    # DH parameters
└── ta.key                        # TLS auth key

/etc/openvpn/server/
└── tbaps.conf                    # OpenVPN server config

/etc/systemd/system/
├── tbaps-backend.service         # Backend service
└── tbaps-vpn-logger.service      # VPN logger service

/var/log/
├── tbaps/                        # Application logs
├── openvpn/                      # OpenVPN logs
└── postgresql/                   # PostgreSQL logs
```

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] Ubuntu/Debian Linux installed
- [ ] Minimum 8GB RAM available
- [ ] 20GB disk space free
- [ ] Sudo access available

### Installation
- [ ] PostgreSQL 15+ installed and running
- [ ] Python 3.11+ installed
- [ ] OpenVPN installed
- [ ] OpenSSL installed
- [ ] All directories created

### Database
- [ ] Database user 'tbaps' created
- [ ] Database 'tbaps' created
- [ ] VPN schema loaded
- [ ] NEF schema loaded
- [ ] Tables verified (10+ tables)

### VPN Infrastructure
- [ ] CA certificate generated
- [ ] Server certificate generated
- [ ] DH parameters generated
- [ ] TLS auth key generated
- [ ] OpenVPN server configured
- [ ] OpenVPN service running
- [ ] Firewall configured

### Backend
- [ ] Python virtual environment created
- [ ] Dependencies installed
- [ ] .env file configured
- [ ] Backend service created
- [ ] Backend service running
- [ ] API responding

### Testing
- [ ] Database connection works
- [ ] OpenVPN server running
- [ ] Backend API accessible
- [ ] Test certificate generated
- [ ] Certificate in database
- [ ] All services enabled

### Production (Optional)
- [ ] Nginx installed and configured
- [ ] SSL/TLS certificates configured
- [ ] Firewall rules configured
- [ ] Backup procedures in place
- [ ] Monitoring configured

---

## 🎉 Deployment Complete!

Your TBAPS system is now deployed natively without Docker!

### Access Points

- **Backend API:** http://YOUR_SERVER_IP:8000
- **API Documentation:** http://YOUR_SERVER_IP:8000/docs
- **Database:** localhost:5432
- **VPN Server:** YOUR_SERVER_IP:1194

### Next Steps

1. Generate employee certificates
2. Distribute .nef files to employees
3. Monitor logs for issues
4. Set up regular backups
5. Configure monitoring (optional)

---

**Status:** ✅ NATIVE DEPLOYMENT COMPLETE  
**Last Updated:** 2026-01-28  
**Version:** 1.0.0

**🎉 Your TBAPS system is running natively! 🎉**
