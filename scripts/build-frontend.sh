#!/usr/bin/env bash
# ==============================================================================
# TBAPS Frontend Build Script
# Builds the React/Vite frontend and deploys to /opt/tbaps/frontend/dist
# ==============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"
DEPLOY_DIR="/opt/tbaps/frontend"

GREEN='\033[0;32m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $*"; }

# Check Node.js
command -v node &>/dev/null || { echo "Node.js not found. Install Node.js 18+."; exit 1; }
command -v npm  &>/dev/null || { echo "npm not found."; exit 1; }

info "Node version: $(node --version)"
info "npm  version: $(npm --version)"

# Install dependencies
info "Installing frontend dependencies..."
cd "$FRONTEND_DIR"
npm ci --prefer-offline 2>/dev/null || npm install

# Build production bundle
info "Building production bundle..."
NODE_ENV=production npm run build

info "Build complete. Output: $FRONTEND_DIR/dist"
ls -lh "$FRONTEND_DIR/dist/"

# Deploy to /opt/tbaps/frontend
if [[ -d "$DEPLOY_DIR" ]]; then
    info "Deploying to $DEPLOY_DIR/dist ..."
    mkdir -p "$DEPLOY_DIR"
    rsync -a --delete "$FRONTEND_DIR/dist/" "$DEPLOY_DIR/dist/"
    info "Frontend deployed successfully."
else
    info "Deploy dir $DEPLOY_DIR not found — run install-services.sh first."
    info "Build output is at: $FRONTEND_DIR/dist"
fi
