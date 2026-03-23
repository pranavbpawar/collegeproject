#!/bin/bash
# TBAPS — Start all local services (Backend + Frontend)
# Run with: bash /mnt/r/MACHINE/MACHINE/scripts/wsl-start.sh
set -e

PROJECT_DIR="/mnt/r/MACHINE/MACHINE"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
WSL_PASS="wsl"

echo "================================================================"
echo " TBAPS — Starting local services"
echo "================================================================"

# Ensure PostgreSQL is running
echo "▶  Ensuring PostgreSQL is running..."
echo "$WSL_PASS" | sudo -S service postgresql start 2>/dev/null || true
sleep 1

# Kill any existing servers on port 8000 or 5173
echo "▶  Clearing ports 8000 and 5173..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true
sleep 1

# Start backend in background
echo "▶  Starting FastAPI backend on http://localhost:8000 ..."
cd "$BACKEND_DIR"
source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/tbaps-backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID (logs: /tmp/tbaps-backend.log)"

# Wait for backend to be ready
echo "▶  Waiting for backend to start..."
RETRIES=15
until curl -s http://localhost:8000/health > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    sleep 2
    RETRIES=$((RETRIES - 1))
done

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Backend is up!"
else
    echo "   ⚠️  Backend did not respond on /health — check logs: tail -f /tmp/tbaps-backend.log"
fi

# Seed admin user
echo "▶  Seeding admin user..."
curl -s -X POST http://localhost:8000/api/v1/admin/users/seed-admin 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('   ' + str(d.get('message', d)))" 2>/dev/null || echo "   (seed skipped or admin exists)"

# Start frontend in background (requires Node.js 20 via nvm)
echo "▶  Starting frontend on http://localhost:5173 ..."
cd "$FRONTEND_DIR"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 20 --silent 2>/dev/null || true
nohup npx vite --host 0.0.0.0 --port 5173 > /tmp/tbaps-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID (logs: /tmp/tbaps-frontend.log)"

echo ""
echo "================================================================"
echo " ✅ All services started!"
echo "================================================================"
echo ""
echo " 🌐 Frontend   →  http://localhost:5173"
echo " ⚙️  Backend    →  http://localhost:8000"
echo " 📖 API Docs   →  http://localhost:8000/docs"
echo " ❤️  Health     →  http://localhost:8000/health"
echo ""
echo " 🔑 Default login: admin / Admin@1234"
echo ""
echo " To view live logs:"
echo "   Backend:  tail -f /tmp/tbaps-backend.log"
echo "   Frontend: tail -f /tmp/tbaps-frontend.log"
echo ""
echo " To stop all services:"
echo "   bash /mnt/r/MACHINE/MACHINE/scripts/wsl-stop.sh"
echo "================================================================"
