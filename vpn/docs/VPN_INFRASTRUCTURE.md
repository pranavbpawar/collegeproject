# TBAPS VPN Infrastructure - Complete Documentation

## 📋 Overview

The TBAPS VPN Infrastructure provides secure, self-hosted OpenVPN access for employees with certificate-based authentication, comprehensive logging, and GDPR-compliant audit trails.

**Version:** 1.0.0  
**Date:** 2026-01-28  
**Role:** VPN Infrastructure Engineer

---

## 🎯 Objectives

### Primary Goals
1. **Secure Access** - Certificate-based authentication with AES-256 encryption
2. **Self-Hosted** - Zero dependency on external VPN services
3. **Scalable** - Support for 500+ concurrent employees
4. **Auditable** - Complete access logging and audit trails
5. **GDPR Compliant** - Privacy-first with data retention policies

### Key Features
- ✅ RSA-2048 key exchange
- ✅ AES-256-CBC encryption
- ✅ SHA256 message authentication
- ✅ TLS 1.2+ handshake
- ✅ Automated certificate management
- ✅ Real-time connection monitoring
- ✅ PostgreSQL access logging
- ✅ Certificate revocation on offboarding

---

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     TBAPS VPN Infrastructure                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   OpenVPN    │  │  VPN Logger  │  │  Cert Mgr    │     │
│  │   Server     │  │   Service    │  │   API        │     │
│  │              │  │              │  │              │     │
│  │ Port: 1194   │  │ Monitors     │  │ REST API     │     │
│  │ UDP          │  │ Connections  │  │ Port: 8001   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                  │              │
│         └─────────────────┴──────────────────┘              │
│                           │                                 │
│                  ┌────────▼────────┐                        │
│                  │   PostgreSQL    │                        │
│                  │    Database     │                        │
│                  │                 │                        │
│                  │  - Certificates │                        │
│                  │  - Connections  │                        │
│                  │  - Audit Logs   │                        │
│                  └─────────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack
- **OpenVPN:** kylemanna/openvpn Docker image
- **Database:** PostgreSQL 15+
- **Logger:** Python 3.11 with asyncpg
- **Container:** Docker + Docker Compose
- **Encryption:** AES-256-CBC, SHA256, TLS 1.2+

---

## 🚀 Quick Start

### Prerequisites
```bash
# Required software
- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 15+
- Bash 4.0+
```

### Installation

**1. Initialize Database**
```bash
cd /home/kali/Desktop/MACHINE
docker-compose exec postgresql psql -U tbaps -d tbaps -f vpn/database/schema.sql
```

**2. Setup OpenVPN Server**
```bash
cd vpn/scripts
chmod +x openvpn-setup.sh
./openvpn-setup.sh
```

**3. Start VPN Services**
```bash
docker-compose -f docker-compose.vpn.yml up -d
```

**4. Verify Installation**
```bash
# Check OpenVPN status
docker-compose -f docker-compose.vpn.yml logs openvpn

# Check logger status
docker-compose -f docker-compose.vpn.yml logs vpn-logger

# Verify database
docker-compose exec postgresql psql -U tbaps -d tbaps -c "SELECT * FROM vpn_configuration;"
```

---

## 🔐 Certificate Management

### Certificate Authority (CA)

**CA Certificate Details:**
- Algorithm: RSA-2048
- Validity: 3650 days (10 years)
- Location: `/vpn/certs/ca.crt`

**Server Certificate:**
- Algorithm: RSA-2048
- Validity: 365 days
- Location: `/vpn/certs/issued/server.crt`

### Employee Certificates

**Generate New Certificate:**
```bash
cd vpn/scripts
chmod +x generate-employee-cert.sh
./generate-employee-cert.sh <employee-id> "Employee Name" employee@company.com
```

**Example:**
```bash
./generate-employee-cert.sh emp-001 "John Doe" john.doe@company.com
```

**Output:**
- `.ovpn` file in `vpn/client-configs/`
- Database entry in `vpn_certificates` table
- Audit log entry

### Certificate Revocation

**Revoke Certificate:**
```bash
cd vpn/scripts
chmod +x revoke-employee-cert.sh
./revoke-employee-cert.sh <employee-id> "Reason"
```

**Example:**
```bash
./revoke-employee-cert.sh emp-001 "Employee terminated"
```

**Actions Performed:**
1. Revoke certificate in PKI
2. Regenerate CRL
3. Update database status
4. Terminate active connections
5. Log audit event
6. Restart OpenVPN server

