#!/usr/bin/env bash
# ==============================================================================
# NEF Agent Build Script
# Compiles the Python agent to a standalone binary using PyInstaller.
# Run: bash agent/build.sh
# ==============================================================================

set -euo pipefail

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$AGENT_DIR/dist"
GREEN='\033[0;32m'; NC='\033[0m'
info() { echo -e "${GREEN}[BUILD]${NC} $*"; }

cd "$AGENT_DIR"

# Install deps
info "Installing agent dependencies..."
pip install -r requirements.txt -q

# ── Linux binary ───────────────────────────────────────────────────────────────
info "Building Linux binary: dist/nef"
pyinstaller \
    --onefile \
    --clean \
    --name nef \
    --add-data "collectors:collectors" \
    --hidden-import=psutil \
    --hidden-import=PIL \
    --hidden-import=watchdog \
    main.py

info "Linux binary: $DIST_DIR/nef"
ls -lh "$DIST_DIR/nef"

echo ""
info "Done!"
info "Deploy to employee Linux machine:"
info "  scp $DIST_DIR/nef user@machine:~/nef"
info "  ssh user@machine './nef --server http://YOUR_IP --install'"
