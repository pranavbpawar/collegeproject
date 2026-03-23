#!/bin/bash
# TBAPS — WSL Local Setup Script
# Run with: bash /mnt/r/MACHINE/MACHINE/scripts/wsl-setup.sh
set -e

PROJECT_DIR="/mnt/r/MACHINE/MACHINE"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
WSL_PASS="wsl"

echo_step() { echo ""; echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; echo "▶  $1"; echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }

# ── 1. System packages ─────────────────────────────────────────────────────────
echo_step "Installing PostgreSQL and Node.js"
echo "$WSL_PASS" | sudo -S apt-get update -qq
echo "$WSL_PASS" | sudo -S apt-get install -y -qq \
    postgresql postgresql-contrib \
    nodejs npm \
    python3-venv python3-pip \
    curl

# ── 2. Start PostgreSQL ────────────────────────────────────────────────────────
echo_step "Starting PostgreSQL service"
echo "$WSL_PASS" | sudo -S service postgresql start
sleep 2

# ── 3. Create DB and user ──────────────────────────────────────────────────────
echo_step "Creating database: zerotrust / user: ztuser"
echo "$WSL_PASS" | sudo -S -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename='ztuser'" \
  | grep -q 1 && echo "User ztuser already exists" || \
  echo "$WSL_PASS" | sudo -S -u postgres psql -c "CREATE USER ztuser WITH PASSWORD 'ztpass123';"

echo "$WSL_PASS" | sudo -S -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='zerotrust'" \
  | grep -q 1 && echo "Database zerotrust already exists" || \
  echo "$WSL_PASS" | sudo -S -u postgres psql -c "CREATE DATABASE zerotrust OWNER ztuser;"

echo "$WSL_PASS" | sudo -S -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE zerotrust TO ztuser;"
echo "✅ Database ready"

# ── 4. Python virtual environment ──────────────────────────────────────────────
echo_step "Setting up Python virtual environment"
cd "$BACKEND_DIR"
python3 -m venv .venv
source .venv/bin/activate

# ── 5. Install Python packages ─────────────────────────────────────────────────
echo_step "Installing Python requirements (this takes a few minutes...)"
pip install --upgrade pip -q
pip install -r requirements.txt

# ── 6. Initialize database tables ─────────────────────────────────────────────
echo_step "Creating database tables"
python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from app.core.database import Base, engine
from app import models  # load all models so metadata knows about them
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print('✅ All tables created')
asyncio.run(init())
"

# ── 7. Seed admin user ─────────────────────────────────────────────────────────
echo_step "Seeding default admin user"
python3 -c "
import asyncio, sys
sys.path.insert(0, '.')
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def seed():
    async with AsyncSessionLocal() as db:
        # Try the seed endpoint logic directly
        result = await db.execute(text(\"SELECT COUNT(*) FROM users WHERE username='admin'\"))
        count = result.scalar()
        if count == 0:
            print('Admin user will be seeded via /api/v1/admin/users/seed-admin endpoint')
        else:
            print('Admin user already exists')

try:
    asyncio.run(seed())
except Exception as e:
    print(f'Note: {e}')
    print('Admin will be seeded on first API call to /api/v1/admin/users/seed-admin')
"

# ── 8. Frontend dependencies ───────────────────────────────────────────────────
echo_step "Installing frontend npm packages"
cd "$FRONTEND_DIR"
npm install --silent

echo ""
echo "================================================================"
echo " ✅ SETUP COMPLETE!"
echo "================================================================"
echo ""
echo " Next run the server with:"
echo "   bash /mnt/r/MACHINE/MACHINE/scripts/wsl-start.sh"
echo ""
echo " Or manually:"
echo "   Terminal 1 (Backend):"
echo "     cd /mnt/r/MACHINE/MACHINE/backend"
echo "     source .venv/bin/activate"
echo "     uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "   Terminal 2 (Frontend):"
echo "     cd /mnt/r/MACHINE/MACHINE/frontend"
echo "     npm run dev"
echo "================================================================"