---

## 📊 Database Schema

### Tables

**vpn_certificates**
```sql
- id (UUID, PK)
- employee_id (VARCHAR, UNIQUE)
- employee_name (VARCHAR)
- employee_email (VARCHAR)
- certificate_name (VARCHAR, UNIQUE)
- issued_at (TIMESTAMP)
- expires_at (TIMESTAMP)
- revoked_at (TIMESTAMP)
- status (VARCHAR) -- active, revoked, expired, suspended
```

**vpn_connections**
```sql
- id (UUID, PK)
- employee_id (VARCHAR, FK)
- certificate_name (VARCHAR)
- connected_at (TIMESTAMP)
- disconnected_at (TIMESTAMP)
- client_ip_address (INET)
- vpn_ip_address (INET)
- bytes_received (BIGINT)
- bytes_sent (BIGINT)
- session_duration_seconds (INTEGER)
```

**vpn_audit_log**
```sql
- id (UUID, PK)
- event_type (VARCHAR)
- employee_id (VARCHAR)
- certificate_name (VARCHAR)
- details (JSONB)
- severity (VARCHAR) -- info, warning, error, critical
- source_ip (INET)
- created_at (TIMESTAMP)
```

**vpn_statistics**
```sql
- id (UUID, PK)
- date (DATE)
- hour (INTEGER)
- total_connections (INTEGER)
- unique_users (INTEGER)
- total_bytes_transferred (BIGINT)
- peak_concurrent_connections (INTEGER)
```

### Views

**vpn_active_certificates**
```sql
SELECT employee_id, employee_name, certificate_name, 
       days_until_expiry
FROM vpn_certificates
WHERE status = 'active' AND expires_at > NOW();
```

**vpn_active_connections**
```sql
SELECT employee_id, employee_name, connected_at, 
       client_ip_address, session_duration_seconds
FROM vpn_connections
WHERE disconnected_at IS NULL;
```

---

## 🔧 Configuration

### Server Configuration

**File:** `vpn/config/server.conf`

```conf
# Network
port 1194
proto udp
dev tun

# Encryption
cipher AES-256-CBC
auth SHA256
tls-version-min 1.2

# Network range
server 10.8.0.0 255.255.255.0

# Client settings
max-clients 500
client-to-client
keepalive 10 120

# Security
crl-verify /etc/openvpn/pki/crl.pem
```

### Environment Variables

**docker-compose.vpn.yml:**
```yaml
OPENVPN_SERVER_IP: Your public IP
DATABASE_URL: postgresql://tbaps:password@postgresql:5432/tbaps
LOG_FILE: /var/log/openvpn/openvpn-status.log
POLL_INTERVAL: 30
```

---

## 📈 Monitoring

### Connection Monitoring

**View Active Connections:**
```sql
SELECT * FROM vpn_active_connections;
```

**Connection History:**
```sql
SELECT 
    employee_name,
    connected_at,
    disconnected_at,
    session_duration_seconds / 3600.0 AS hours,
    (bytes_received + bytes_sent) / 1024 / 1024 AS mb_transferred
FROM vpn_connection_history
WHERE connected_at > NOW() - INTERVAL '7 days'
ORDER BY connected_at DESC;
```

### Statistics

**Daily Statistics:**
```sql
SELECT 
    date,
    total_connections,
    unique_users,
    total_bytes_transferred / 1024 / 1024 / 1024 AS gb_transferred,
    peak_concurrent_connections
FROM vpn_statistics
WHERE date > CURRENT_DATE - INTERVAL '30 days'
ORDER BY date DESC;
```

### Audit Logs

