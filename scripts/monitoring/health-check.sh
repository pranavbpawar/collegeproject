#!/bin/bash
# TBAPS Health Check Script
# /srv/tbaps/scripts/monitoring/health-check.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="/home/kali/Desktop/MACHINE/docker-compose.production.yml"
FAILED_CHECKS=0

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_failure() {
    echo -e "${RED}✗${NC} $1"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Main health check
print_header "TBAPS Health Check - $(date)"
echo ""

# 1. Docker Services
print_header "Docker Services Status"
if docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null | jq -r '.[] | "\(.Name): \(.State)"' | while read line; do
    service=$(echo "$line" | cut -d: -f1)
    state=$(echo "$line" | cut -d: -f2 | tr -d ' ')
    
    if [ "$state" = "running" ]; then
        print_success "$service is running"
    else
        print_failure "$service is $state"
    fi
done; then
    :
else
    print_failure "Could not check Docker services"
fi
echo ""

# 2. System Resources
print_header "System Resources"

# CPU
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
if (( $(echo "$CPU_USAGE < 80" | bc -l) )); then
    print_success "CPU Usage: ${CPU_USAGE}%"
else
    print_warning "CPU Usage: ${CPU_USAGE}% (High)"
fi

# Memory
MEM_TOTAL=$(free -m | awk 'NR==2{print $2}')
MEM_USED=$(free -m | awk 'NR==2{print $3}')
MEM_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($MEM_USED/$MEM_TOTAL)*100}")

if (( $(echo "$MEM_PERCENT < 85" | bc -l) )); then
    print_success "Memory Usage: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%)"
else
    print_warning "Memory Usage: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%) (High)"
fi

# Disk Space
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}' | cut -d'%' -f1)
if [ "$DISK_USAGE" -lt 80 ]; then
    print_success "Disk Usage: ${DISK_USAGE}%"
else
    print_warning "Disk Usage: ${DISK_USAGE}% (High)"
fi

# Load Average
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | cut -d',' -f1)
print_info "Load Average: $LOAD_AVG"

echo ""

# 3. Network Connectivity
print_header "Network Connectivity"

# Internet
if ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
    print_success "Internet connectivity: OK"
else
    print_warning "Internet connectivity: Failed"
fi

# DNS
if nslookup google.com > /dev/null 2>&1; then
    print_success "DNS resolution: OK"
else
    print_warning "DNS resolution: Failed"
fi

echo ""

# 4. Service Health Checks
print_header "Service Health Checks"

# PostgreSQL
if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U tbaps_user > /dev/null 2>&1; then
    print_success "PostgreSQL: Healthy"
    
    # Check connections
    CONN_COUNT=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U tbaps_user -d tbaps_production -t -c \
        "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tr -d ' ')
    print_info "  Active connections: $CONN_COUNT"
    
    # Check database size
    DB_SIZE=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U tbaps_user -d tbaps_production -t -c \
        "SELECT pg_size_pretty(pg_database_size('tbaps_production'));" 2>/dev/null | tr -d ' ')
    print_info "  Database size: $DB_SIZE"
else
    print_failure "PostgreSQL: Unhealthy"
fi

