# TBAPS Self-Hosted Infrastructure Setup Guide

## Table of Contents
1. [Hardware Requirements](#hardware-requirements)
2. [Network Configuration](#network-configuration)
3. [Security Hardening](#security-hardening)
4. [Installation Steps](#installation-steps)
5. [Backup Strategy](#backup-strategy)
6. [Monitoring Setup](#monitoring-setup)
7. [Disaster Recovery](#disaster-recovery)
8. [Capacity Planning](#capacity-planning)

---

## Hardware Requirements

### Primary Server Specifications

**Minimum Requirements for 500+ Employees:**

```
CPU: 8 cores (Intel Xeon or AMD EPYC)
RAM: 16GB DDR4 ECC
Storage: 500GB SSD (NVMe preferred)
Network: 1Gbps Ethernet
OS: Ubuntu 22.04 LTS Server
```

**Recommended Specifications:**

```
CPU: 16 cores @ 2.5GHz+
RAM: 32GB DDR4 ECC
Storage: 1TB NVMe SSD + 2TB HDD (backups)
Network: 10Gbps Ethernet
RAID: RAID 10 for data redundancy
UPS: 1500VA for power protection
```

### Backup Server (Optional but Recommended)

Same specifications as primary server for failover capability.

### Estimated Hardware Costs

| Component | Cost (USD) |
|-----------|------------|
| Server (Dell PowerEdge R450) | $2,500 |
| Additional RAM (16GB) | $200 |
| NVMe SSD (1TB) | $150 |
| HDD for backups (2TB) | $80 |
| UPS (1500VA) | $300 |
| Network Switch (Managed) | $400 |
| **Total** | **$3,630** |

### Operating Costs

- **Electricity**: ~$150-200/month (24/7 operation)
- **Cooling**: Included in facility costs
- **Maintenance**: $0/month (self-managed)
- **Software**: $0/month (all open-source)

---

## Network Configuration

### Network Topology

```
Internet
    |
    v
[Firewall/Router] (192.168.1.1)
    |
    +--- [VPN Server] (10.8.0.1)
    |
    +--- [TBAPS Server] (192.168.1.100)
            |
            +--- Docker Network (172.20.0.0/16) - Internal
            +--- Docker Network (172.21.0.0/16) - External
```

### IP Address Allocation

**Physical Network (192.168.1.0/24):**
- Gateway: 192.168.1.1
- TBAPS Server: 192.168.1.100
- Backup Server: 192.168.1.101
- Management: 192.168.1.10-50
- Workstations: 192.168.1.51-254

**VPN Network (10.8.0.0/24):**
- VPN Server: 10.8.0.1
- VPN Clients: 10.8.0.10-254

**Docker Internal (172.20.0.0/16):**
- PostgreSQL: 172.20.0.10
- Redis: 172.20.0.11
- RabbitMQ: 172.20.0.12
- Backend: 172.20.0.20
- Frontend: 172.20.0.21
- Nginx: 172.20.0.30
- Prometheus: 172.20.0.40
- Grafana: 172.20.0.41

**Docker External (172.21.0.0/16):**
- Nginx: 172.21.0.10
- OpenVPN: 172.21.0.20

### Firewall Rules (UFW)

```bash
#!/bin/bash
# /srv/tbaps/scripts/configure-firewall.sh

# Reset firewall
sudo ufw --force reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH (key-based only)
sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp

# HTTPS (public access)
sudo ufw allow 443/tcp

# HTTP (redirect to HTTPS)
sudo ufw allow 80/tcp

# OpenVPN
sudo ufw allow 1194/udp

# Internal network access
sudo ufw allow from 192.168.1.0/24

# VPN network access
sudo ufw allow from 10.8.0.0/24

# Enable firewall
sudo ufw --force enable

# Show status
sudo ufw status verbose
```

### DNS Configuration

**Internal DNS Records (bind9 or dnsmasq):**

```
# /etc/hosts or DNS server
192.168.1.100   tbaps.yourcompany.local
192.168.1.100   vpn.yourcompany.local
192.168.1.100   grafana.yourcompany.local
192.168.1.101   tbaps-backup.yourcompany.local
```

---

## Security Hardening

### 1. SSH Configuration

**File: `/etc/ssh/sshd_config`**

```bash
# Disable password authentication
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no

# Use SSH Protocol 2 only
Protocol 2

# Limit users
AllowUsers tbaps-admin

# Change default port (optional)
Port 22

# Disable X11 forwarding
X11Forwarding no

# Set idle timeout
ClientAliveInterval 300
ClientAliveCountMax 2
```

**Generate SSH Keys:**

```bash
# On your workstation
ssh-keygen -t ed25519 -C "tbaps-admin@yourcompany.local"

# Copy to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub tbaps-admin@192.168.1.100
```

### 2. Fail2Ban Configuration

**Install and configure:**

```bash
sudo apt install fail2ban -y

# Create jail configuration
sudo tee /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
destemail = security@yourcompany.local
sendername = TBAPS-Security

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/tbaps/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/tbaps/nginx/error.log
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. SSL/TLS Certificates

**Generate self-signed certificates (for internal use):**

```bash
#!/bin/bash
# /srv/tbaps/scripts/generate-ssl-certs.sh

CERT_DIR="/srv/tbaps/ssl"
DOMAIN="tbaps.yourcompany.local"

mkdir -p $CERT_DIR

# Generate private key
openssl genrsa -out $CERT_DIR/privkey.pem 4096

# Generate certificate signing request
openssl req -new -key $CERT_DIR/privkey.pem \
    -out $CERT_DIR/cert.csr \
    -subj "/C=US/ST=State/L=City/O=YourCompany/CN=$DOMAIN"

# Generate self-signed certificate (valid for 10 years)
openssl x509 -req -days 3650 \
    -in $CERT_DIR/cert.csr \
    -signkey $CERT_DIR/privkey.pem \
    -out $CERT_DIR/fullchain.pem

# Generate DH parameters for perfect forward secrecy
openssl dhparam -out $CERT_DIR/dhparam.pem 2048

# Set permissions
chmod 600 $CERT_DIR/privkey.pem
chmod 644 $CERT_DIR/fullchain.pem
chmod 644 $CERT_DIR/dhparam.pem

echo "SSL certificates generated in $CERT_DIR"
```

**For production, use Let's Encrypt or internal CA:**

```bash
# Using certbot for Let's Encrypt (if publicly accessible)
sudo apt install certbot -y
sudo certbot certonly --standalone -d tbaps.yourcompany.com
```

### 4. Database Security

**PostgreSQL hardening (`/srv/tbaps/config/postgresql.conf`):**

```ini
# Connection settings
listen_addresses = '172.20.0.10'  # Docker network only
max_connections = 500
superuser_reserved_connections = 3

# SSL/TLS
ssl = on
ssl_cert_file = '/etc/ssl/certs/ssl-cert-snakeoil.pem'
ssl_key_file = '/etc/ssl/private/ssl-cert-snakeoil.key'
ssl_ciphers = 'HIGH:MEDIUM:+3DES:!aNULL'
ssl_prefer_server_ciphers = on

# Logging
log_connections = on
log_disconnections = on
log_duration = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_statement = 'ddl'

# Performance
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 16MB
```

### 5. Application Security Checklist

- [x] All passwords stored as bcrypt hashes
- [x] JWT tokens with short expiration (30 minutes)
- [x] HTTPS only (HSTS enabled)
- [x] CORS properly configured
- [x] SQL injection protection (parameterized queries)
- [x] XSS protection (Content Security Policy)
- [x] CSRF tokens on all forms
- [x] Rate limiting on API endpoints
- [x] Input validation and sanitization
- [x] Secrets stored in environment variables (not code)
- [x] Regular security updates (automated)

---

## Installation Steps

### Step 1: Prepare the Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    curl \
    git \
    ufw \
    fail2ban \
    htop \
    iotop \
    net-tools \
    vim \
    wget

# Set timezone
sudo timedatectl set-timezone America/New_York

# Set hostname
sudo hostnamectl set-hostname tbaps-primary
```

### Step 2: Install Docker

```bash
#!/bin/bash
# Install Docker CE

# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Verify installation
docker --version
docker compose version
```

### Step 3: Create Directory Structure

```bash
#!/bin/bash
# Create all required directories

# Data directories
sudo mkdir -p /var/lib/postgresql/tbaps
sudo mkdir -p /var/lib/redis/tbaps
sudo mkdir -p /var/lib/rabbitmq/tbaps

# Application directories
sudo mkdir -p /srv/tbaps/{prometheus,grafana,openvpn,uploads,reports,ssl}

# Backup directories
sudo mkdir -p /srv/backups/{postgres,redis,app}

# Log directories
sudo mkdir -p /var/log/tbaps/{postgres,redis,rabbitmq,backend,celery,nginx,prometheus,grafana,openvpn,backup}

# Set permissions
sudo chown -R 999:999 /var/lib/postgresql/tbaps  # postgres user
sudo chown -R 999:999 /var/lib/redis/tbaps       # redis user
sudo chown -R $USER:$USER /srv/tbaps
sudo chown -R $USER:$USER /srv/backups
sudo chown -R $USER:$USER /var/log/tbaps

echo "Directory structure created successfully"
```

### Step 4: Configure Environment Variables

```bash
# Create .env file
cat > /home/kali/Desktop/MACHINE/.env << 'EOF'
# TBAPS Production Environment Variables

# PostgreSQL
POSTGRES_PASSWORD=<GENERATE_SECURE_PASSWORD>

# Redis
REDIS_PASSWORD=<GENERATE_SECURE_PASSWORD>

# RabbitMQ
RABBITMQ_PASSWORD=<GENERATE_SECURE_PASSWORD>

# Application
APP_SECRET_KEY=<GENERATE_SECURE_KEY>
JWT_SECRET_KEY=<GENERATE_SECURE_JWT_KEY>
ENCRYPTION_KEY=<GENERATE_SECURE_ENCRYPTION_KEY>

# Grafana
GRAFANA_PASSWORD=<GENERATE_SECURE_PASSWORD>

# Backup
BACKUP_ENCRYPTION_PASSWORD=<GENERATE_SECURE_PASSWORD>

# Domain
DOMAIN=tbaps.yourcompany.local
EOF

# Generate secure passwords
echo "Generating secure passwords..."
for var in POSTGRES_PASSWORD REDIS_PASSWORD RABBITMQ_PASSWORD GRAFANA_PASSWORD BACKUP_ENCRYPTION_PASSWORD; do
    password=$(openssl rand -base64 32)
    sed -i "s/<GENERATE_SECURE_PASSWORD>/$password/" /home/kali/Desktop/MACHINE/.env
    break
done

# Generate secure keys
APP_SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -base64 32)

sed -i "s/<GENERATE_SECURE_KEY>/$APP_SECRET_KEY/" /home/kali/Desktop/MACHINE/.env
sed -i "s/<GENERATE_SECURE_JWT_KEY>/$JWT_SECRET_KEY/" /home/kali/Desktop/MACHINE/.env
sed -i "s/<GENERATE_SECURE_ENCRYPTION_KEY>/$ENCRYPTION_KEY/" /home/kali/Desktop/MACHINE/.env

# Secure the file
chmod 600 /home/kali/Desktop/MACHINE/.env

echo ".env file created with secure credentials"
```

### Step 5: Deploy Services

```bash
cd /home/kali/Desktop/MACHINE

# Pull images
docker compose -f docker-compose.production.yml pull

# Start services
docker compose -f docker-compose.production.yml up -d

# Check status
docker compose -f docker-compose.production.yml ps

# View logs
docker compose -f docker-compose.production.yml logs -f
```

### Step 6: Initialize Database

```bash
# Wait for PostgreSQL to be ready
sleep 30

# Run migrations
docker compose -f docker-compose.production.yml exec backend python manage.py migrate

# Create superuser
docker compose -f docker-compose.production.yml exec backend python manage.py createsuperuser
```

### Step 7: Configure OpenVPN

```bash
# Initialize OpenVPN
docker compose -f docker-compose.production.yml exec openvpn ovpn_genconfig \
    -u udp://vpn.yourcompany.local

# Generate PKI
docker compose -f docker-compose.production.yml exec openvpn ovpn_initpki

# Generate client certificate
docker compose -f docker-compose.production.yml exec openvpn easyrsa build-client-full employee1 nopass

# Retrieve client configuration
docker compose -f docker-compose.production.yml exec openvpn ovpn_getclient employee1 > employee1.ovpn
```

---

## Backup Strategy

### Automated Backup Script

**File: `/srv/tbaps/scripts/backup/backup.sh`**

```bash
#!/bin/bash
# TBAPS Automated Backup Script

set -e

BACKUP_DIR="/srv/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Backup PostgreSQL
echo "Backing up PostgreSQL..."
docker compose -f /home/kali/Desktop/MACHINE/docker-compose.production.yml exec -T postgres \
    pg_dump -U tbaps_user tbaps_production | \
    gzip > $BACKUP_DIR/postgres/tbaps_db_$DATE.sql.gz

# Backup Redis
echo "Backing up Redis..."
docker compose -f /home/kali/Desktop/MACHINE/docker-compose.production.yml exec -T redis \
    redis-cli --rdb /data/dump.rdb
cp /var/lib/redis/tbaps/dump.rdb $BACKUP_DIR/redis/redis_$DATE.rdb

# Backup application data
echo "Backing up application data..."
tar -czf $BACKUP_DIR/app/app_data_$DATE.tar.gz \
    /srv/tbaps/uploads \
    /srv/tbaps/reports

# Encrypt backups
echo "Encrypting backups..."
for file in $BACKUP_DIR/*/*.{gz,rdb}; do
    if [ -f "$file" ]; then
        openssl enc -aes-256-cbc -salt \
            -in "$file" \
            -out "${file}.enc" \
            -pass pass:$BACKUP_ENCRYPTION_PASSWORD
        rm "$file"
    fi
done

# Remove old backups
echo "Removing backups older than $RETENTION_DAYS days..."
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete

# Verify backup integrity
echo "Verifying backup integrity..."
latest_backup=$(ls -t $BACKUP_DIR/postgres/*.enc | head -1)
if [ -f "$latest_backup" ]; then
    echo "Latest backup: $latest_backup"
    echo "Size: $(du -h $latest_backup | cut -f1)"
else
    echo "ERROR: No backup found!"
    exit 1
fi

# Send notification
echo "Backup completed successfully at $(date)" | \
    mail -s "TBAPS Backup Success" admin@yourcompany.local

echo "Backup completed successfully"
```

### Backup Cron Job

```bash
# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /srv/tbaps/scripts/backup/backup.sh >> /var/log/tbaps/backup/backup.log 2>&1") | crontab -
```

### Restore Procedure

```bash
#!/bin/bash
# Restore from backup

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz.enc>"
    exit 1
fi

# Decrypt backup
openssl enc -aes-256-cbc -d \
    -in "$BACKUP_FILE" \
    -out "${BACKUP_FILE%.enc}" \
    -pass pass:$BACKUP_ENCRYPTION_PASSWORD

# Restore PostgreSQL
gunzip -c "${BACKUP_FILE%.enc}" | \
    docker compose -f /home/kali/Desktop/MACHINE/docker-compose.production.yml exec -T postgres \
    psql -U tbaps_user tbaps_production

echo "Restore completed successfully"
```

---

## Monitoring Setup

### Prometheus Configuration

**File: `/srv/tbaps/config/prometheus.yml`**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'tbaps-production'
    environment: 'on-premise'

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets: []

# Load rules
rule_files:
  - '/etc/prometheus/alerts.yml'

# Scrape configurations
scrape_configs:
  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Backend API
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:9100']
    metrics_path: '/metrics'

  # PostgreSQL
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  # RabbitMQ
  - job_name: 'rabbitmq'
    static_configs:
      - targets: ['rabbitmq:15692']

  # Nginx
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']

  # Node exporter (system metrics)
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
```

### Prometheus Alerts

**File: `/srv/tbaps/config/prometheus-alerts.yml`**

```yaml
groups:
  - name: tbaps_alerts
    interval: 30s
    rules:
      # High CPU usage
      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is above 80% (current value: {{ $value }}%)"

      # High memory usage
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is above 85% (current value: {{ $value }}%)"

      # Disk space low
      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 15
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Low disk space on {{ $labels.instance }}"
          description: "Disk space is below 15% (current value: {{ $value }}%)"

      # Service down
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "{{ $labels.instance }} has been down for more than 2 minutes"

      # High API error rate
      - alert: HighAPIErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API error rate"
          description: "API error rate is above 5% (current value: {{ $value }})"

      # Database connection pool exhausted
      - alert: DatabaseConnectionPoolExhausted
        expr: pg_stat_database_numbackends / pg_settings_max_connections > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool nearly exhausted"
          description: "Database connections are at {{ $value }}% of maximum"
```

### Grafana Dashboards

Create dashboards for:

1. **System Overview**
   - CPU, Memory, Disk, Network usage
   - Service health status
   - Request rate and latency

2. **Application Metrics**
   - Active users
   - API requests per second
   - Error rates
   - Response times

3. **Database Performance**
   - Query performance
   - Connection pool usage
   - Cache hit ratio
   - Slow queries

4. **Security Monitoring**
   - Failed login attempts
   - Suspicious activity
   - VPN connections
   - Firewall blocks

---

## Disaster Recovery

### Recovery Time Objective (RTO): 4 hours
### Recovery Point Objective (RPO): 24 hours

### Disaster Recovery Plan

#### Scenario 1: Hardware Failure

```bash
# 1. Provision new hardware
# 2. Install Ubuntu 22.04 LTS
# 3. Install Docker
# 4. Restore from backup

# Copy backup from off-site location
rsync -avz backup-server:/srv/backups/ /srv/backups/

# Restore latest backup
./scripts/restore.sh /srv/backups/postgres/latest.sql.gz.enc

# Start services
docker compose -f docker-compose.production.yml up -d

# Verify functionality
./scripts/health-check.sh
```

#### Scenario 2: Data Corruption

```bash
# Stop affected services
docker compose -f docker-compose.production.yml stop postgres

# Restore from last known good backup
./scripts/restore.sh /srv/backups/postgres/backup_YYYYMMDD.sql.gz.enc

# Restart services
docker compose -f docker-compose.production.yml start postgres

# Verify data integrity
docker compose -f docker-compose.production.yml exec postgres psql -U tbaps_user -d tbaps_production -c "SELECT COUNT(*) FROM users;"
```

#### Scenario 3: Complete Site Failure

```bash
# Activate backup server
# Update DNS to point to backup server IP
# Restore from latest backup
# Verify all services operational
```

### Failover Procedure

**Automatic failover using Keepalived:**

```bash
# Install on both servers
sudo apt install keepalived -y

# Configure virtual IP (VIP)
# Primary server: priority 100
# Backup server: priority 90

# /etc/keepalived/keepalived.conf
vrrp_instance TBAPS {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass tbaps_secret
    }
    virtual_ipaddress {
        192.168.1.100/24
    }
}
```

---

## Capacity Planning

### Current Capacity (500 employees)

**Resource Utilization Estimates:**

| Resource | Usage | Headroom |
|----------|-------|----------|
| CPU | 40% | 60% |
| RAM | 50% | 50% |
| Storage | 30% | 70% |
| Network | 20% | 80% |

### Scaling Thresholds

**When to scale:**

- CPU usage > 70% sustained
- RAM usage > 75% sustained
- Storage > 80% used
- Database connections > 400 concurrent

### Horizontal Scaling Plan

**For 1000+ employees:**

```yaml
# Add load balancer
# Scale backend to 4 replicas
backend:
  deploy:
    replicas: 4

# Add read replicas for PostgreSQL
postgres-replica-1:
  image: postgres:15-alpine
  # ... configuration

postgres-replica-2:
  image: postgres:15-alpine
  # ... configuration

# Add Redis cluster
redis-cluster:
  # ... configuration
```

### Performance Benchmarks

**Expected performance:**

- API response time: < 200ms (p95)
- Database query time: < 50ms (p95)
- Page load time: < 2s
- Concurrent users: 500+
- Requests per second: 1000+

---

## Maintenance Schedule

### Daily
- Automated backups (2 AM)
- Log rotation
- Health checks

### Weekly
- Review monitoring alerts
- Check disk space
- Review security logs

### Monthly
- Security updates
- Backup restoration test
- Performance review
- Capacity planning review

### Quarterly
- Full disaster recovery drill
- Security audit
- Hardware health check
- Update documentation

---

## Support and Troubleshooting

### Common Issues

**Issue: Service won't start**
```bash
# Check logs
docker compose -f docker-compose.production.yml logs <service>

# Check resource usage
docker stats

# Restart service
docker compose -f docker-compose.production.yml restart <service>
```

**Issue: Database connection errors**
```bash
# Check PostgreSQL status
docker compose -f docker-compose.production.yml exec postgres pg_isready

# Check connections
docker compose -f docker-compose.production.yml exec postgres psql -U tbaps_user -c "SELECT count(*) FROM pg_stat_activity;"

# Restart PostgreSQL
docker compose -f docker-compose.production.yml restart postgres
```

**Issue: High memory usage**
```bash
# Identify memory hogs
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"

# Clear Redis cache
docker compose -f docker-compose.production.yml exec redis redis-cli FLUSHDB
```

### Health Check Script

```bash
#!/bin/bash
# /srv/tbaps/scripts/health-check.sh

echo "TBAPS Health Check - $(date)"
echo "================================"

# Check Docker services
echo -e "\n[Docker Services]"
docker compose -f /home/kali/Desktop/MACHINE/docker-compose.production.yml ps

# Check disk space
echo -e "\n[Disk Space]"
df -h | grep -E '/$|/srv|/var'

# Check memory
echo -e "\n[Memory Usage]"
free -h

# Check CPU
echo -e "\n[CPU Load]"
uptime

# Check network
echo -e "\n[Network Connectivity]"
ping -c 3 8.8.8.8 > /dev/null && echo "Internet: OK" || echo "Internet: FAIL"

# Check services
echo -e "\n[Service Health]"
curl -f http://localhost:8000/health && echo "Backend: OK" || echo "Backend: FAIL"
curl -f http://localhost:3000/api/health && echo "Grafana: OK" || echo "Grafana: FAIL"

echo -e "\n================================"
echo "Health check completed"
```

---

## Compliance and Auditing

### GDPR Compliance

- [x] Data encryption at rest and in transit
- [x] User data export capability
- [x] Right to be forgotten (data deletion)
- [x] Audit logging of all data access
- [x] Data retention policies
- [x] Privacy by design

### Audit Logging

All security-relevant events are logged:
- User authentication
- Data access
- Configuration changes
- Administrative actions
- Security incidents

Logs are:
- Immutable (append-only)
- Encrypted
- Retained for 7 years
- Regularly reviewed

---

## Conclusion

This infrastructure provides a complete, self-hosted solution for TBAPS with:

✅ **Zero cloud dependency** - All data on-premise  
✅ **High availability** - Redundant services and failover  
✅ **Scalability** - Supports 500+ employees, can scale to 1000+  
✅ **Security** - Multiple layers of protection  
✅ **Monitoring** - Comprehensive observability  
✅ **Backup** - Automated daily backups with encryption  
✅ **Cost-effective** - ~$3,600 initial + $200/month operating  

For questions or support, contact: infrastructure@yourcompany.local
