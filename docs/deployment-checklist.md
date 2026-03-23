# TBAPS Self-Hosted Deployment Checklist

## Pre-Deployment Checklist

### Hardware Preparation
- [ ] Server hardware meets minimum requirements (16GB RAM, 8 CPU cores, 500GB storage)
- [ ] Ubuntu 22.04 LTS installed and updated
- [ ] Network connectivity verified (1Gbps minimum)
- [ ] UPS connected and tested
- [ ] RAID configured (if applicable)
- [ ] Backup server provisioned (optional but recommended)

### Network Configuration
- [ ] Static IP address assigned (192.168.1.100)
- [ ] DNS records created (tbaps.yourcompany.local, vpn.yourcompany.local)
- [ ] Firewall rules planned
- [ ] VPN network range allocated (10.8.0.0/24)
- [ ] Port forwarding configured (if needed)

### Security Preparation
- [ ] SSH key pairs generated
- [ ] SSL certificates obtained (Let's Encrypt or internal CA)
- [ ] Secure passwords generated for all services
- [ ] Encryption keys generated
- [ ] Security policies documented

---

## Installation Checklist

### Step 1: System Preparation
```bash
# Update system
- [ ] sudo apt update && sudo apt upgrade -y

# Set timezone
- [ ] sudo timedatectl set-timezone America/New_York

# Set hostname
- [ ] sudo hostnamectl set-hostname tbaps-primary

# Create admin user
- [ ] sudo adduser tbaps-admin
- [ ] sudo usermod -aG sudo tbaps-admin
```

### Step 2: Install Dependencies
```bash
# Install required packages
- [ ] sudo apt install -y curl git ufw fail2ban htop vim wget net-tools

# Install Docker
- [ ] curl -fsSL https://get.docker.com | sh
- [ ] sudo usermod -aG docker $USER
- [ ] docker --version

# Install Docker Compose
- [ ] sudo apt install docker-compose-plugin
- [ ] docker compose version
```

### Step 3: Directory Structure
```bash
# Create data directories
- [ ] sudo mkdir -p /var/lib/postgresql/tbaps
- [ ] sudo mkdir -p /var/lib/redis/tbaps
- [ ] sudo mkdir -p /var/lib/rabbitmq/tbaps

# Create application directories
- [ ] sudo mkdir -p /srv/tbaps/{prometheus,grafana,openvpn,uploads,reports,ssl}

# Create backup directories
- [ ] sudo mkdir -p /srv/backups/{postgres,redis,app,config}

# Create log directories
- [ ] sudo mkdir -p /var/log/tbaps/{postgres,redis,rabbitmq,backend,celery,nginx,prometheus,grafana,openvpn,backup}

# Set permissions
- [ ] sudo chown -R 999:999 /var/lib/postgresql/tbaps
- [ ] sudo chown -R 999:999 /var/lib/redis/tbaps
- [ ] sudo chown -R $USER:$USER /srv/tbaps
- [ ] sudo chown -R $USER:$USER /srv/backups
- [ ] sudo chown -R $USER:$USER /var/log/tbaps
```

### Step 4: Security Configuration
```bash
# Configure SSH
- [ ] Disable password authentication
- [ ] Copy SSH public key to server
- [ ] Test SSH key authentication
- [ ] Disable root login

# Configure firewall
- [ ] sudo ufw default deny incoming
- [ ] sudo ufw default allow outgoing
- [ ] sudo ufw allow from 192.168.1.0/24 to any port 22
- [ ] sudo ufw allow 80/tcp
- [ ] sudo ufw allow 443/tcp
- [ ] sudo ufw allow 1194/udp
- [ ] sudo ufw enable

# Configure Fail2Ban
- [ ] sudo systemctl enable fail2ban
- [ ] sudo systemctl start fail2ban
- [ ] sudo fail2ban-client status
```

### Step 5: SSL Certificates
```bash
# Generate self-signed certificates (or use Let's Encrypt)
- [ ] cd /srv/tbaps/ssl
- [ ] openssl genrsa -out privkey.pem 4096
- [ ] openssl req -new -key privkey.pem -out cert.csr
- [ ] openssl x509 -req -days 3650 -in cert.csr -signkey privkey.pem -out fullchain.pem
- [ ] openssl dhparam -out dhparam.pem 2048
- [ ] chmod 600 privkey.pem
- [ ] chmod 644 fullchain.pem dhparam.pem
```

### Step 6: Environment Configuration
```bash
# Create .env file
- [ ] cd /home/kali/Desktop/MACHINE
- [ ] cp .env.example .env
- [ ] Generate secure passwords: openssl rand -base64 32
- [ ] Update POSTGRES_PASSWORD in .env
- [ ] Update REDIS_PASSWORD in .env
- [ ] Update RABBITMQ_PASSWORD in .env
- [ ] Update APP_SECRET_KEY in .env (openssl rand -hex 32)
- [ ] Update JWT_SECRET_KEY in .env (openssl rand -hex 32)
- [ ] Update ENCRYPTION_KEY in .env (openssl rand -base64 32)
- [ ] Update GRAFANA_PASSWORD in .env
- [ ] Update BACKUP_ENCRYPTION_PASSWORD in .env
- [ ] Update DOMAIN in .env
- [ ] chmod 600 .env
```

### Step 7: Deploy Services
```bash
# Pull Docker images
- [ ] docker compose -f docker-compose.production.yml pull

# Start services
- [ ] docker compose -f docker-compose.production.yml up -d

# Check service status
- [ ] docker compose -f docker-compose.production.yml ps

# View logs
- [ ] docker compose -f docker-compose.production.yml logs -f
```

### Step 8: Initialize Application
```bash
# Wait for services to be ready (30-60 seconds)
- [ ] sleep 60

# Run database migrations
- [ ] docker compose -f docker-compose.production.yml exec backend python manage.py migrate

# Create superuser
- [ ] docker compose -f docker-compose.production.yml exec backend python manage.py createsuperuser

# Load initial data (if any)
- [ ] docker compose -f docker-compose.production.yml exec backend python manage.py loaddata initial_data.json
```

### Step 9: Configure OpenVPN
```bash
# Initialize OpenVPN
- [ ] docker compose -f docker-compose.production.yml exec openvpn ovpn_genconfig -u udp://vpn.yourcompany.local
- [ ] docker compose -f docker-compose.production.yml exec openvpn ovpn_initpki

# Generate client certificates
- [ ] docker compose -f docker-compose.production.yml exec openvpn easyrsa build-client-full employee1 nopass
- [ ] docker compose -f docker-compose.production.yml exec openvpn ovpn_getclient employee1 > employee1.ovpn
```

### Step 10: Configure Monitoring
```bash
# Access Grafana
- [ ] Open https://tbaps.yourcompany.local/grafana
- [ ] Login with admin credentials
- [ ] Add Prometheus data source (http://prometheus:9090)
- [ ] Import dashboards from /srv/tbaps/config/grafana/dashboards/

# Verify Prometheus
- [ ] Open http://localhost:9090
- [ ] Check targets are up
- [ ] Verify metrics collection
```

---

## Post-Deployment Checklist

### Verification
- [ ] All Docker containers running
- [ ] PostgreSQL accepting connections
- [ ] Redis responding to ping
- [ ] RabbitMQ management UI accessible
- [ ] Backend API health check passing
- [ ] Frontend loading correctly
- [ ] Nginx reverse proxy working
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards displaying data
- [ ] OpenVPN server running

### Functional Testing
- [ ] User registration works
- [ ] User login works
- [ ] Dashboard loads
- [ ] Data persistence verified
- [ ] API endpoints responding
- [ ] WebSocket connections working
- [ ] File uploads working
- [ ] Report generation working
- [ ] Email notifications working (if configured)

### Performance Testing
- [ ] API response time < 200ms
- [ ] Page load time < 2s
- [ ] Database query performance acceptable
- [ ] Memory usage within limits
- [ ] CPU usage within limits
- [ ] Disk I/O acceptable

### Security Testing
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] SSL certificate valid
- [ ] Firewall rules active
- [ ] Fail2Ban active
- [ ] SSH key authentication only
- [ ] No default passwords in use
- [ ] CORS configured correctly
- [ ] Security headers present
- [ ] Rate limiting working
- [ ] SQL injection protection verified
- [ ] XSS protection verified

