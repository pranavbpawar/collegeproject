#!/usr/bin/env bash
# ==============================================================================
# TBAPS Native Service Installer
# Installs TBAPS as native Linux systemd services (no Docker).
# Run as root: sudo bash scripts/install-services.sh
# ==============================================================================

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────────
TBAPS_USER="tbaps"
TBAPS_GROUP="tbaps"
INSTALL_DIR="/opt/tbaps"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="/var/log/tbaps"
RUN_DIR="/var/run/tbaps"
SYSTEMD_DIR="/etc/systemd/system"
# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# Auto-detect Python 3 (prefer 3.11, fall back to 3.13, 3.12, or python3)
if   command -v python3.11 &>/dev/null; then PYTHON_BIN="python3.11"
elif command -v python3.13 &>/dev/null; then PYTHON_BIN="python3.13"
elif command -v python3.12 &>/dev/null; then PYTHON_BIN="python3.12"
elif command -v python3    &>/dev/null; then PYTHON_BIN="python3"
else error "No Python 3 interpreter found. Install python3."; fi

# ── Checks ─────────────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "This script must be run as root (sudo)."
command -v nginx &>/dev/null || warn "Nginx not found — install it for frontend serving."

info "Python: $PYTHON_BIN ($($PYTHON_BIN --version 2>&1))"

info "Installing TBAPS from: $PROJECT_DIR"
info "Target directory:      $INSTALL_DIR"

# ── Create system user ─────────────────────────────────────────────────────────
if ! id "$TBAPS_USER" &>/dev/null; then
    info "Creating system user: $TBAPS_USER"
    useradd --system --no-create-home --shell /usr/sbin/nologin \
            --comment "TBAPS Service Account" "$TBAPS_USER"
else
    info "User $TBAPS_USER already exists — skipping."
fi

# ── Create directories ─────────────────────────────────────────────────────────
info "Creating directories..."
mkdir -p "$INSTALL_DIR"/{backend,vpn/traffic-monitor,frontend}
mkdir -p "$LOG_DIR"
mkdir -p "$RUN_DIR"

# ── Copy project files ─────────────────────────────────────────────────────────
info "Copying project files..."
rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
         --exclude='venv' --exclude='.env' --exclude='node_modules' \
         "$PROJECT_DIR/backend/"              "$INSTALL_DIR/backend/"
rsync -a "$PROJECT_DIR/vpn/traffic-monitor/"  "$INSTALL_DIR/vpn/traffic-monitor/"
rsync -a "$PROJECT_DIR/scripts/"              "$INSTALL_DIR/scripts/"

# Copy .env if it exists, otherwise copy .env.example
if [[ -f "$PROJECT_DIR/.env" ]]; then
    cp "$PROJECT_DIR/.env" "$INSTALL_DIR/.env"
    chmod 640 "$INSTALL_DIR/.env"
    info "Copied .env to $INSTALL_DIR/.env"
else
    cp "$PROJECT_DIR/.env.example" "$INSTALL_DIR/.env"
    chmod 640 "$INSTALL_DIR/.env"
    warn ".env not found — copied .env.example. Edit $INSTALL_DIR/.env before starting services!"
fi

# ── Create Python virtual environment (backend) ────────────────────────────────
info "Creating Python venv for backend..."
if [[ ! -d "$INSTALL_DIR/venv" ]]; then
    "$PYTHON_BIN" -m venv "$INSTALL_DIR/venv"
fi
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip setuptools wheel -q
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/backend/requirements.txt" -q
info "Backend dependencies installed."

# ── Create Python virtual environment (traffic monitor) ───────────────────────
info "Creating Python venv for traffic monitor..."
if [[ ! -d "$INSTALL_DIR/traffic-venv" ]]; then
    "$PYTHON_BIN" -m venv "$INSTALL_DIR/traffic-venv"
fi
if [[ -f "$INSTALL_DIR/vpn/traffic-monitor/requirements.txt" ]]; then
    "$INSTALL_DIR/traffic-venv/bin/pip" install --upgrade pip -q
    "$INSTALL_DIR/traffic-venv/bin/pip" install \
        -r "$INSTALL_DIR/vpn/traffic-monitor/requirements.txt" -q
    info "Traffic monitor dependencies installed."
fi

# ── Set permissions ────────────────────────────────────────────────────────────
info "Setting permissions..."
chown -R "$TBAPS_USER:$TBAPS_GROUP" "$INSTALL_DIR"
chown -R "$TBAPS_USER:$TBAPS_GROUP" "$LOG_DIR"
chown -R "$TBAPS_USER:$TBAPS_GROUP" "$RUN_DIR"
# .env must not be world-readable
chmod 640 "$INSTALL_DIR/.env"
# Packet capture venv stays root-owned (service runs as root)
chown -R root:root "$INSTALL_DIR/traffic-venv"

# ── Install systemd services ───────────────────────────────────────────────────
info "Installing systemd services..."
for svc in tbaps-api tbaps-worker tbaps-capture; do
    src="$PROJECT_DIR/systemd/${svc}.service"
    dst="$SYSTEMD_DIR/${svc}.service"
    if [[ -f "$src" ]]; then
        cp "$src" "$dst"
        chmod 644 "$dst"
        info "  Installed $dst"
    else
        warn "  Service file not found: $src — skipping."
    fi
done

systemctl daemon-reload
info "systemd daemon reloaded."

# ── Enable services (but don't start yet) ─────────────────────────────────────
systemctl enable tbaps-api tbaps-worker tbaps-capture 2>/dev/null || true
info "Services enabled for auto-start on boot."

# ── Install Nginx config ───────────────────────────────────────────────────────
if command -v nginx &>/dev/null && [[ -f "$PROJECT_DIR/nginx/tbaps.conf" ]]; then
    cp "$PROJECT_DIR/nginx/tbaps.conf" /etc/nginx/sites-available/tbaps.conf
    ln -sf /etc/nginx/sites-available/tbaps.conf /etc/nginx/sites-enabled/tbaps.conf
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && info "Nginx config installed and validated." || warn "Nginx config test failed — check /etc/nginx/sites-available/tbaps.conf"
fi

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  TBAPS Installation Complete!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo ""
echo "  Next steps:"
echo "  1. Edit /opt/tbaps/.env with your secrets"
echo "  2. Initialize the database:"
echo "       psql -U ztuser -d zerotrust -h localhost -f /opt/tbaps/scripts/init_schema.sql"
echo "  3. Build the frontend:"
echo "       bash $PROJECT_DIR/scripts/build-frontend.sh"
echo "  4. Start services:"
echo "       sudo systemctl start tbaps-api tbaps-worker tbaps-capture"
echo "  5. Check health:"
echo "       curl http://localhost:8000/health"
echo ""
