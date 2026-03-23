# TBAPS Quick Start Guide

## 🚀 5-Minute Quick Start

### Prerequisites
- Ubuntu 22.04 LTS server
- 16GB RAM, 8 CPU cores, 500GB storage
- Root or sudo access
- Internet connection

### Installation

```bash
# 1. Clone or copy TBAPS to your server
cd /home/kali/Desktop/MACHINE

# 2. Run the automated setup script
sudo ./scripts/quick-setup.sh

# 3. Access the application
https://tbaps.yourcompany.local
```

That's it! The setup script handles everything automatically.

---

## 📋 Manual Installation (Step-by-Step)

### Step 1: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

### Step 2: Create Directory Structure

```bash
# Run the directory setup script
sudo ./scripts/setup-directories.sh
```

Or manually:

```bash
sudo mkdir -p /var/lib/{postgresql,redis,rabbitmq}/tbaps
sudo mkdir -p /srv/tbaps/{prometheus,grafana,openvpn,uploads,reports,ssl}
sudo mkdir -p /srv/backups/{postgres,redis,app,config}
sudo mkdir -p /var/log/tbaps/{postgres,redis,rabbitmq,backend,celery,nginx,prometheus,grafana,openvpn,backup}
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate secure passwords
./scripts/generate-secrets.sh

# Edit .env with your domain
nano .env
```

### Step 4: Generate SSL Certificates

```bash
# Self-signed (for testing)
./scripts/generate-ssl-certs.sh

# Or use Let's Encrypt (for production)
sudo certbot certonly --standalone -d tbaps.yourcompany.com
sudo cp /etc/letsencrypt/live/tbaps.yourcompany.com/* /srv/tbaps/ssl/
```

### Step 5: Deploy Services

```bash
# Start all services
docker compose -f docker-compose.production.yml up -d

# Check status
docker compose -f docker-compose.production.yml ps

# View logs
docker compose -f docker-compose.production.yml logs -f
```

### Step 6: Initialize Database

```bash
# Wait for services to start
sleep 60

# Run migrations
docker compose -f docker-compose.production.yml exec backend python manage.py migrate

# Create admin user
docker compose -f docker-compose.production.yml exec backend python manage.py createsuperuser
```

---

## 🔧 Common Commands

### Service Management

```bash
# Start all services
docker compose -f docker-compose.production.yml up -d

# Stop all services
docker compose -f docker-compose.production.yml down

# Restart a specific service
docker compose -f docker-compose.production.yml restart backend

# View service status
docker compose -f docker-compose.production.yml ps

# View logs (all services)
docker compose -f docker-compose.production.yml logs -f

# View logs (specific service)
docker compose -f docker-compose.production.yml logs -f backend

# Execute command in container
docker compose -f docker-compose.production.yml exec backend bash
```

### Database Operations

```bash
# Access PostgreSQL
docker compose -f docker-compose.production.yml exec postgres psql -U tbaps_user -d tbaps_production

# Backup database
docker compose -f docker-compose.production.yml exec postgres pg_dump -U tbaps_user tbaps_production > backup.sql

# Restore database
cat backup.sql | docker compose -f docker-compose.production.yml exec -T postgres psql -U tbaps_user tbaps_production

# Check database size
docker compose -f docker-compose.production.yml exec postgres psql -U tbaps_user -d tbaps_production -c "SELECT pg_size_pretty(pg_database_size('tbaps_production'));"
```

### Backup & Restore

```bash
# Manual backup
sudo /srv/tbaps/scripts/backup/backup.sh

# Restore from backup
sudo /srv/tbaps/scripts/backup/restore.sh /srv/backups/postgres/tbaps_db_20260125_020000.sql.gz.enc

# List backups
ls -lh /srv/backups/postgres/

# Check backup size
du -sh /srv/backups/
```

### Monitoring

```bash
# Health check
./scripts/monitoring/health-check.sh

# Container resource usage
docker stats

# System resources
htop

# Disk usage
df -h

# Check logs for errors
docker compose -f docker-compose.production.yml logs --tail=100 | grep -i error
```