### Backup Testing
- [ ] Automated backup script installed
- [ ] Backup cron job configured
- [ ] Manual backup successful
- [ ] Backup encryption working
- [ ] Backup restoration tested
- [ ] Backup retention policy configured
- [ ] Off-site backup configured (optional)

### Monitoring Setup
- [ ] Prometheus alerts configured
- [ ] Grafana dashboards created
- [ ] Email notifications configured
- [ ] Health check script scheduled
- [ ] Log rotation configured
- [ ] Disk space monitoring active

---

## Ongoing Maintenance Checklist

### Daily
- [ ] Check service status: `docker compose ps`
- [ ] Review error logs: `docker compose logs --tail=100`
- [ ] Verify backups completed: `ls -lh /srv/backups/postgres/`
- [ ] Check disk space: `df -h`

### Weekly
- [ ] Run health check: `./scripts/monitoring/health-check.sh`
- [ ] Review Grafana dashboards
- [ ] Check for security alerts
- [ ] Review failed login attempts
- [ ] Check SSL certificate expiry

### Monthly
- [ ] Test backup restoration
- [ ] Review and rotate logs
- [ ] Update system packages: `sudo apt update && sudo apt upgrade`
- [ ] Review user access
- [ ] Check for Docker image updates
- [ ] Review capacity planning metrics

