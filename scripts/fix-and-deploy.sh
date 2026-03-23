#!/usr/bin/env bash
# ==============================================================================
# TBAPS Complete Fix & Deploy Script
# Run: sudo bash /home/kali/Desktop/MACHINE/scripts/fix-and-deploy.sh
# ==============================================================================

set -e
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
step() { echo -e "\n${GREEN}══ $* ${NC}"; }

PROJECT_DIR="/home/kali/Desktop/MACHINE"
INSTALL_DIR="/opt/tbaps"

# ── 1. Stop any old processes ─────────────────────────────────────────────────
step "1. Stopping old services"
systemctl stop tbaps-api 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
ok "Cleared port 8000"

# ── 2. Symlink .env so backend finds it ───────────────────────────────────────
step "2. Linking .env"
ln -sf "$PROJECT_DIR/.env" "$PROJECT_DIR/backend/.env"
ok ".env linked"

# ── 3. Sync latest backend code to /opt/tbaps ────────────────────────────────
step "3. Syncing backend to /opt/tbaps"
mkdir -p "$INSTALL_DIR/backend"
rsync -a --exclude='__pycache__' --exclude='*.pyc' \
    "$PROJECT_DIR/backend/" "$INSTALL_DIR/backend/"
cp "$PROJECT_DIR/.env" "$INSTALL_DIR/.env"
# Make the venv accessible
if [[ -d /venv ]]; then
    VENV=/venv
else
    VENV="$INSTALL_DIR/venv"
    [[ -d $VENV ]] || python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade pip
    "$VENV/bin/pip" install -q -r "$INSTALL_DIR/backend/requirements.txt"
fi
ok "Backend synced"

# ── 4. Build frontend ─────────────────────────────────────────────────────────
step "4. Building frontend"
cd "$PROJECT_DIR/frontend"
npm install --silent 2>/dev/null
npm run build
ok "Frontend built"

# ── 5. Deploy frontend to nginx root ─────────────────────────────────────────
step "5. Deploying frontend"
mkdir -p "$INSTALL_DIR/frontend/dist"
cp -r "$PROJECT_DIR/frontend/dist/." "$INSTALL_DIR/frontend/dist/"
ok "Frontend deployed to $INSTALL_DIR/frontend/dist"

# ── 6. Install nginx config ───────────────────────────────────────────────────
step "6. Configuring nginx"
cp "$PROJECT_DIR/nginx/tbaps.conf" /etc/nginx/sites-available/tbaps.conf
ln -sf /etc/nginx/sites-available/tbaps.conf /etc/nginx/sites-enabled/tbaps.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
ok "Nginx configured and restarted"

# ── 7. Apply admin schema ─────────────────────────────────────────────────────
step "7. Applying admin schema (login system)"
PGPASSWORD=ztpass123 psql -U ztuser -d zerotrust -h localhost \
    -f "$PROJECT_DIR/scripts/admin_schema.sql" 2>/dev/null && ok "Admin schema applied" \
    || warn "Admin schema: already applied or DB issue (safe to ignore)"

# ── 8. Install and start backend as systemd service ───────────────────────────
step "8. Creating tbaps-api service"

# Find the uvicorn binary
if [[ -f /venv/bin/uvicorn ]]; then
    UVICORN=/venv/bin/uvicorn
elif [[ -f "$INSTALL_DIR/venv/bin/uvicorn" ]]; then
    UVICORN="$INSTALL_DIR/venv/bin/uvicorn"
else
    UVICORN=$(which uvicorn)
fi

cat > /etc/systemd/system/tbaps-api.service <<EOF
[Unit]
Description=TBAPS FastAPI Backend
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=kali
WorkingDirectory=$INSTALL_DIR/backend
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$UVICORN app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable tbaps-api
systemctl restart tbaps-api
sleep 4
ok "tbaps-api service started"

# ── 9. Health check ───────────────────────────────────────────────────────────
step "9. Health checks"
sleep 2
curl -sf http://localhost:8000/health && ok "Backend API: UP" || warn "Backend API: not responding yet (check: journalctl -u tbaps-api -n 30)"
curl -sf http://localhost/health      && ok "Nginx proxy:  UP" || warn "Nginx proxy: not responding"

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  TBAPS is deployed!${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo "  API:       http://localhost:8000"
echo "  Dashboard: http://localhost"
echo "  Login:     admin / Admin@1234"
echo ""
echo "  Now start Cloudflare tunnel:"
echo "  cloudflared tunnel --url http://localhost:80 --protocol http2"
echo ""
