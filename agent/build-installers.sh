#!/usr/bin/env bash
# ==============================================================================
# NEF Agent — Installer Builder
# Builds:  dist/nef          — Linux standalone binary (PyInstaller)
#          dist/nef-agent.exe — Windows standalone .exe (PyInstaller via Wine)
# Run: bash agent/build-installers.sh
# ==============================================================================

set -euo pipefail

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$AGENT_DIR/dist"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
step() { echo -e "\n${GREEN}══ $* ${NC}"; }

cd "$AGENT_DIR"
mkdir -p "$DIST_DIR"

# ── Install build dependencies ─────────────────────────────────────────────────
step "Installing dependencies"
/venv/bin/pip install pyinstaller pillow psutil watchdog requests -q
ok "Dependencies ready"

# ── Build Linux binary ────────────────────────────────────────────────────────
step "Building Linux binary (nef)"
/venv/bin/pyinstaller \
    --onefile \
    --clean \
    --noconfirm \
    --name nef \
    --add-data "collectors:collectors" \
    --hidden-import=psutil \
    --hidden-import=PIL \
    --hidden-import=watchdog \
    --hidden-import=watchdog.observers \
    --hidden-import=watchdog.events \
    main.py 2>&1 | tail -5

if [[ -f "$DIST_DIR/nef" ]]; then
    ok "Linux binary: $DIST_DIR/nef ($(du -sh "$DIST_DIR/nef" | cut -f1))"
else
    warn "Linux binary build failed"
fi

# ── Build Windows .exe via Wine ───────────────────────────────────────────────
step "Building Windows .exe"
if command -v wine &>/dev/null; then
    # Check if Python is in Wine
    if wine python --version &>/dev/null 2>&1; then
        wine pip install pyinstaller psutil requests pillow watchdog -q 2>/dev/null
        wine pyinstaller \
            --onefile --clean --noconfirm \
            --name nef-agent \
            --add-data "collectors;collectors" \
            --hidden-import=psutil \
            --hidden-import=PIL \
            --hidden-import=watchdog \
            --hidden-import=watchdog.observers \
            main.py 2>&1 | tail -5
        if [[ -f "$DIST_DIR/nef-agent.exe" ]]; then
            ok "Windows .exe: $DIST_DIR/nef-agent.exe ($(du -sh "$DIST_DIR/nef-agent.exe" | cut -f1))"
        fi
    else
        warn "Wine Python not found. Install it:"
        warn "  winetricks python3"
        warn "  (or download Python from https://www.python.org/downloads/windows/)"
        warn "  Skipping .exe build — Linux .deb still works."
    fi
else
    warn "Wine not installed. To build .exe, run:"
    warn "  sudo apt install wine winetricks -y"
    warn "  winetricks python3"
    warn "  Then re-run this script."
fi

echo ""
ok "BUILD COMPLETE"
echo ""
echo "  Binaries in: $DIST_DIR/"
ls -lh "$DIST_DIR/" 2>/dev/null || true
echo ""
echo "  The backend will use these binaries to create .deb and .exe packages."
echo "  You do NOT need to rebuild unless agent code changes."
echo ""
