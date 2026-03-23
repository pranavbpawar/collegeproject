#!/bin/bash
# TBAPS Automated Backup Script
# /srv/tbaps/scripts/backup/backup.sh

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/srv/backups}"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"
COMPOSE_FILE="/home/kali/Desktop/MACHINE/docker-compose.production.yml"
LOG_FILE="/var/log/tbaps/backup/backup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    error "Please run as root or with sudo"
    exit 1
fi

# Create backup directories if they don't exist
mkdir -p "$BACKUP_DIR"/{postgres,redis,app,config}

log "========================================="
log "TBAPS Backup Started"
log "========================================="

# 1. Backup PostgreSQL
log "Backing up PostgreSQL database..."
if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U tbaps_user tbaps_production | \
    gzip > "$BACKUP_DIR/postgres/tbaps_db_$DATE.sql.gz"; then
    log "PostgreSQL backup completed: tbaps_db_$DATE.sql.gz"
    POSTGRES_SIZE=$(du -h "$BACKUP_DIR/postgres/tbaps_db_$DATE.sql.gz" | cut -f1)
    log "PostgreSQL backup size: $POSTGRES_SIZE"
else
    error "PostgreSQL backup failed!"
    exit 1
fi

# 2. Backup Redis
log "Backing up Redis data..."
if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" SAVE > /dev/null 2>&1; then
    sleep 2
    if [ -f "/var/lib/redis/tbaps/dump.rdb" ]; then
        cp /var/lib/redis/tbaps/dump.rdb "$BACKUP_DIR/redis/redis_$DATE.rdb"
        log "Redis backup completed: redis_$DATE.rdb"
        REDIS_SIZE=$(du -h "$BACKUP_DIR/redis/redis_$DATE.rdb" | cut -f1)
        log "Redis backup size: $REDIS_SIZE"
    else
        warning "Redis dump file not found, skipping..."
    fi
else
    warning "Redis backup failed, continuing..."
fi

# 3. Backup RabbitMQ definitions
log "Backing up RabbitMQ definitions..."
if docker compose -f "$COMPOSE_FILE" exec -T rabbitmq rabbitmqadmin export "$BACKUP_DIR/rabbitmq_$DATE.json" > /dev/null 2>&1; then
    log "RabbitMQ backup completed: rabbitmq_$DATE.json"
else
    warning "RabbitMQ backup failed, continuing..."
fi

# 4. Backup application data
log "Backing up application data..."
if tar -czf "$BACKUP_DIR/app/app_data_$DATE.tar.gz" \
    -C /srv/tbaps uploads reports 2>/dev/null; then
    log "Application data backup completed: app_data_$DATE.tar.gz"
    APP_SIZE=$(du -h "$BACKUP_DIR/app/app_data_$DATE.tar.gz" | cut -f1)
    log "Application data size: $APP_SIZE"
else
    warning "Application data backup failed, continuing..."
fi

# 5. Backup configuration files
log "Backing up configuration files..."
if tar -czf "$BACKUP_DIR/config/config_$DATE.tar.gz" \
    -C /home/kali/Desktop/MACHINE config .env 2>/dev/null; then
    log "Configuration backup completed: config_$DATE.tar.gz"
else
    warning "Configuration backup failed, continuing..."
fi