### Quarterly
- [ ] Full disaster recovery drill
- [ ] Security audit
- [ ] Performance review
- [ ] Capacity planning review
- [ ] Update documentation
- [ ] Rotate secrets and passwords

---

## Troubleshooting Checklist

### Service Won't Start
- [ ] Check logs: `docker compose logs <service>`
- [ ] Check disk space: `df -h`
- [ ] Check memory: `free -h`
- [ ] Check port conflicts: `netstat -tulpn`
- [ ] Restart service: `docker compose restart <service>`

### Database Connection Issues
- [ ] Verify PostgreSQL is running: `docker compose ps postgres`
- [ ] Check PostgreSQL logs: `docker compose logs postgres`
- [ ] Test connection: `docker compose exec postgres pg_isready`
- [ ] Check connection count: `docker compose exec postgres psql -U tbaps_user -c "SELECT count(*) FROM pg_stat_activity;"`

### High Resource Usage
- [ ] Check container stats: `docker stats`
- [ ] Identify resource hogs: `docker stats --no-stream`
- [ ] Review application logs for errors
- [ ] Check for memory leaks
- [ ] Consider scaling up resources

### Backup Failures
- [ ] Check backup script logs: `tail -f /var/log/tbaps/backup/backup.log`
- [ ] Verify disk space: `df -h /srv/backups`
- [ ] Test backup script manually: `sudo /srv/tbaps/scripts/backup/backup.sh`
- [ ] Verify encryption password is set

### SSL Certificate Issues
- [ ] Check certificate expiry: `openssl x509 -enddate -noout -in /srv/tbaps/ssl/fullchain.pem`
- [ ] Verify certificate permissions: `ls -l /srv/tbaps/ssl/`
- [ ] Test SSL configuration: `openssl s_client -connect localhost:443`
- [ ] Renew certificate if needed

---

## Emergency Procedures

### Complete System Failure
1. [ ] Assess the situation
2. [ ] Notify stakeholders
3. [ ] Activate backup server (if available)
4. [ ] Restore from latest backup
5. [ ] Verify functionality
6. [ ] Update DNS if needed
7. [ ] Document incident

### Data Corruption
1. [ ] Stop affected services immediately
2. [ ] Identify extent of corruption
3. [ ] Restore from last known good backup
4. [ ] Verify data integrity
5. [ ] Restart services
6. [ ] Monitor for issues
7. [ ] Document incident

### Security Breach
1. [ ] Isolate affected systems
2. [ ] Preserve evidence
3. [ ] Assess scope of breach
4. [ ] Notify security team
5. [ ] Rotate all credentials
6. [ ] Apply security patches
7. [ ] Restore from clean backup
8. [ ] Document incident
9. [ ] Conduct post-mortem

---

## Compliance Checklist

### GDPR Compliance
- [ ] Data encryption at rest
- [ ] Data encryption in transit
- [ ] User consent mechanisms
- [ ] Data export capability
- [ ] Data deletion capability
- [ ] Audit logging enabled
- [ ] Privacy policy documented
- [ ] Data retention policy configured
- [ ] Data processing agreement in place

### Security Compliance
- [ ] Access controls implemented
- [ ] MFA enabled for admins
- [ ] Password policies enforced
- [ ] Session timeout configured
- [ ] Audit logging enabled
- [ ] Security monitoring active
- [ ] Incident response plan documented
- [ ] Regular security audits scheduled

### Operational Compliance
- [ ] Backup policy documented
- [ ] Disaster recovery plan documented
- [ ] Change management process in place
- [ ] Documentation up to date
- [ ] Training materials available
- [ ] Support procedures documented

---

## Sign-Off

### Deployment Team
- [ ] Infrastructure Lead: _________________ Date: _______
- [ ] Security Lead: _________________ Date: _______
- [ ] Application Lead: _________________ Date: _______
- [ ] QA Lead: _________________ Date: _______

### Management Approval
- [ ] IT Manager: _________________ Date: _______
- [ ] Security Manager: _________________ Date: _______
- [ ] Operations Manager: _________________ Date: _______

---

## Notes

Use this space to document any deviations from the standard deployment, issues encountered, or special configurations:

```
[Add deployment notes here]
```

---

**Deployment Completed:** _________________ (Date)

**Production Go-Live:** _________________ (Date)

**Next Review Date:** _________________ (Date)