# Redis
if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
    print_success "Redis: Healthy"
    
    # Check memory usage
    REDIS_MEM=$(docker compose -f "$COMPOSE_FILE" exec -T redis \
        redis-cli info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    print_info "  Memory usage: $REDIS_MEM"
    
    # Check connected clients
    REDIS_CLIENTS=$(docker compose -f "$COMPOSE_FILE" exec -T redis \
        redis-cli info clients | grep connected_clients | cut -d: -f2 | tr -d '\r')
    print_info "  Connected clients: $REDIS_CLIENTS"
else
    print_failure "Redis: Unhealthy"
fi

# RabbitMQ
if docker compose -f "$COMPOSE_FILE" exec -T rabbitmq rabbitmq-diagnostics ping > /dev/null 2>&1; then
    print_success "RabbitMQ: Healthy"
else
    print_failure "RabbitMQ: Unhealthy"
fi

# Backend API
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Backend API: Healthy"
    
    # Check response time
    RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
    print_info "  Response time: ${RESPONSE_TIME}s"
else
    print_failure "Backend API: Unhealthy"
fi

# Nginx
if curl -f -s http://localhost/health > /dev/null 2>&1; then
    print_success "Nginx: Healthy"
else
    print_failure "Nginx: Unhealthy"
fi

# Grafana
if curl -f -s http://localhost:3000/api/health > /dev/null 2>&1; then
    print_success "Grafana: Healthy"
else
    print_failure "Grafana: Unhealthy"
fi

# Prometheus
if curl -f -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    print_success "Prometheus: Healthy"
else
    print_failure "Prometheus: Unhealthy"
fi

echo ""

# 5. Docker Resource Usage
print_header "Docker Container Resources"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | \
    grep -E "tbaps-|NAME" || print_warning "Could not retrieve container stats"

echo ""

# 6. Recent Logs (Errors)
print_header "Recent Error Logs (Last 10 minutes)"

ERROR_COUNT=0
for service in postgres redis rabbitmq backend nginx; do
    ERRORS=$(docker compose -f "$COMPOSE_FILE" logs --since 10m "$service" 2>/dev/null | \
        grep -iE "error|fatal|critical" | wc -l)
    
    if [ "$ERRORS" -gt 0 ]; then
        print_warning "$service: $ERRORS errors found"
        ERROR_COUNT=$((ERROR_COUNT + ERRORS))
    fi
done

if [ "$ERROR_COUNT" -eq 0 ]; then
    print_success "No errors in recent logs"
else
    print_warning "Total errors in last 10 minutes: $ERROR_COUNT"
fi

echo ""

# 7. Backup Status
print_header "Backup Status"

LATEST_BACKUP=$(find /srv/backups/postgres -type f -name "*.enc" -o -name "*.gz" 2>/dev/null | \
    sort -r | head -1)

if [ -n "$LATEST_BACKUP" ]; then
    BACKUP_AGE=$(( ($(date +%s) - $(stat -c %Y "$LATEST_BACKUP")) / 86400 ))
    BACKUP_SIZE=$(du -h "$LATEST_BACKUP" | cut -f1)
    
    if [ "$BACKUP_AGE" -le 1 ]; then
        print_success "Latest backup: $(basename $LATEST_BACKUP) ($BACKUP_SIZE, ${BACKUP_AGE} days old)"
    else
        print_warning "Latest backup: $(basename $LATEST_BACKUP) ($BACKUP_SIZE, ${BACKUP_AGE} days old)"
    fi
else
    print_failure "No backups found!"
fi

echo ""

# 8. SSL Certificate Status
print_header "SSL Certificate Status"

if [ -f "/srv/tbaps/ssl/fullchain.pem" ]; then
    CERT_EXPIRY=$(openssl x509 -enddate -noout -in /srv/tbaps/ssl/fullchain.pem | cut -d= -f2)
    CERT_DAYS=$(( ($(date -d "$CERT_EXPIRY" +%s) - $(date +%s)) / 86400 ))
    
    if [ "$CERT_DAYS" -gt 30 ]; then
        print_success "SSL Certificate valid until: $CERT_EXPIRY ($CERT_DAYS days)"
    elif [ "$CERT_DAYS" -gt 0 ]; then
        print_warning "SSL Certificate expires soon: $CERT_EXPIRY ($CERT_DAYS days)"
    else
        print_failure "SSL Certificate expired: $CERT_EXPIRY"
    fi
else
    print_warning "SSL Certificate not found"
fi

echo ""

# 9. Security Checks
print_header "Security Checks"

# Firewall
if ufw status | grep -q "Status: active"; then
    print_success "Firewall (UFW): Active"
else
    print_failure "Firewall (UFW): Inactive"
fi

# Fail2Ban
if systemctl is-active --quiet fail2ban; then
    print_success "Fail2Ban: Active"
    
    # Check banned IPs
    BANNED_IPS=$(fail2ban-client status sshd 2>/dev/null | grep "Currently banned" | awk '{print $NF}')
    if [ "$BANNED_IPS" -gt 0 ]; then
        print_info "  Banned IPs: $BANNED_IPS"
    fi
else
    print_warning "Fail2Ban: Inactive"
fi

echo ""

# 10. Summary
print_header "Health Check Summary"

if [ $FAILED_CHECKS -eq 0 ]; then
    print_success "All checks passed! System is healthy."
    EXIT_CODE=0
elif [ $FAILED_CHECKS -le 3 ]; then
    print_warning "$FAILED_CHECKS checks failed. System needs attention."
    EXIT_CODE=1
else
    print_failure "$FAILED_CHECKS checks failed. System is unhealthy!"
    EXIT_CODE=2
fi

echo ""
print_info "Health check completed at $(date)"
echo ""

exit $EXIT_CODE
