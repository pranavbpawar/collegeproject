# TBAPS NEF Certificate Management - Complete Documentation

## 📋 Overview

The TBAPS NEF Certificate Management System provides automated generation, distribution, and lifecycle management of .nef VPN certificates for remote employee access.

**What is .nef?**
.nef is a custom extension for OpenVPN certificate files specific to TBAPS. Functionally equivalent to .ovpn format but branded for TBAPS usage with embedded certificates and keys.

**Version:** 1.0.0  
**Date:** 2026-01-28  
**Role:** VPN Security and Certificate Management Specialist

---

## 🎯 Objectives

### Primary Goals
1. **Automated Certificate Generation** - On-demand .nef certificate creation
2. **Secure Distribution** - Encrypted delivery to remote employees
3. **Lifecycle Management** - Track issuance, renewal, and revocation
4. **Access Control** - Manage employee VPN access rights
5. **Audit Compliance** - Complete audit trail for all operations

### Key Features
- ✅ Automated .nef certificate generation
- ✅ Employee onboarding with VPN access
- ✅ Batch certificate generation from CSV
- ✅ Certificate revocation and rotation
- ✅ PostgreSQL-backed tracking
- ✅ REST API for programmatic access
- ✅ Comprehensive audit logging
- ✅ AES-256-CBC encryption

---

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│              TBAPS NEF Certificate System                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Generation  │  │  Onboarding  │  │    Batch     │     │
│  │   Scripts    │  │   Scripts    │  │  Generator   │     │
│  │              │  │              │  │              │     │
│  │  .nef files  │  │  Employee +  │  │  CSV → .nef  │     │
│  │              │  │  .nef cert   │  │  Multiple    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                  │              │
│         └─────────────────┴──────────────────┘              │
│                           │                                 │
│                  ┌────────▼────────┐                        │
│                  │   FastAPI       │                        │
│                  │   REST API      │                        │
│                  │                 │                        │
│                  │  - Generate     │                        │
│                  │  - Download     │                        │
│                  │  - Revoke       │                        │
│                  │  - Monitor      │                        │
│                  └────────┬────────┘                        │
│                           │                                 │
│                  ┌────────▼────────┐                        │
│                  │   PostgreSQL    │                        │
│                  │    Database     │                        │
│                  │                 │                        │
│                  │  - Certificates │                        │
│                  │  - Connections  │                        │
│                  │  - Audit Logs   │                        │
│                  │  - Delivery     │                        │
│                  └─────────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
```bash
# Required
- OpenSSL installed
- PostgreSQL 15+ running
- Docker Compose
- Bash 4.0+
- Python 3.11+ (for API)

# Optional
- FastAPI backend (for API access)
```

### Installation

**1. Create Directory Structure**
```bash
mkdir -p /srv/tbaps/vpn/{certificates,certs,configs,ca}
mkdir -p /var/log/tbaps
```

**2. Initialize Database**
```bash
cd /home/kali/Desktop/MACHINE
docker-compose exec postgresql psql -U tbaps -d tbaps -f vpn/database/nef_schema.sql
```

**3. Setup Certificate Authority**
```bash
# Ensure CA is initialized (from previous VPN setup)
# Required files:
# - /srv/tbaps/vpn/ca/ca.crt
# - /srv/tbaps/vpn/ca/ca.key
# - /srv/tbaps/vpn/ta.key
```

**4. Configure Server IP**
```bash
echo "YOUR_VPN_SERVER_IP" > /srv/tbaps/vpn/config/server_ip.txt
```

**5. Verify Installation**
```bash
# Test certificate generation
cd vpn/scripts
./generate-nef-certificate.sh "Test User" "test@company.com"
```

---

## 📝 Usage Guide

### Single Employee Certificate

**Generate .nef Certificate:**
```bash
cd /home/kali/Desktop/MACHINE/vpn/scripts
./generate-nef-certificate.sh "John Doe" "john.doe@company.com"
```

**Output:**
- Certificate file: `/srv/tbaps/vpn/configs/john_doe.nef`
- Database entry created
- Audit log recorded
- Checksum calculated

**What's in the .nef file:**
- VPN server configuration
- Employee information
- Embedded CA certificate
- Embedded client certificate
- Embedded private key
- Embedded TLS auth key

---

### Employee Onboarding

**Interactive Onboarding:**
```bash
cd /home/kali/Desktop/MACHINE/vpn/scripts
./onboard-employee-with-nef.sh
```

**Process:**
1. Collects employee information (name, email, department, role)
2. Creates employee in database
3. Generates .nef VPN certificate
4. Creates welcome email with instructions
5. Logs onboarding event

