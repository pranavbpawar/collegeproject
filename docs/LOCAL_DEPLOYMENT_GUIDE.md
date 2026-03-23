# TBAPS - Complete Local Deployment Guide

## 📋 Overview

This guide provides step-by-step instructions to deploy and run the complete TBAPS (Trust-Based Algorithmic Performance System) locally, including:

- Backend API (FastAPI)
- PostgreSQL Database
- VPN Infrastructure (OpenVPN)
- NEF Certificate Management
- All supporting services

**Estimated Setup Time:** 30-45 minutes  
**Last Updated:** 2026-01-28

---

## 🖥️ System Requirements

### Hardware
- **CPU:** 4+ cores recommended
- **RAM:** 8GB minimum, 16GB recommended
- **Disk:** 20GB free space
- **Network:** Internet connection for initial setup

### Software Prerequisites
- **OS:** Linux (Ubuntu 20.04+, Debian 11+) or macOS
- **Docker:** 20.10+
- **Docker Compose:** 2.0+
- **Git:** 2.0+
- **OpenSSL:** 1.1.1+
- **Bash:** 4.0+

---

## 📥 Step 1: Install Prerequisites

### On Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install Docker
sudo apt install -y docker.io docker-compose

# Install other dependencies
sudo apt install -y git openssl curl wget

# Add your user to docker group (logout/login required after this)
sudo usermod -aG docker $USER

# Verify installations
docker --version
docker-compose --version
git --version
openssl version
```

### On macOS

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Install other dependencies
brew install git openssl

# Start Docker Desktop
open -a Docker

# Verify installations
docker --version
docker-compose --version
git --version
openssl version
```

---

## 📂 Step 2: Clone and Setup Project

```bash
# Navigate to your workspace
cd ~/Desktop

# If not already cloned, clone the repository
# (Skip if you already have the MACHINE directory)
# git clone <repository-url> MACHINE

# Navigate to project directory
cd MACHINE

# Verify project structure
ls -la
# You should see: backend/, vpn/, docker-compose.yml, etc.
```

---

## 🗄️ Step 3: Setup PostgreSQL Database

### Create Environment File

```bash
# Create .env file for database credentials
cat > .env << 'EOF'
# PostgreSQL Configuration
POSTGRES_USER=tbaps
POSTGRES_PASSWORD=tbaps_secure_password_2026
POSTGRES_DB=tbaps
DATABASE_URL=postgresql://tbaps:tbaps_secure_password_2026@postgresql:5432/tbaps

# VPN Configuration
OPENVPN_SERVER_IP=192.168.1.100

# Application Configuration
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ENVIRONMENT=development
EOF

# Secure the .env file
chmod 600 .env
```

### Start PostgreSQL

```bash
# Start PostgreSQL container
docker-compose up -d postgresql

# Wait for PostgreSQL to be ready (about 10 seconds)
sleep 10

# Verify PostgreSQL is running
docker-compose ps postgresql

# Test database connection
docker-compose exec postgresql psql -U tbaps -d tbaps -c "SELECT version();"
```

### Initialize Database Schema

```bash
# Create all database tables and schemas

# 1. Main VPN infrastructure schema
docker-compose exec -T postgresql psql -U tbaps -d tbaps < vpn/database/schema.sql

# 2. NEF certificate management schema
docker-compose exec -T postgresql psql -U tbaps -d tbaps < vpn/database/nef_schema.sql

# Verify tables were created
docker-compose exec postgresql psql -U tbaps -d tbaps -c "\dt"

# You should see tables like:
# - employees
# - vpn_certificates
# - vpn_connections
# - vpn_connection_logs
# - nef_delivery_audit
# - vpn_audit_log
# etc.
```

---

## 🔐 Step 4: Setup VPN Infrastructure

### Create VPN Directory Structure

```bash
# Create required directories
sudo mkdir -p /srv/tbaps/vpn/{certificates,certs,configs,ca,config}
sudo mkdir -p /var/log/tbaps

# Set permissions
sudo chown -R $USER:$USER /srv/tbaps
sudo chown -R $USER:$USER /var/log/tbaps
```

### Generate Certificate Authority (CA)

```bash
# Navigate to CA directory
cd /srv/tbaps/vpn/ca

# Generate CA private key
openssl genrsa -out ca.key 2048

# Generate CA certificate (valid for 10 years)
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  -subj "/C=US/ST=State/L=City/O=TBAPS/CN=TBAPS-CA"

# Set secure permissions
chmod 600 ca.key
chmod 644 ca.crt

# Verify CA certificate
openssl x509 -in ca.crt -text -noout | head -20
```

### Generate TLS Authentication Key

```bash
# Generate TLS auth key
openvpn --genkey --secret /srv/tbaps/vpn/ta.key

# Set permissions
chmod 600 /srv/tbaps/vpn/ta.key
```