---

## 🌐 Access Points

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| **Application** | https://tbaps.yourcompany.local | (created during setup) |
| **Grafana** | https://tbaps.yourcompany.local/grafana | admin / (from .env) |
| **RabbitMQ** | http://localhost:15672 | tbaps_admin / (from .env) |
| **Prometheus** | http://localhost:9090 | (no auth) |

---

## 🔒 Security Best Practices

### 1. Change Default Passwords

```bash
# Generate new password
openssl rand -base64 32

# Update .env file
nano .env

# Restart services
docker compose -f docker-compose.production.yml restart
```

### 2. Configure Firewall

```bash
# Enable firewall
sudo ufw enable

# Allow SSH (from internal network only)
sudo ufw allow from 192.168.1.0/24 to any port 22

# Allow HTTPS
sudo ufw allow 443/tcp

# Allow OpenVPN
sudo ufw allow 1194/udp

# Check status
sudo ufw status verbose
```

### 3. Enable Fail2Ban

```bash
# Install
sudo apt install fail2ban -y

# Enable
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check status
sudo fail2ban-client status
```

### 4. SSL/TLS Configuration

```bash
# Test SSL configuration
openssl s_client -connect tbaps.yourcompany.local:443

# Check certificate expiry
openssl x509 -enddate -noout -in /srv/tbaps/ssl/fullchain.pem

# Renew Let's Encrypt certificate
sudo certbot renew
```

---

## 📊 Monitoring & Alerts

### Grafana Dashboards

1. **System Overview**
   - Navigate to https://tbaps.yourcompany.local/grafana
   - Login with admin credentials
   - Import dashboards from Configuration → Data Sources → Prometheus

2. **Key Metrics to Monitor**
   - CPU usage (should be < 70%)
   - Memory usage (should be < 85%)
   - Disk space (should be > 20% free)
   - API response time (should be < 200ms)
   - Error rate (should be < 1%)

### Prometheus Alerts

Check active alerts:
```bash
curl http://localhost:9090/api/v1/alerts | jq
```

### Email Notifications

Configure in `.env`:
```bash
SMTP_HOST=smtp.yourcompany.local
SMTP_PORT=587
SMTP_USER=tbaps@yourcompany.local
SMTP_PASSWORD=your_password
ADMIN_EMAIL=admin@yourcompany.local
```

---

## 🔄 Backup & Recovery

### Automated Backups

Backups run daily at 2 AM automatically. To configure:

```bash
# Edit crontab
crontab -e

# Add backup job (if not already present)
0 2 * * * /srv/tbaps/scripts/backup/backup.sh >> /var/log/tbaps/backup/backup.log 2>&1
```

### Manual Backup

```bash
sudo /srv/tbaps/scripts/backup/backup.sh
```

### Restore from Backup

```bash
# List available backups
ls -lh /srv/backups/postgres/

# Restore specific backup
sudo /srv/tbaps/scripts/backup/restore.sh /srv/backups/postgres/tbaps_db_20260125_020000.sql.gz.enc

# Verify restoration
docker compose -f docker-compose.production.yml exec postgres psql -U tbaps_user -d tbaps_production -c "SELECT COUNT(*) FROM users;"
```

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose -f docker-compose.production.yml logs <service>

# Check if port is in use
sudo netstat -tulpn | grep <port>

# Restart service
docker compose -f docker-compose.production.yml restart <service>

# Rebuild and restart
docker compose -f docker-compose.production.yml up -d --build <service>
```

### Database Connection Errors

```bash
# Check PostgreSQL status
docker compose -f docker-compose.production.yml exec postgres pg_isready

# Check connections
docker compose -f docker-compose.production.yml exec postgres psql -U tbaps_user -c "SELECT count(*) FROM pg_stat_activity;"

# Restart PostgreSQL
docker compose -f docker-compose.production.yml restart postgres
```

### High Memory Usage

```bash
# Check container memory usage
docker stats --no-stream