# 6. Encrypt backups
log "Encrypting backups..."
if [ -n "${BACKUP_ENCRYPTION_PASSWORD:-}" ]; then
    for dir in postgres redis app config; do
        for file in "$BACKUP_DIR/$dir"/*_$DATE.*; do
            if [ -f "$file" ] && [[ ! "$file" =~ \.enc$ ]]; then
                if openssl enc -aes-256-cbc -salt -pbkdf2 \
                    -in "$file" \
                    -out "${file}.enc" \
                    -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" 2>/dev/null; then
                    rm "$file"
                    log "Encrypted: $(basename ${file}.enc)"
                else
                    error "Failed to encrypt: $(basename $file)"
                fi
            fi
        done
    done
else
    warning "BACKUP_ENCRYPTION_PASSWORD not set, skipping encryption"
fi

# 7. Create backup manifest
log "Creating backup manifest..."
cat > "$BACKUP_DIR/manifest_$DATE.txt" << EOF
TBAPS Backup Manifest
=====================
Date: $(date)
Hostname: $(hostname)
Backup ID: $DATE

Files:
$(find "$BACKUP_DIR" -type f -name "*_$DATE.*" -exec ls -lh {} \; | awk '{print $9, $5}')

Total Size: $(du -sh "$BACKUP_DIR" | cut -f1)

Checksums (SHA256):
$(find "$BACKUP_DIR" -type f -name "*_$DATE.*" -exec sha256sum {} \;)
EOF

log "Backup manifest created: manifest_$DATE.txt"

# 8. Remove old backups
log "Removing backups older than $RETENTION_DAYS days..."
DELETED_COUNT=0
for dir in postgres redis app config; do
    DELETED=$(find "$BACKUP_DIR/$dir" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)
    DELETED_COUNT=$((DELETED_COUNT + DELETED))
done

if [ $DELETED_COUNT -gt 0 ]; then
    log "Removed $DELETED_COUNT old backup files"
else
    log "No old backups to remove"
fi

# 9. Verify backup integrity
log "Verifying backup integrity..."
LATEST_BACKUP=$(ls -t "$BACKUP_DIR/postgres"/*_$DATE.*.enc 2>/dev/null | head -1)
if [ -f "$LATEST_BACKUP" ]; then
    BACKUP_SIZE=$(du -h "$LATEST_BACKUP" | cut -f1)
    log "Latest backup verified: $(basename $LATEST_BACKUP) ($BACKUP_SIZE)"
    
    # Test decryption
    if [ -n "${BACKUP_ENCRYPTION_PASSWORD:-}" ]; then
        if openssl enc -aes-256-cbc -d -pbkdf2 \
            -in "$LATEST_BACKUP" \
            -pass pass:"$BACKUP_ENCRYPTION_PASSWORD" 2>/dev/null | gzip -t 2>/dev/null; then
            log "Backup integrity verified successfully"
        else
            error "Backup integrity check failed!"
            exit 1
        fi
    fi
else
    error "No backup found for verification!"
    exit 1
fi

# 10. Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Total backup size: $TOTAL_SIZE"

# 11. Optional: Copy to off-site location (NAS, external drive)
if [ -n "${OFFSITE_BACKUP_PATH:-}" ] && [ -d "$OFFSITE_BACKUP_PATH" ]; then
    log "Copying backups to off-site location..."
    if rsync -az --progress "$BACKUP_DIR/" "$OFFSITE_BACKUP_PATH/" >> "$LOG_FILE" 2>&1; then
        log "Off-site backup completed successfully"
    else
        warning "Off-site backup failed"
    fi
fi

# 12. Send notification
log "========================================="
log "TBAPS Backup Completed Successfully"
log "========================================="

# Send email notification (if mail is configured)
if command -v mail &> /dev/null; then
    {
        echo "TBAPS Backup Report"
        echo "==================="
        echo ""
        echo "Date: $(date)"
        echo "Status: SUCCESS"
        echo "Backup ID: $DATE"
        echo "Total Size: $TOTAL_SIZE"
        echo ""
        echo "Backed up:"
        echo "  - PostgreSQL database"
        echo "  - Redis data"
        echo "  - Application data"
        echo "  - Configuration files"
        echo ""
        echo "Retention: $RETENTION_DAYS days"
        echo "Deleted old backups: $DELETED_COUNT files"
        echo ""
        echo "Location: $BACKUP_DIR"
        echo ""
        echo "Full log: $LOG_FILE"
    } | mail -s "TBAPS Backup Success - $DATE" admin@yourcompany.local
fi

# Exit successfully
exit 0
