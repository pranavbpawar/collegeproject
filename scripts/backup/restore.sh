#!/bin/bash
# TBAPS Restore Script
# /srv/tbaps/scripts/backup/restore.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file> [component]"
    echo ""
    echo "Components:"
    echo "  postgres  - Restore PostgreSQL database only"
    echo "  redis     - Restore Redis data only"
    echo "  app       - Restore application data only"
    echo "  all       - Restore everything (default)"
    echo ""
    echo "Example:"
    echo "  $0 /srv/backups/postgres/tbaps_db_20260125_020000.sql.gz.enc"
    echo "  $0 /srv/backups/postgres/tbaps_db_20260125_020000.sql.gz.enc postgres"
    exit 1
fi

BACKUP_FILE="$1"
COMPONENT="${2:-all}"
COMPOSE_FILE="/home/kali/Desktop/MACHINE/docker-compose.production.yml"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    error "Please run as root or with sudo"
    exit 1
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

log "========================================="
log "TBAPS Restore Process"
log "========================================="
log "Backup file: $BACKUP_FILE"
log "Component: $COMPONENT"
log ""

# Confirm restore
read -p "This will OVERWRITE existing data. Are you sure? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    log "Restore cancelled"
    exit 0
fi

# Decrypt if encrypted
TEMP_FILE="$BACKUP_FILE"
if [[ "$BACKUP_FILE" =~ \.enc$ ]]; then
    log "Decrypting backup..."
    if [ -z "${BACKUP_ENCRYPTION_PASSWORD:-}" ]; then
        read -sp "Enter backup encryption password: " BACKUP_ENCRYPTION_PASSWORD
        echo ""
    fi
    
    TEMP_FILE="${BACKUP_FILE%.enc}"
    if openssl enc -aes-256-cbc -d -pbkdf2 \
        -in "$BACKUP_FILE" \
        -out "$TEMP_FILE" \
        -pass pass:"$BACKUP_ENCRYPTION_PASSWORD"; then
        log "Decryption successful"
    else
        error "Decryption failed!"
        exit 1
    fi
fi

# Restore PostgreSQL
if [ "$COMPONENT" = "postgres" ] || [ "$COMPONENT" = "all" ]; then
    log "Restoring PostgreSQL database..."
    
    # Stop dependent services
    log "Stopping backend services..."
    docker compose -f "$COMPOSE_FILE" stop backend celery-worker
    
    # Drop existing connections
    docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U tbaps_user -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'tbaps_production' AND pid <> pg_backend_pid();"
    
    # Drop and recreate database
    docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U tbaps_user -d postgres -c \
        "DROP DATABASE IF EXISTS tbaps_production;"
    docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U tbaps_user -d postgres -c \
        "CREATE DATABASE tbaps_production OWNER tbaps_user;"
    
    # Restore from backup
    if gunzip -c "$TEMP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U tbaps_user tbaps_production; then
        log "PostgreSQL restore completed successfully"
    else
        error "PostgreSQL restore failed!"
        exit 1
    fi
    
    # Restart services
    log "Restarting backend services..."
    docker compose -f "$COMPOSE_FILE" start backend celery-worker
fi

# Restore Redis
if [ "$COMPONENT" = "redis" ] || [ "$COMPONENT" = "all" ]; then
    if [[ "$TEMP_FILE" =~ \.rdb$ ]]; then
        log "Restoring Redis data..."
        
        # Stop Redis
        docker compose -f "$COMPOSE_FILE" stop redis
        
        # Replace dump file
        cp "$TEMP_FILE" /var/lib/redis/tbaps/dump.rdb
        chown 999:999 /var/lib/redis/tbaps/dump.rdb
        
        # Start Redis
        docker compose -f "$COMPOSE_FILE" start redis
        
        log "Redis restore completed successfully"
    fi
fi

# Restore application data
if [ "$COMPONENT" = "app" ] || [ "$COMPONENT" = "all" ]; then
    if [[ "$TEMP_FILE" =~ \.tar\.gz$ ]]; then
        log "Restoring application data..."
        
        # Extract to temporary location
        TEMP_DIR=$(mktemp -d)
        tar -xzf "$TEMP_FILE" -C "$TEMP_DIR"
        
        # Backup current data
        if [ -d "/srv/tbaps/uploads" ]; then
            mv /srv/tbaps/uploads /srv/tbaps/uploads.backup.$(date +%s)
        fi
        if [ -d "/srv/tbaps/reports" ]; then
            mv /srv/tbaps/reports /srv/tbaps/reports.backup.$(date +%s)
        fi
        
        # Restore from backup
        mv "$TEMP_DIR/uploads" /srv/tbaps/
        mv "$TEMP_DIR/reports" /srv/tbaps/
        
        # Set permissions
        chown -R 1000:1000 /srv/tbaps/uploads /srv/tbaps/reports
        
        # Cleanup
        rm -rf "$TEMP_DIR"
        
        log "Application data restore completed successfully"
    fi
fi

# Cleanup temporary files
if [ "$TEMP_FILE" != "$BACKUP_FILE" ]; then
    rm -f "$TEMP_FILE"
fi

# Verify restore
log "Verifying restore..."

if [ "$COMPONENT" = "postgres" ] || [ "$COMPONENT" = "all" ]; then
    # Check database
    USER_COUNT=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U tbaps_user -d tbaps_production -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
    
    if [ -n "$USER_COUNT" ] && [ "$USER_COUNT" -gt 0 ]; then
        log "Database verification: OK ($USER_COUNT users found)"
    else
        warning "Database verification: Could not verify user count"
    fi
fi

if [ "$COMPONENT" = "redis" ] || [ "$COMPONENT" = "all" ]; then
    # Check Redis
    if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
        log "Redis verification: OK"
    else
        warning "Redis verification: Failed"
    fi
fi

log "========================================="
log "Restore Completed Successfully"
log "========================================="
log ""
log "Next steps:"
log "1. Verify application functionality"
log "2. Check logs for any errors"
log "3. Test user login and core features"
log "4. Monitor system performance"

exit 0