### Configure VPN Server IP

```bash
# Set your server IP (use your actual IP or localhost for testing)
# To find your IP: ip addr show | grep "inet " | grep -v 127.0.0.1

# For local testing, use localhost
echo "127.0.0.1" > /srv/tbaps/vpn/config/server_ip.txt

# For production, use your public IP
# echo "YOUR_PUBLIC_IP" > /srv/tbaps/vpn/config/server_ip.txt
```

### Start OpenVPN Server

```bash
# Navigate back to project root
cd ~/Desktop/MACHINE

# Start OpenVPN and VPN services
docker-compose -f docker-compose.vpn.yml up -d

# Verify services are running
docker-compose -f docker-compose.vpn.yml ps

# Check OpenVPN logs
docker-compose -f docker-compose.vpn.yml logs openvpn

# Check VPN logger
docker-compose -f docker-compose.vpn.yml logs vpn-logger
```

---

## 🚀 Step 5: Setup Backend API

### Install Python Dependencies

```bash
# Navigate to backend directory
cd ~/Desktop/MACHINE/backend

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
pip list | grep asyncpg
```

### Configure Backend Environment

```bash
# Copy environment template
cp .env.test .env.local

# Edit .env.local with your settings
cat > .env.local << 'EOF'
# Database
DATABASE_URL=postgresql://tbaps:tbaps_secure_password_2026@localhost:5432/tbaps

# Application
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ENVIRONMENT=development

# VPN
OPENVPN_SERVER_IP=127.0.0.1
EOF
```

### Start Backend API

```bash
# Option 1: Run with Uvicorn directly
cd ~/Desktop/MACHINE/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Run with Docker (recommended)
cd ~/Desktop/MACHINE
docker-compose up -d backend

# Verify backend is running
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/nef/health
```

---

## 🧪 Step 6: Test the System

### Test Database Connection

```bash
# Connect to PostgreSQL
docker-compose exec postgresql psql -U tbaps -d tbaps

# Run some test queries
SELECT COUNT(*) FROM vpn_certificates;
SELECT COUNT(*) FROM employees;
\q
```

### Test NEF Certificate Generation

```bash
# Navigate to VPN scripts
cd ~/Desktop/MACHINE/vpn/scripts

# Make scripts executable (if not already)
chmod +x *.sh

# Generate a test certificate
./generate-nef-certificate.sh "Test User" "test@company.com"

# Verify certificate was created
ls -lh /srv/tbaps/vpn/configs/test_user.nef

# Check database entry
docker-compose exec postgresql psql -U tbaps -d tbaps -c \
  "SELECT certificate_id, employee_name, status FROM vpn_certificates WHERE certificate_id = 'test_user';"
```

### Test API Endpoints

```bash
# Test health endpoint
curl http://localhost:8000/api/v1/nef/health

# Generate certificate via API
curl -X POST http://localhost:8000/api/v1/nef/generate \
  -H "Content-Type: application/json" \
  -d '{
    "employee_name": "API Test User",
    "employee_email": "apitest@company.com"
  }'

# List certificates
curl http://localhost:8000/api/v1/nef/list?status=active

# Get certificate status
curl http://localhost:8000/api/v1/nef/status/api_test_user

# Get statistics
curl http://localhost:8000/api/v1/nef/statistics
```

### Test Employee Onboarding

```bash
# Run interactive onboarding
cd ~/Desktop/MACHINE/vpn/scripts
./onboard-employee-with-nef.sh

# Follow the prompts:
# Employee Full Name: John Doe
# Employee Email Address: john.doe@company.com
# Department: Engineering
# Job Role: Developer
# Manager Name: Jane Smith
# Is this information correct? (yes/no): yes
```

### Test Batch Generation

```bash
# Create sample CSV file
cat > /tmp/test_employees.csv << 'EOF'
name,email,department,role
Alice Johnson,alice@company.com,Engineering,Senior Developer
Bob Smith,bob@company.com,Sales,Account Manager
Carol White,carol@company.com,HR,HR Specialist
EOF

# Run batch generation
cd ~/Desktop/MACHINE/vpn/scripts
./batch-generate-nef-certificates.sh /tmp/test_employees.csv

# Check results
ls -lh /srv/tbaps/vpn/configs/
```

---

## 🌐 Step 7: Access the System

### API Documentation

```bash
# Open in browser:
# http://localhost:8000/docs          # Swagger UI
# http://localhost:8000/redoc         # ReDoc
```

### Database Access

```bash
# Using psql
docker-compose exec postgresql psql -U tbaps -d tbaps

# Using a GUI tool (e.g., pgAdmin, DBeaver)
# Host: localhost
# Port: 5432
# Database: tbaps
# Username: tbaps
# Password: tbaps_secure_password_2026
```

### VPN Server