# Clear Redis cache
docker compose -f docker-compose.production.yml exec redis redis-cli FLUSHDB

# Restart memory-intensive services
docker compose -f docker-compose.production.yml restart backend celery-worker
```

### SSL Certificate Errors

```bash
# Check certificate
openssl x509 -in /srv/tbaps/ssl/fullchain.pem -text -noout

# Regenerate self-signed certificate
./scripts/generate-ssl-certs.sh

# Or renew Let's Encrypt
sudo certbot renew --force-renewal
```

---

## 📈 Scaling

### Horizontal Scaling

To scale backend services:

```bash
# Scale backend to 4 replicas
docker compose -f docker-compose.production.yml up -d --scale backend=4

# Scale Celery workers to 4 replicas
docker compose -f docker-compose.production.yml up -d --scale celery-worker=4
```

### Vertical Scaling

Edit `docker-compose.production.yml` and adjust resource limits:

```yaml
deploy:
  resources:
    limits:
      cpus: '8'
      memory: 16G
```

Then restart:
```bash
docker compose -f docker-compose.production.yml up -d
```

---

## 🔐 VPN Setup

### Generate Client Certificate

```bash
# Generate certificate for new user
docker compose -f docker-compose.production.yml exec openvpn easyrsa build-client-full employee1 nopass

# Export client configuration
docker compose -f docker-compose.production.yml exec openvpn ovpn_getclient employee1 > employee1.ovpn

# Send employee1.ovpn to the user
```

### Revoke Client Certificate

```bash
# Revoke certificate
docker compose -f docker-compose.production.yml exec openvpn easyrsa revoke employee1

# Update CRL
docker compose -f docker-compose.production.yml exec openvpn easyrsa gen-crl

# Restart OpenVPN
docker compose -f docker-compose.production.yml restart openvpn
```

---

## 📞 Support

### Logs Location

```
/var/log/tbaps/
├── postgres/       # PostgreSQL logs
├── redis/          # Redis logs
├── rabbitmq/       # RabbitMQ logs
├── backend/        # Backend API logs
├── celery/         # Celery worker logs
├── nginx/          # Nginx access/error logs
├── prometheus/     # Prometheus logs
├── grafana/        # Grafana logs
├── openvpn/        # OpenVPN logs
└── backup/         # Backup script logs
```

### Health Check

```bash
# Run comprehensive health check
./scripts/monitoring/health-check.sh

# Quick status check
docker compose -f docker-compose.production.yml ps
```

### Get Help

1. Check logs: `docker compose logs <service>`
2. Run health check: `./scripts/monitoring/health-check.sh`
3. Review documentation: `docs/`
4. Contact support: infrastructure@yourcompany.local

---

## 📚 Additional Resources

- [Full Infrastructure Setup Guide](docs/infrastructure-setup.md)
- [Deployment Checklist](docs/deployment-checklist.md)
- [Architecture Documentation](docs/architecture.md)
- [Security Best Practices](docs/security.md)

---

## 🎯 Quick Reference

### Environment Variables
```bash
# View current configuration
cat .env

# Generate new secrets
./scripts/generate-secrets.sh

# Validate configuration
docker compose -f docker-compose.production.yml config
```

### Docker Compose Shortcuts
```bash
# Alias for convenience
alias dc='docker compose -f docker-compose.production.yml'

# Usage
dc ps
dc logs -f
dc restart backend
```

### Performance Tuning
```bash
# Check database performance
docker compose -f docker-compose.production.yml exec postgres psql -U tbaps_user -d tbaps_production -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Check Redis performance
docker compose -f docker-compose.production.yml exec redis redis-cli INFO stats

# Check API performance
curl -w "@curl-format.txt" -o /dev/null -s https://tbaps.yourcompany.local/api/health
```

---

**Last Updated:** 2026-01-25

**Version:** 1.0.0

**Maintained by:** Infrastructure Team