**Example Session:**
```
Employee Full Name: Jane Smith
Employee Email Address: jane.smith@company.com
Department: Engineering
Job Role: Senior Developer
Manager Name: John Doe

Is this information correct? (yes/no): yes

[1/4] Creating employee in TBAPS database...
✓ Employee created with ID: 550e8400-e29b-41d4-a716-446655440000

[2/4] Generating .nef VPN certificate...
✓ Certificate generated successfully

[3/4] Creating welcome email...
✓ Welcome email created

[4/4] Logging onboarding event...
✓ Onboarding event logged
```

---

### Batch Generation

**Prepare CSV File:**
```csv
name,email,department,role
John Doe,john@company.com,Engineering,Senior Engineer
Jane Smith,jane@company.com,Sales,Sales Manager
Bob Johnson,bob@company.com,IT,System Administrator
```

**Run Batch Generation:**
```bash
cd /home/kali/Desktop/MACHINE/vpn/scripts
./batch-generate-nef-certificates.sh employees.csv
```

**Output:**
- Processes all employees in CSV
- Generates .nef for each
- Creates detailed report
- Logs all operations

**Report Example:**
```
Summary:
  • Total Employees: 3
  • Successfully Generated: 3
  • Failed: 0
  • Skipped: 0
  • Success Rate: 100%

Files:
  • Certificates: /srv/tbaps/vpn/configs/
  • Log File: /var/log/tbaps/batch_nef_generation_20260128_105700.log
  • Report File: /tmp/batch_nef_report_20260128_105700.txt
```

---

## 🔌 API Usage

### Generate Certificate

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/nef/generate \
  -H "Content-Type: application/json" \
  -d '{
    "employee_name": "John Doe",
    "employee_email": "john.doe@company.com",
    "department": "Engineering",
    "role": "Developer"
  }'
```

**Response:**
```json
{
  "status": "success",
  "certificate_id": "john_doe",
  "filename": "john_doe.nef",
  "checksum": "a1b2c3d4e5f6...",
  "generated_at": "2026-01-28T10:57:00",
  "expires_at": "2027-01-28T10:57:00"
}
```

---

### Download Certificate

**Request:**
```bash
curl -O http://localhost:8000/api/v1/nef/download/john_doe
```

**Response:**
- Downloads `john_doe.nef` file
- Increments download counter
- Logs delivery event

---

### Revoke Certificate

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/nef/revoke \
  -H "Content-Type: application/json" \
  -d '{
    "certificate_id": "john_doe",
    "reason": "Employee terminated"
  }'
```

**Response:**
```json
{
  "status": "revoked",
  "certificate_id": "john_doe",
  "reason": "Employee terminated",
  "revoked_at": "2026-01-28T11:00:00"
}
```

---

### List Certificates

**Active Certificates:**
```bash
curl http://localhost:8000/api/v1/nef/list?status=active
```

**All Certificates:**
```bash
curl http://localhost:8000/api/v1/nef/list?status=all&limit=50
```

---

### Get Certificate Status

**Request:**
```bash
curl http://localhost:8000/api/v1/nef/status/john_doe
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "employee_name": "John Doe",
  "employee_email": "john.doe@company.com",
  "certificate_id": "john_doe",
  "issued_at": "2026-01-28T10:57:00",
  "expires_at": "2027-01-28T10:57:00",
  "status": "active",
  "download_count": 3,
  "total_connections": 15,
  "last_connection_at": "2026-01-28T09:30:00"
}
```

---

### Get Expiring Certificates

**Request:**
```bash
curl http://localhost:8000/api/v1/nef/expiring?days=30
```

**Response:**
```json
[
  {
    "employee_name": "Jane Smith",
    "employee_email": "jane@company.com",
    "certificate_id": "jane_smith",
    "expires_at": "2026-02-15T10:00:00",
    "days_remaining": 18
  }
]
```

---

### Get Connection Logs

**All Connections:**
```bash
curl http://localhost:8000/api/v1/nef/connection-logs?limit=100
```

**Specific Certificate:**
```bash
curl http://localhost:8000/api/v1/nef/connection-logs?certificate_id=john_doe
```

---

### Get Statistics

**Request:**
```bash
curl http://localhost:8000/api/v1/nef/statistics
```

**Response:**
```json
{
  "certificates": {
    "active_certificates": 45,
    "revoked_certificates": 5,
    "expired_certificates": 2,
    "total_certificates": 52,
    "total_downloads": 150,
    "total_connections": 1250
  },
  "recent_connections_24h": 38,
  "active_sessions": 12,
  "timestamp": "2026-01-28T11:00:00"
}
```