```bash
# Check OpenVPN status
docker-compose -f docker-compose.vpn.yml ps

# View OpenVPN logs
docker-compose -f docker-compose.vpn.yml logs -f openvpn

# View connection logs
docker-compose -f docker-compose.vpn.yml logs -f vpn-logger
```

---

## 📊 Step 8: Verify Everything is Working

### Quick Verification Checklist

```bash
# 1. Check all containers are running
docker-compose ps
docker-compose -f docker-compose.vpn.yml ps

# 2. Check database tables
docker-compose exec postgresql psql -U tbaps -d tbaps -c "\dt"

# 3. Check API health
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/nef/health

# 4. Check generated certificates
ls -lh /srv/tbaps/vpn/configs/

# 5. Check database entries
docker-compose exec postgresql psql -U tbaps -d tbaps -c \
  "SELECT COUNT(*) as total_certificates FROM vpn_certificates;"

# 6. Check logs
tail -f /var/log/tbaps/nef_generation.log
```

### Expected Results

✅ PostgreSQL container running  
✅ Backend API responding on port 8000  
✅ OpenVPN server running on port 1194  
✅ VPN logger service running  
✅ Database tables created  
✅ Test certificates generated  
✅ API endpoints responding  

---

## 🔧 Step 9: Common Operations

### Generate Employee Certificate

```bash
cd ~/Desktop/MACHINE/vpn/scripts
./generate-nef-certificate.sh "Employee Name" "email@company.com"
```

### Onboard New Employee

```bash
cd ~/Desktop/MACHINE/vpn/scripts
./onboard-employee-with-nef.sh
```

### Revoke Certificate

```bash
cd ~/Desktop/MACHINE/vpn/scripts
./revoke-employee-cert.sh emp-001 "Employee terminated"
```

### View Active Certificates

```bash
docker-compose exec postgresql psql -U tbaps -d tbaps -c \
  "SELECT * FROM vpn_active_nef_certificates;"
```

### View Connection Logs

```bash
docker-compose exec postgresql psql -U tbaps -d tbaps -c \
  "SELECT * FROM vpn_recent_connections LIMIT 10;"
```

### Check Expiring Certificates

```bash
curl http://localhost:8000/api/v1/nef/expiring?days=30
```

---

## 🛑 Step 10: Stop the System

### Stop All Services

```bash
# Stop backend and database
cd ~/Desktop/MACHINE
docker-compose down

# Stop VPN services
docker-compose -f docker-compose.vpn.yml down

# Or stop everything at once
docker-compose down && docker-compose -f docker-compose.vpn.yml down
```

### Stop and Remove All Data

```bash
# WARNING: This will delete all data!

# Stop all services
docker-compose down -v
docker-compose -f docker-compose.vpn.yml down -v

# Remove generated certificates
sudo rm -rf /srv/tbaps/vpn/configs/*
sudo rm -rf /srv/tbaps/vpn/certs/*

# Remove logs
sudo rm -rf /var/log/tbaps/*
```

---

## 🔄 Step 11: Restart the System

### Quick Restart

```bash
cd ~/Desktop/MACHINE

# Start database
docker-compose up -d postgresql
sleep 10

# Start VPN services
docker-compose -f docker-compose.vpn.yml up -d

# Start backend
docker-compose up -d backend

# Or start everything at once
docker-compose up -d && docker-compose -f docker-compose.vpn.yml up -d
```

### Full Restart (with logs)

```bash
cd ~/Desktop/MACHINE

# Stop everything
docker-compose down
docker-compose -f docker-compose.vpn.yml down

# Start with logs visible
docker-compose up -d && docker-compose logs -f &
docker-compose -f docker-compose.vpn.yml up -d && docker-compose -f docker-compose.vpn.yml logs -f &
```

---

## 🐛 Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgresql

# Check PostgreSQL logs
docker-compose logs postgresql

# Test connection
docker-compose exec postgresql psql -U tbaps -d tbaps -c "SELECT 1;"

# Restart PostgreSQL
docker-compose restart postgresql
```

### Certificate Generation Fails

```bash
# Check CA files exist
ls -la /srv/tbaps/vpn/ca/

# Check permissions
chmod 600 /srv/tbaps/vpn/ca/ca.key
chmod 644 /srv/tbaps/vpn/ca/ca.crt

# Check logs
tail -f /var/log/tbaps/nef_generation.log

# Verify OpenSSL
openssl version
```

### API Not Responding

```bash
# Check if backend is running
docker-compose ps backend

# Check backend logs
docker-compose logs backend

# Check if port 8000 is in use
sudo netstat -tulpn | grep 8000

# Restart backend
docker-compose restart backend
```

### VPN Server Issues

```bash
# Check OpenVPN status
docker-compose -f docker-compose.vpn.yml ps openvpn

# Check OpenVPN logs
docker-compose -f docker-compose.vpn.yml logs openvpn