**Recent Events:**
```sql
SELECT 
    event_type,
    employee_id,
    certificate_name,
    severity,
    created_at
FROM vpn_audit_log
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

**Certificate Events:**
```sql
SELECT * FROM vpn_audit_log
WHERE event_type IN ('certificate_issued', 'certificate_revoked')
ORDER BY created_at DESC;
```

---

## 🔒 Security

### Encryption Standards

**Symmetric Encryption:**
- Algorithm: AES-256-CBC
- Key Size: 256 bits
- Mode: Cipher Block Chaining

**Message Authentication:**
- Algorithm: SHA256
- HMAC: Yes

**Key Exchange:**
- Algorithm: RSA
- Key Size: 2048 bits
- Diffie-Hellman: 2048 bits

**TLS:**
- Version: 1.2 minimum
- TLS Auth: Enabled
- Direction: 0 (server), 1 (client)

### Access Control

**Certificate-Based:**
- No username/password
- Client certificate required
- Server certificate verification
- CRL checking enabled

**Network:**
- Firewall: UFW recommended
- Port: 1194/UDP only
- Protocol: UDP (TCP fallback available)

### Certificate Rotation

**Automatic Expiration:**
```sql
-- Run daily
SELECT auto_expire_certificates();
```

**Renewal Process:**
1. Generate new certificate 30 days before expiry
2. Send to employee
3. Old certificate auto-revoked after import
4. Audit trail maintained

---

## 📝 GDPR Compliance

### Data Retention

**Connection Logs:**
- Retention: 90 days
- Auto-deletion: Yes
- Purpose: Security auditing

**Audit Logs:**
- Retention: 365 days
- Auto-deletion: Yes
- Purpose: Compliance

**Certificates:**
- Retention: Indefinite (metadata only)
- Revoked certs: Kept for audit
- Private keys: Deleted on revocation

### Data Processing

**Personal Data Collected:**
- Employee ID
- Employee name
- Employee email
- IP addresses
- Connection timestamps
- Traffic statistics

**Legal Basis:**
- Legitimate interest (security)
- Contract (employment)
- Legal obligation (audit)

**Data Subject Rights:**
- Access: Query database
- Rectification: Update records
- Erasure: Anonymize after retention
- Portability: Export available

### Privacy Measures

**Encryption:**
- Data in transit: TLS 1.2+
- Data at rest: PostgreSQL encryption
- Backups: Encrypted

**Access Control:**
- Role-based access
- Audit logging
- Least privilege

---

## 🐛 Troubleshooting

### Server Issues

**OpenVPN won't start:**
```bash
# Check logs
docker-compose -f docker-compose.vpn.yml logs openvpn

# Verify configuration
docker-compose -f docker-compose.vpn.yml exec openvpn cat /etc/openvpn/server.conf

# Check certificates
docker-compose -f docker-compose.vpn.yml exec openvpn ls -la /etc/openvpn/pki/
```

**Clients can't connect:**
```bash
# Check firewall
sudo ufw status
sudo ufw allow 1194/udp

# Verify server is listening
sudo netstat -ulnp | grep 1194

# Check CRL
docker-compose -f docker-compose.vpn.yml exec openvpn cat /etc/openvpn/pki/crl.pem
```

### Certificate Issues

**Certificate generation fails:**
```bash
# Re-initialize PKI
docker-compose -f docker-compose.vpn.yml exec openvpn ovpn_initpki

# Check CA certificate
docker-compose -f docker-compose.vpn.yml exec openvpn cat /etc/openvpn/pki/ca.crt
```

**Revocation not working:**
```bash
# Regenerate CRL
docker-compose -f docker-compose.vpn.yml exec openvpn easyrsa gen-crl

# Restart server
docker-compose -f docker-compose.vpn.yml restart openvpn
```

### Database Issues

**Logger not recording:**
```bash
# Check logger logs
docker-compose -f docker-compose.vpn.yml logs vpn-logger

# Verify database connection
docker-compose exec postgresql psql -U tbaps -d tbaps -c "SELECT COUNT(*) FROM vpn_connections;"

# Check status log
cat vpn/logs/openvpn-status.log
```

---

## 📞 Support

**Documentation:**
- Employee Setup: `vpn/docs/EMPLOYEE_SETUP_INSTRUCTIONS.md`
- Database Schema: `vpn/database/schema.sql`
- Scripts: `vpn/scripts/`

**Logs:**
- OpenVPN: `vpn/logs/openvpn.log`
- Status: `vpn/logs/openvpn-status.log`
- Logger: Docker logs

**Contact:**
- Email: vpn-admin@company.com
- Emergency: +1 (555) 123-9999

---

## 🎉 Summary

The TBAPS VPN Infrastructure provides:

✅ **Self-hosted OpenVPN** with Docker  
✅ **Certificate-based authentication** (RSA-2048)  
✅ **AES-256-CBC encryption** with SHA256 auth  
✅ **Automated certificate management**  
✅ **Real-time connection logging**  
✅ **PostgreSQL audit trails**  
✅ **GDPR-compliant data retention**  
✅ **Support for 500+ employees**  
✅ **Comprehensive monitoring**  

**Status:** ✅ PRODUCTION READY

---

**Delivered By:** VPN Infrastructure Engineer  
**Date:** 2026-01-28  
**Version:** 1.0.0