---

## 🗄️ Database Schema

### Tables

**vpn_certificates**
```sql
- id (UUID, PK)
- employee_id (UUID, FK → employees)
- employee_name (VARCHAR)
- employee_email (VARCHAR)
- certificate_id (VARCHAR, UNIQUE)
- issued_at (TIMESTAMP)
- expires_at (TIMESTAMP)
- revoked_at (TIMESTAMP)
- status (VARCHAR) -- active, revoked, expired, suspended
- config_file (VARCHAR) -- filename.nef
- checksum (VARCHAR) -- SHA256
- download_count (INTEGER)
- last_downloaded_at (TIMESTAMP)
- total_connections (INTEGER)
```

**vpn_connection_logs**
```sql
- id (UUID, PK)
- certificate_id (VARCHAR)
- employee_id (UUID, FK)
- connected_at (TIMESTAMP)
- disconnected_at (TIMESTAMP)
- session_duration (INTERVAL)
- ip_address (INET)
- bytes_sent (BIGINT)
- bytes_received (BIGINT)
- status (VARCHAR)
```

**nef_delivery_audit**
```sql
- id (UUID, PK)
- certificate_id (VARCHAR)
- employee_email (VARCHAR)
- delivery_method (VARCHAR) -- email, api_download, manual
- delivery_date (TIMESTAMP)
- recipient_confirmed (BOOLEAN)
- delivery_status (VARCHAR)
```

---

## 🔒 Security

### Encryption Standards

**Certificate Encryption:**
- Algorithm: AES-256-CBC
- Authentication: SHA256
- TLS Version: 1.2 minimum
- Key Exchange: RSA-2048

**File Security:**
- Permissions: 400 (read-only for owner)
- Storage: Encrypted filesystem recommended
- Transmission: HTTPS/TLS only

### Certificate Lifecycle

**Validity:**
- Default: 365 days
- Auto-expiry: Database function
- Renewal: 30 days before expiration

**Revocation:**
- Immediate effect
- CRL updated
- Active sessions terminated
- Audit logged

---

## 📊 Monitoring

### Certificate Status

**Active Certificates:**
```sql
SELECT * FROM vpn_active_nef_certificates;
```

**Expiring Soon:**
```sql
SELECT * FROM vpn_expiring_nef_certificates;
```

### Connection Monitoring

**Recent Connections:**
```sql
SELECT * FROM vpn_recent_connections LIMIT 50;
```

**Usage Statistics:**
```sql
SELECT * FROM vpn_certificate_usage_stats;
```

---

## 🐛 Troubleshooting

### Certificate Generation Fails

**Check CA Files:**
```bash
ls -la /srv/tbaps/vpn/ca/
# Should see: ca.crt, ca.key
```

**Check Permissions:**
```bash
chmod 600 /srv/tbaps/vpn/ca/ca.key
chmod 644 /srv/tbaps/vpn/ca/ca.crt
```

### Database Connection Issues

**Test Connection:**
```bash
docker-compose exec postgresql psql -U tbaps -d tbaps -c "SELECT COUNT(*) FROM vpn_certificates;"
```

### API Not Working

**Check FastAPI Service:**
```bash
docker-compose logs backend
```

**Test Health Endpoint:**
```bash
curl http://localhost:8000/api/v1/nef/health
```

---

## 📞 Support

**Documentation:**
- NEF System: This file
- VPN Infrastructure: `vpn/docs/VPN_INFRASTRUCTURE.md`
- Employee Setup: `vpn/docs/EMPLOYEE_SETUP_INSTRUCTIONS.md`

**Logs:**
- Generation: `/var/log/tbaps/nef_generation.log`
- Batch: `/var/log/tbaps/batch_nef_generation_*.log`
- API: Docker logs

**Contact:**
- Email: vpn-support@company.com
- Emergency: +1 (555) 123-9999

---

## 🎉 Summary

The TBAPS NEF Certificate Management System provides:

✅ **Automated .nef generation** with OpenSSL  
✅ **Employee onboarding** with VPN access  
✅ **Batch processing** from CSV files  
✅ **REST API** for programmatic access  
✅ **PostgreSQL tracking** with audit trails  
✅ **Secure distribution** with checksums  
✅ **Lifecycle management** (issue, renew, revoke)  
✅ **AES-256-CBC encryption**  

**Status:** ✅ PRODUCTION READY

---

**Delivered By:** VPN Security and Certificate Management Specialist  
**Date:** 2026-01-28  
**Version:** 1.0.0
