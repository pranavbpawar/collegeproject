# TBAPS - Detailed Local Deployment Map

## 🗺️ Complete System Architecture & Deployment Flow

**Last Updated:** 2026-01-28  
**Deployment Type:** Local Development Environment

---

## 📊 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TBAPS COMPLETE SYSTEM                                │
│                         Local Deployment Map                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────┐
                                    │   CLIENT     │
                                    │  (Browser)   │
                                    └──────┬───────┘
                                           │
                                           │ HTTP/HTTPS
                                           │ Port 8000
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      FastAPI Backend                                 │   │
│  │                      (Port 8000)                                     │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                       │   │
│  │  API Endpoints:                                                      │   │
│  │  ├─ /api/v1/nef/*              NEF Certificate Management           │   │
│  │  ├─ /api/v1/copilot/*          Employee Copilot                     │   │
│  │  ├─ /api/v1/intervention/*     Intervention Engine                  │   │
│  │  ├─ /api/v1/bias/*             Bias Detection                       │   │
│  │  └─ /docs                      API Documentation (Swagger)          │   │
│  │                                                                       │   │
│  │  Services:                                                           │   │
│  │  ├─ Employee Copilot Service                                        │   │
│  │  ├─ Intervention Engine                                             │   │
│  │  ├─ Bias Detection System                                           │   │
│  │  └─ NEF Certificate Manager                                         │   │
│  │                                                                       │   │
│  └───────────────────────────┬─────────────────────────────────────────┘   │
│                              │                                               │
│                              │ asyncpg                                       │
│                              │ (PostgreSQL Driver)                           │
│                              ▼                                               │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                          DATABASE LAYER                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   PostgreSQL Database                                │   │
│  │                   (Port 5432)                                        │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                       │   │
│  │  Schemas:                                                            │   │
│  │  ├─ employees                  Employee master data                 │   │
│  │  ├─ vpn_certificates           VPN certificate lifecycle            │   │
│  │  ├─ vpn_connections            Connection logs                      │   │
│  │  ├─ vpn_connection_logs        Detailed session logs                │   │
│  │  ├─ nef_delivery_audit         Certificate delivery tracking        │   │
│  │  ├─ vpn_audit_log              Audit trail                          │   │
│  │  ├─ trust_scores               Employee trust metrics               │   │
│  │  ├─ signal_events              Performance signals                  │   │
│  │  └─ intervention_history       Intervention tracking                │   │
│  │                                                                       │   │
│  │  Views:                                                              │   │
│  │  ├─ vpn_active_nef_certificates                                     │   │
│  │  ├─ vpn_expiring_nef_certificates                                   │   │
│  │  ├─ vpn_recent_connections                                          │   │
│  │  └─ vpn_certificate_usage_stats                                     │   │
│  │                                                                       │   │
│  │  Functions:                                                          │   │
│  │  ├─ auto_expire_nef_certificates()                                  │   │
│  │  ├─ increment_download_count()                                      │   │
│  │  ├─ log_vpn_connection()                                            │   │
│  │  └─ calculate_vpn_session_duration()                                │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                          VPN INFRASTRUCTURE LAYER                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   OpenVPN Server                                     │   │
│  │                   (Port 1194/UDP)                                    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                       │   │
│  │  Configuration:                                                      │   │
│  │  ├─ Protocol: UDP                                                   │   │
│  │  ├─ Encryption: AES-256-CBC                                         │   │
│  │  ├─ Authentication: SHA256                                          │   │
│  │  ├─ TLS Version: 1.2+                                               │   │
│  │  ├─ Key Exchange: RSA-2048                                          │   │
│  │  └─ Max Clients: 500                                                │   │
│  │                                                                       │   │
│  │  Certificate Authority:                                              │   │
│  │  ├─ /srv/tbaps/vpn/ca/ca.crt   (CA Certificate)                    │   │
│  │  ├─ /srv/tbaps/vpn/ca/ca.key   (CA Private Key)                    │   │
│  │  └─ /srv/tbaps/vpn/ta.key      (TLS Auth Key)                      │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   VPN Connection Logger                              │   │
│  │                   (Python Service)                                   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                       │   │
│  │  Monitors:                                                           │   │
│  │  ├─ /var/log/openvpn/openvpn-status.log                            │   │
│  │  ├─ Active connections                                              │   │
│  │  ├─ Connection events                                               │   │
│  │  └─ Traffic statistics                                              │   │
│  │                                                                       │   │
│  │  Logs to:                                                            │   │
│  │  └─ PostgreSQL (vpn_connection_logs table)                          │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                          FILE SYSTEM LAYER                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  /srv/tbaps/vpn/                                                             │
│  ├─ ca/                           Certificate Authority                      │
│  │  ├─ ca.crt                     CA Certificate (10 year validity)          │
│  │  └─ ca.key                     CA Private Key (2048-bit RSA)              │
│  ├─ certs/                        Individual Certificates                    │
│  │  ├─ employee_id.csr            Certificate Signing Request                │
│  │  ├─ employee_id.crt            Signed Certificate                         │
│  │  └─ employee_id.key            Private Key                                │
│  ├─ configs/                      Generated .nef Files                       │
│  │  └─ employee_id.nef            Complete VPN config (embedded certs)       │
│  ├─ config/                       Configuration                              │
│  │  └─ server_ip.txt              VPN Server IP Address                      │
│  └─ ta.key                        TLS Authentication Key                     │
│                                                                               │
│  /var/log/tbaps/                                                             │
│  ├─ nef_generation.log            Certificate generation logs                │
│  └─ batch_nef_generation_*.log   Batch generation logs                      │
│                                                                               │
│  ~/Desktop/MACHINE/                                                          │
│  ├─ backend/                      FastAPI Application                        │
│  │  ├─ app/                       Application code                           │
│  │  │  ├─ api/v1/                 API endpoints                              │
│  │  │  │  ├─ nef_certificates.py  NEF certificate endpoints                 │
│  │  │  │  ├─ copilot.py           Employee copilot endpoints                │
│  │  │  │  └─ ...                  Other endpoints                            │
│  │  │  ├─ services/               Business logic                             │
│  │  │  │  ├─ employee_copilot.py  Copilot service                           │
│  │  │  │  ├─ intervention_engine.py Intervention service                    │
│  │  │  │  └─ ...                  Other services                             │
│  │  │  └─ main.py                 Application entry point                    │
│  │  ├─ tests/                     Test suites                                │
│  │  ├─ requirements.txt           Python dependencies                        │
│  │  └─ .env.local                 Environment configuration                  │
│  ├─ vpn/                          VPN Infrastructure                         │
│  │  ├─ scripts/                   Management scripts                         │
│  │  │  ├─ generate-nef-certificate.sh                                       │
│  │  │  ├─ onboard-employee-with-nef.sh                                      │
│  │  │  ├─ batch-generate-nef-certificates.sh                                │
│  │  │  ├─ revoke-employee-cert.sh                                           │
│  │  │  └─ openvpn-setup.sh                                                  │
│  │  ├─ database/                  Database schemas                           │
│  │  │  ├─ schema.sql              VPN infrastructure schema                  │
│  │  │  └─ nef_schema.sql          NEF certificate schema                     │
│  │  └─ docs/                      Documentation                              │
│  ├─ docker-compose.yml            Main services (PostgreSQL, Backend)        │
│  ├─ docker-compose.vpn.yml        VPN services (OpenVPN, Logger)             │
│  └─ .env                          Environment variables                      │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Deployment Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT SEQUENCE FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

START
  │
  ├─► [1] PREREQUISITES CHECK
  │   ├─ Docker installed? ──────────► NO ──► Install Docker
  │   ├─ Docker Compose installed? ──► NO ──► Install Docker Compose
  │   ├─ OpenSSL installed? ─────────► NO ──► Install OpenSSL
  │   └─ Git installed? ─────────────► NO ──► Install Git
  │
  ├─► [2] PROJECT SETUP
  │   ├─ Navigate to ~/Desktop/MACHINE
  │   ├─ Verify directory structure
  │   └─ Check all files present
  │
  ├─► [3] ENVIRONMENT CONFIGURATION
  │   ├─ Create .env file
  │   │   ├─ POSTGRES_USER=tbaps
  │   │   ├─ POSTGRES_PASSWORD=tbaps_secure_password_2026
  │   │   ├─ POSTGRES_DB=tbaps
  │   │   ├─ DATABASE_URL=postgresql://...
  │   │   └─ OPENVPN_SERVER_IP=127.0.0.1
  │   └─ Set permissions: chmod 600 .env
  │
  ├─► [4] DATABASE INITIALIZATION
  │   ├─ Start PostgreSQL container
  │   │   └─ docker-compose up -d postgresql
  │   ├─ Wait 10 seconds for startup
  │   ├─ Test connection
  │   │   └─ docker-compose exec postgresql psql -U tbaps -d tbaps -c "SELECT 1;"
  │   ├─ Load VPN schema
  │   │   └─ docker-compose exec -T postgresql psql -U tbaps -d tbaps < vpn/database/schema.sql
  │   ├─ Load NEF schema
  │   │   └─ docker-compose exec -T postgresql psql -U tbaps -d tbaps < vpn/database/nef_schema.sql
  │   └─ Verify tables created
  │       └─ docker-compose exec postgresql psql -U tbaps -d tbaps -c "\dt"
  │
  ├─► [5] VPN INFRASTRUCTURE SETUP
  │   ├─ Create directory structure
  │   │   ├─ sudo mkdir -p /srv/tbaps/vpn/{ca,certs,configs,config}
  │   │   ├─ sudo mkdir -p /var/log/tbaps
  │   │   └─ sudo chown -R $USER:$USER /srv/tbaps /var/log/tbaps
  │   │
  │   ├─ Generate Certificate Authority
  │   │   ├─ cd /srv/tbaps/vpn/ca
  │   │   ├─ openssl genrsa -out ca.key 2048
  │   │   ├─ openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  │   │   │     -subj "/C=US/ST=State/L=City/O=TBAPS/CN=TBAPS-CA"
  │   │   ├─ chmod 600 ca.key
  │   │   └─ chmod 644 ca.crt
  │   │
  │   ├─ Generate TLS Auth Key
  │   │   ├─ openvpn --genkey --secret /srv/tbaps/vpn/ta.key
  │   │   └─ chmod 600 /srv/tbaps/vpn/ta.key
  │   │
  │   ├─ Configure Server IP
  │   │   └─ echo "127.0.0.1" > /srv/tbaps/vpn/config/server_ip.txt
  │   │
  │   └─ Start VPN Services
  │       ├─ docker-compose -f docker-compose.vpn.yml up -d
  │       └─ Verify: docker-compose -f docker-compose.vpn.yml ps
  │
  ├─► [6] BACKEND API SETUP
  │   ├─ Install Python dependencies
  │   │   ├─ cd ~/Desktop/MACHINE/backend
  │   │   ├─ python3 -m venv venv (optional)
  │   │   ├─ source venv/bin/activate
  │   │   └─ pip install -r requirements.txt
  │   │
  │   ├─ Configure environment
  │   │   └─ cp .env.test .env.local
  │   │
  │   └─ Start backend
  │       ├─ Option A: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  │       └─ Option B: docker-compose up -d backend
  │
  ├─► [7] SYSTEM VERIFICATION
  │   ├─ Check PostgreSQL
  │   │   └─ docker-compose ps postgresql ──► RUNNING ✓
  │   │
  │   ├─ Check OpenVPN
  │   │   └─ docker-compose -f docker-compose.vpn.yml ps openvpn ──► RUNNING ✓
  │   │
  │   ├─ Check VPN Logger
  │   │   └─ docker-compose -f docker-compose.vpn.yml ps vpn-logger ──► RUNNING ✓
  │   │
  │   ├─ Check Backend API
  │   │   └─ curl http://localhost:8000/health ──► {"status":"healthy"} ✓
  │   │
  │   └─ Check Database Tables
  │       └─ docker-compose exec postgresql psql -U tbaps -d tbaps -c "\dt" ──► 10+ tables ✓
  │
  ├─► [8] FUNCTIONAL TESTING
  │   ├─ Test Certificate Generation
  │   │   ├─ cd ~/Desktop/MACHINE/vpn/scripts
  │   │   ├─ ./generate-nef-certificate.sh "Test User" "test@company.com"
  │   │   └─ Verify: ls -lh /srv/tbaps/vpn/configs/test_user.nef ──► EXISTS ✓
  │   │
  │   ├─ Test API Endpoints
  │   │   ├─ curl http://localhost:8000/api/v1/nef/health ──► {"status":"healthy"} ✓
  │   │   ├─ curl http://localhost:8000/api/v1/nef/list?status=active ──► [...] ✓
  │   │   └─ curl http://localhost:8000/api/v1/nef/statistics ──► {...} ✓
  │   │
  │   ├─ Test Employee Onboarding
  │   │   └─ ./onboard-employee-with-nef.sh ──► Interactive ✓
  │   │
  │   └─ Test Batch Generation
  │       ├─ Create test CSV
  │       └─ ./batch-generate-nef-certificates.sh test.csv ──► SUCCESS ✓
  │
  └─► [9] DEPLOYMENT COMPLETE ✓
      │
      ├─ Access Points:
      │   ├─ API: http://localhost:8000
      │   ├─ API Docs: http://localhost:8000/docs
      │   ├─ Database: localhost:5432
      │   └─ VPN: localhost:1194
      │
      └─ Ready for Use! 🎉

END
```

---

## 🎯 Component Dependency Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPONENT DEPENDENCIES                                    │
└─────────────────────────────────────────────────────────────────────────────┘

                        ┌──────────────────┐
                        │   Docker Engine  │
                        └────────┬─────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
          ┌─────────▼─────────┐     ┌────────▼────────┐
          │  Docker Compose   │     │   Docker Images │
          └─────────┬─────────┘     └─────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
┌───────▼──────┐ ┌──▼──────┐ ┌─▼────────────┐
│ PostgreSQL   │ │ OpenVPN │ │ FastAPI      │
│ Container    │ │ Server  │ │ Backend      │
└───────┬──────┘ └──┬──────┘ └─┬────────────┘
        │           │           │
        │           │           │
        │    ┌──────▼──────┐    │
        │    │ VPN Logger  │    │
        │    │  Service    │    │
        │    └──────┬──────┘    │
        │           │           │
        └───────────┼───────────┘
                    │
            ┌───────▼────────┐
            │   File System  │
            ├────────────────┤
            │ /srv/tbaps/    │
            │ /var/log/      │
            │ ~/Desktop/     │
            └────────────────┘

DEPENDENCY CHAIN:

1. Docker Engine (Base requirement)
   └─► Docker Compose
       └─► PostgreSQL Container
           ├─► Database Schemas
           │   ├─► VPN Infrastructure Schema
           │   └─► NEF Certificate Schema
           │
           ├─► OpenVPN Server
           │   ├─► Certificate Authority
           │   ├─► TLS Auth Key
           │   └─► Server Configuration
           │
           ├─► VPN Logger Service
           │   └─► Python Dependencies
           │
           └─► FastAPI Backend
               ├─► Python Dependencies
               ├─► API Endpoints
               └─► Business Services
```

---

## 📋 Pre-Deployment Checklist

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRE-DEPLOYMENT CHECKLIST                                  │
└─────────────────────────────────────────────────────────────────────────────┘

SYSTEM REQUIREMENTS:
  ☐ Operating System: Linux (Ubuntu 20.04+) or macOS
  ☐ CPU: 4+ cores
  ☐ RAM: 8GB minimum (16GB recommended)
  ☐ Disk Space: 20GB free
  ☐ Network: Internet connection

SOFTWARE PREREQUISITES:
  ☐ Docker 20.10+ installed
  ☐ Docker Compose 2.0+ installed
  ☐ Git 2.0+ installed
  ☐ OpenSSL 1.1.1+ installed
  ☐ Bash 4.0+ available
  ☐ Python 3.11+ installed (for backend)
  ☐ curl/wget available

PERMISSIONS:
  ☐ User added to docker group
  ☐ Sudo access available
  ☐ Can create directories in /srv/
  ☐ Can create directories in /var/log/

PROJECT FILES:
  ☐ Project cloned to ~/Desktop/MACHINE
  ☐ All scripts present in vpn/scripts/
  ☐ All schemas present in vpn/database/
  ☐ docker-compose.yml exists
  ☐ docker-compose.vpn.yml exists
  ☐ backend/requirements.txt exists

NETWORK PORTS AVAILABLE:
  ☐ Port 5432 (PostgreSQL)
  ☐ Port 8000 (FastAPI Backend)
  ☐ Port 1194 (OpenVPN Server)

READY TO DEPLOY:
  ☐ All above items checked
  ☐ Deployment guide reviewed
  ☐ Time allocated: 30-45 minutes
```

---

## 🔄 Post-Deployment Verification

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    POST-DEPLOYMENT VERIFICATION                              │
└─────────────────────────────────────────────────────────────────────────────┘

CONTAINER STATUS:
  ☐ PostgreSQL container running
     └─ docker-compose ps postgresql
  ☐ OpenVPN container running
     └─ docker-compose -f docker-compose.vpn.yml ps openvpn
  ☐ VPN Logger container running
     └─ docker-compose -f docker-compose.vpn.yml ps vpn-logger
  ☐ Backend container running (if using Docker)
     └─ docker-compose ps backend

DATABASE VERIFICATION:
  ☐ Can connect to PostgreSQL
     └─ docker-compose exec postgresql psql -U tbaps -d tbaps -c "SELECT 1;"
  ☐ VPN tables created (10+ tables)
     └─ docker-compose exec postgresql psql -U tbaps -d tbaps -c "\dt"
  ☐ Views created (4+ views)
     └─ docker-compose exec postgresql psql -U tbaps -d tbaps -c "\dv"
  ☐ Functions created (5+ functions)
     └─ docker-compose exec postgresql psql -U tbaps -d tbaps -c "\df"

VPN INFRASTRUCTURE:
  ☐ CA certificate exists
     └─ ls -la /srv/tbaps/vpn/ca/ca.crt
  ☐ CA private key exists
     └─ ls -la /srv/tbaps/vpn/ca/ca.key
  ☐ TLS auth key exists
     └─ ls -la /srv/tbaps/vpn/ta.key
  ☐ Server IP configured
     └─ cat /srv/tbaps/vpn/config/server_ip.txt
  ☐ OpenVPN logs show startup
     └─ docker-compose -f docker-compose.vpn.yml logs openvpn | grep "Initialization Sequence Completed"

BACKEND API:
  ☐ Health endpoint responds
     └─ curl http://localhost:8000/health
  ☐ NEF health endpoint responds
     └─ curl http://localhost:8000/api/v1/nef/health
  ☐ API documentation accessible
     └─ curl http://localhost:8000/docs
  ☐ Can list certificates
     └─ curl http://localhost:8000/api/v1/nef/list?status=active

FUNCTIONAL TESTS:
  ☐ Can generate test certificate
     └─ cd vpn/scripts && ./generate-nef-certificate.sh "Test User" "test@company.com"
  ☐ Certificate file created
     └─ ls -lh /srv/tbaps/vpn/configs/test_user.nef
  ☐ Certificate in database
     └─ docker-compose exec postgresql psql -U tbaps -d tbaps -c \
        "SELECT * FROM vpn_certificates WHERE certificate_id='test_user';"
  ☐ Can download via API
     └─ curl -O http://localhost:8000/api/v1/nef/download/test_user

FILE SYSTEM:
  ☐ Log directory writable
     └─ touch /var/log/tbaps/test.log && rm /var/log/tbaps/test.log
  ☐ Config directory writable
     └─ touch /srv/tbaps/vpn/configs/test.txt && rm /srv/tbaps/vpn/configs/test.txt
  ☐ Scripts executable
     └─ ls -la ~/Desktop/MACHINE/vpn/scripts/*.sh | grep "x"

ALL CHECKS PASSED:
  ☐ System fully operational
  ☐ Ready for production use
  ☐ Deployment successful! 🎉
```

---

## 🚀 Quick Command Reference

### Start Everything
```bash
cd ~/Desktop/MACHINE
docker-compose up -d
docker-compose -f docker-compose.vpn.yml up -d
```

### Stop Everything
```bash
cd ~/Desktop/MACHINE
docker-compose down
docker-compose -f docker-compose.vpn.yml down
```

### View Logs
```bash
# PostgreSQL logs
docker-compose logs -f postgresql

# OpenVPN logs
docker-compose -f docker-compose.vpn.yml logs -f openvpn

# VPN Logger logs
docker-compose -f docker-compose.vpn.yml logs -f vpn-logger

# Backend logs
docker-compose logs -f backend
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec postgresql psql -U tbaps -d tbaps

# List tables
docker-compose exec postgresql psql -U tbaps -d tbaps -c "\dt"

# Query certificates
docker-compose exec postgresql psql -U tbaps -d tbaps -c \
  "SELECT * FROM vpn_active_nef_certificates;"
```

### Certificate Management
```bash
cd ~/Desktop/MACHINE/vpn/scripts

# Generate single certificate
./generate-nef-certificate.sh "Employee Name" "email@company.com"

# Onboard employee
./onboard-employee-with-nef.sh

# Batch generation
./batch-generate-nef-certificates.sh employees.csv

# Revoke certificate
./revoke-employee-cert.sh emp-001 "Reason"
```

### API Testing
```bash
# Health check
curl http://localhost:8000/health

# List certificates
curl http://localhost:8000/api/v1/nef/list?status=active

# Get statistics
curl http://localhost:8000/api/v1/nef/statistics

# Generate certificate
curl -X POST http://localhost:8000/api/v1/nef/generate \
  -H "Content-Type: application/json" \
  -d '{"employee_name":"John Doe","employee_email":"john@company.com"}'
```

---

## 📊 Resource Requirements

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RESOURCE ALLOCATION                                       │
└─────────────────────────────────────────────────────────────────────────────┘

CONTAINER RESOURCES:

PostgreSQL:
  ├─ CPU: 1-2 cores
  ├─ RAM: 2-4 GB
  ├─ Disk: 5-10 GB
  └─ Network: Port 5432

OpenVPN Server:
  ├─ CPU: 0.5-1 core
  ├─ RAM: 512 MB - 1 GB
  ├─ Disk: 1 GB
  └─ Network: Port 1194/UDP

VPN Logger:
  ├─ CPU: 0.25 core
  ├─ RAM: 256-512 MB
  ├─ Disk: 500 MB
  └─ Network: Internal only

FastAPI Backend:
  ├─ CPU: 1-2 cores
  ├─ RAM: 1-2 GB
  ├─ Disk: 2 GB
  └─ Network: Port 8000

TOTAL SYSTEM:
  ├─ CPU: 4+ cores recommended
  ├─ RAM: 8 GB minimum, 16 GB recommended
  ├─ Disk: 20 GB free space
  └─ Network: Internet + 3 ports (5432, 8000, 1194)
```

---

**Status:** ✅ DEPLOYMENT MAP COMPLETE  
**Last Updated:** 2026-01-28  
**Version:** 1.0.0

**🎉 Use this map to visualize and deploy TBAPS locally! 🎉**
