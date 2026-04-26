#!/usr/bin/env bash
# =============================================================================
#  NEF Agent — Linux/macOS VM One-Click Installer
#  Works on Ubuntu, Debian, Fedora, macOS.
#  Usage: bash install.sh [SERVER_URL]
#  Example: bash install.sh http://192.168.1.100:8000
# =============================================================================

set -e

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   NEF Agent Installer — TBAPS Monitoring System  ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${RESET}"
echo ""

# ── 1. Determine Server URL ──────────────────────────────────────────────────
PRODUCTION_URL="https://tbaps-backend.onrender.com"
if [ -n "$1" ]; then
    SERVER_URL="$1"
else
    read -rp "Enter the TBAPS backend URL [default: ${PRODUCTION_URL}]: " SERVER_URL
    SERVER_URL="${SERVER_URL:-$PRODUCTION_URL}"
fi

if [ -z "$SERVER_URL" ]; then
    echo -e "${RED}[ERROR] Server URL is required. Exiting.${RESET}"
    exit 1
fi

echo -e "[KBT] Server URL: ${GREEN}${SERVER_URL}${RESET}"
echo ""

# ── 2. Verify Python is available ───────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 not found.${RESET}"
    echo "Install with: sudo apt-get install python3 python3-pip  (Ubuntu/Debian)"
    echo "         or:  sudo dnf install python3                   (Fedora)"
    exit 1
fi
echo "[NEF] Python found: $(python3 --version)"

# ── 3. Get agent directory ───────────────────────────────────────────────────
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[NEF] Agent directory: $AGENT_DIR"

# ── 4. Install Python dependencies ──────────────────────────────────────────
echo "[NEF] Installing Python dependencies..."
python3 -m pip install psutil Pillow watchdog requests pynput \
    --break-system-packages -q 2>/dev/null \
    || python3 -m pip install psutil Pillow watchdog requests pynput -q

echo "[NEF] Dependencies installed."

# ── 5. Create config directory and write initial config ─────────────────────
mkdir -p "$HOME/.nef/certs"
cat > "$HOME/.nef/config.json" <<EOF
{
  "server_url": "${SERVER_URL}",
  "upload_interval": 10,
  "heartbeat_interval": 60,
  "screenshot_interval": 300,
  "collect_screenshots": true,
  "collect_files": true,
  "collect_usb": true,
  "collect_input_metrics": true,
  "dns_capture_method": "cache",
  "max_buffer_events": 10000,
  "batch_size": 50,
  "enable_tray_icon": false
}
EOF
echo "[NEF] Config written to ~/.nef/config.json"

# ── 6. Register the agent with the server ───────────────────────────────────
echo "[NEF] Registering with server..."
python3 "$AGENT_DIR/main.py" --server "$SERVER_URL" --install || {
    echo -e "${YELLOW}[WARN] Registration failed — agent will retry on startup.${RESET}"
    echo "       Make sure the backend at $SERVER_URL is reachable."
}

# ── 7. Install as systemd user service ──────────────────────────────────────
if command -v systemctl &>/dev/null; then
    echo "[NEF] Installing systemd user service..."
    mkdir -p "$HOME/.config/systemd/user"
    cat > "$HOME/.config/systemd/user/nef.service" <<EOF
[Unit]
Description=NEF Monitoring Agent (TBAPS)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$(which python3) ${AGENT_DIR}/main.py
WorkingDirectory=${AGENT_DIR}
Restart=always
RestartSec=15
StartLimitIntervalSec=300
StartLimitBurst=5
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=%h/.nef
Environment=PYTHONUNBUFFERED=1
Environment=NEF_SERVER_URL=${SERVER_URL}

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable --now nef.service
    echo "[NEF] Systemd user service installed and started."
    echo "      Check status: systemctl --user status nef.service"
    echo "      View logs:    journalctl --user -u nef.service -f"
else
    # Fallback: cron job / nohup
    echo -e "${YELLOW}[NEF] systemctl not available — starting agent with nohup.${RESET}"
    nohup python3 "$AGENT_DIR/main.py" > "$HOME/.nef/agent.log" 2>&1 &
    echo "[NEF] Agent started (PID $!). Logs: ~/.nef/agent.log"
    # Add to ~/.bashrc for auto-start on login
    STARTUP_CMD="nohup python3 ${AGENT_DIR}/main.py >> ~/.nef/agent.log 2>&1 &"
    if ! grep -q "NEF Agent" "$HOME/.bashrc" 2>/dev/null; then
        echo "" >> "$HOME/.bashrc"
        echo "# NEF Agent auto-start" >> "$HOME/.bashrc"
        echo "$STARTUP_CMD" >> "$HOME/.bashrc"
        echo "[NEF] Added auto-start to ~/.bashrc"
    fi
fi

echo ""
echo -e "${GREEN}${BOLD}✅ NEF Agent installed and started!${RESET}"
echo ""
echo "   Server:  $SERVER_URL"
echo "   Logs:    ~/.nef/agent.log"
echo "   Status:  python3 $AGENT_DIR/main.py --status"
echo ""
echo "   The agent will appear in the TBAPS dashboard automatically."
echo ""