# Restart OpenVPN
docker-compose -f docker-compose.vpn.yml restart openvpn
```

### Port Already in Use

```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill the process (replace PID)
sudo kill -9 PID

# Or change the port in docker-compose.yml
```

### Permission Denied Errors

```bash
# Fix directory permissions
sudo chown -R $USER:$USER /srv/tbaps
sudo chown -R $USER:$USER /var/log/tbaps

# Fix script permissions
chmod +x ~/Desktop/MACHINE/vpn/scripts/*.sh
```

---

## 📝 Configuration Files

### Key Configuration Files

```
MACHINE/
├── .env                              # Main environment variables
├── docker-compose.yml                # Main services (PostgreSQL, backend)
├── docker-compose.vpn.yml            # VPN services
├── backend/
│   ├── .env.local                    # Backend environment
│   └── requirements.txt              # Python dependencies
└── vpn/
    ├── database/
    │   ├── schema.sql                # VPN database schema
    │   └── nef_schema.sql            # NEF certificate schema
    └── scripts/
        ├── generate-nef-certificate.sh
        ├── onboard-employee-with-nef.sh
        └── batch-generate-nef-certificates.sh
```

### Important Directories

```
/srv/tbaps/vpn/
├── ca/                               # Certificate Authority files
│   ├── ca.crt                        # CA certificate
│   └── ca.key                        # CA private key
├── certs/                            # Individual certificates
├── configs/                          # Generated .nef files
├── config/
│   └── server_ip.txt                 # VPN server IP
└── ta.key                            # TLS auth key

/var/log/tbaps/
├── nef_generation.log                # Certificate generation logs
└── batch_nef_generation_*.log        # Batch generation logs
```

---

## 🔒 Security Notes

### For Development

- Default passwords are used - **CHANGE IN PRODUCTION**
- Debug mode is enabled
- All services run on localhost
- Certificates are for testing only

### For Production

1. **Change all default passwords**
2. **Disable debug mode**
3. **Use proper SSL/TLS certificates**
4. **Configure firewall rules**
5. **Use environment-specific .env files**
6. **Enable authentication on all endpoints**
7. **Set up proper backup procedures**
8. **Use secrets management (e.g., Vault)**

---

## 📚 Additional Resources

### Documentation

- **VPN Infrastructure:** `vpn/docs/VPN_INFRASTRUCTURE.md`
- **NEF Certificates:** `vpn/docs/NEF_CERTIFICATE_MANAGEMENT.md`
- **Employee Setup:** `vpn/docs/EMPLOYEE_SETUP_INSTRUCTIONS.md`
- **API Documentation:** http://localhost:8000/docs

### Support

- **Logs Directory:** `/var/log/tbaps/`
- **Database:** `docker-compose exec postgresql psql -U tbaps -d tbaps`
- **API Health:** http://localhost:8000/health

---

## ✅ Quick Start Summary

```bash
# 1. Install prerequisites
sudo apt install -y docker.io docker-compose git openssl

# 2. Navigate to project
cd ~/Desktop/MACHINE

# 3. Create .env file
cat > .env << 'EOF'
POSTGRES_USER=tbaps
POSTGRES_PASSWORD=tbaps_secure_password_2026
POSTGRES_DB=tbaps
DATABASE_URL=postgresql://tbaps:tbaps_secure_password_2026@postgresql:5432/tbaps
OPENVPN_SERVER_IP=127.0.0.1
EOF

# 4. Start PostgreSQL
docker-compose up -d postgresql
sleep 10

# 5. Initialize database
docker-compose exec -T postgresql psql -U tbaps -d tbaps < vpn/database/schema.sql
docker-compose exec -T postgresql psql -U tbaps -d tbaps < vpn/database/nef_schema.sql

# 6. Setup VPN directories
sudo mkdir -p /srv/tbaps/vpn/{ca,configs,config}
sudo chown -R $USER:$USER /srv/tbaps

# 7. Generate CA
cd /srv/tbaps/vpn/ca
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  -subj "/C=US/ST=State/L=City/O=TBAPS/CN=TBAPS-CA"
openvpn --genkey --secret /srv/tbaps/vpn/ta.key

# 8. Configure server IP
echo "127.0.0.1" > /srv/tbaps/vpn/config/server_ip.txt

# 9. Start all services
cd ~/Desktop/MACHINE
docker-compose up -d
docker-compose -f docker-compose.vpn.yml up -d

# 10. Test the system
curl http://localhost:8000/health
cd vpn/scripts
./generate-nef-certificate.sh "Test User" "test@company.com"
```

---

**Status:** ✅ READY FOR LOCAL DEPLOYMENT  
**Last Updated:** 2026-01-28  
**Version:** 1.0.0

**🎉 You're all set! Your TBAPS system is now running locally. 🎉**
